<?php
/* This file is part of Jeedom.
*
* Jeedom is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* Jeedom is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with Jeedom. If not, see <http://www.gnu.org/licenses/>.
*/

/* * ***************************Includes********************************* */
require_once __DIR__  . '/../../../../core/php/core.inc.php';

class geckospa extends eqLogic {

    public static function getcmdName($name) {
      	return str_replace(array('lights','pumps','waterCare','sensorBinary','sensor','waterHeater'),array('Lumière','Pompe','Traitement de l\'eau','Capteur binaire','Capteur','Chauffage'),$name);
    }

    public static function getCmdState($state) {
      	return str_replace(array('Away From Home','Energy Saving','Standard','Super Energy Saving','Weekender','state','ON','OFF','LO','HI'),array('En dehors de la maison', 'Economie d\énergie', 'Standard','Super economie d\énergie','Week-end', 'Etat','On','Off','Doucement','Fort',),$state);

    }

  /* Gestion du démon */
  public static function deamon_info() {
    $return = array();
    $return['log'] = __CLASS__;
    $return['state'] = 'nok';
    $pid_file = jeedom::getTmpFolder(__CLASS__) . '/geckospad.pid';
    if (file_exists($pid_file)) {
        if (@posix_getsid(trim(file_get_contents($pid_file)))) {
            $return['state'] = 'ok';
        } else {
            shell_exec(system::getCmdSudo() . 'rm -rf ' . $pid_file . ' 2>&1 > /dev/null');
        }
    }
    $return['launchable'] = 'ok';
    //$user = config::byKey('user', __CLASS__); // exemple si votre démon à besoin de la config user,
    //$pswd = config::byKey('password', __CLASS__); // password,
    // $clientId = config::byKey('clientId', __CLASS__); // et clientId
    $portDaemon=config::byKey('daemonPort', __CLASS__);
    /*
    if ($user == '') {
        $return['launchable'] = 'nok';
        $return['launchable_message'] = __('Le nom d\'utilisateur n\'est pas configuré', __FILE__);
    } elseif ($pswd == '') {
        $return['launchable'] = 'nok';
        $return['launchable_message'] = __('Le mot de passe n\'est pas configuré', __FILE__);
     } elseif ($clientId == '') {
         $return['launchable'] = 'nok';
         $return['launchable_message'] = __('La clé d\'application n\'est pas configurée', __FILE__);
    }
    */
    return $return;
}

/* Start daemon */
public static function deamon_start() {
  self::deamon_stop();
  $deamon_info = self::deamon_info();
  if ($deamon_info['launchable'] != 'ok') {
      throw new Exception(__('Veuillez vérifier la configuration', __FILE__));
  }

  $path = realpath(dirname(__FILE__) . '/../../resources/geckospad'); 
  $cmd = 'python3 ' . $path . '/geckospad.py'; // nom du démon
  $cmd .= ' --loglevel ' . log::convertLogLevel(log::getLogLevel(__CLASS__));
  $cmd .= ' --socketport ' . config::byKey('socketport', __CLASS__, '55009'); // port du daemon
  $cmd .= ' --callback ' . network::getNetworkAccess('internal', 'proto:127.0.0.1:port:comp') . '/plugins/geckospa/core/php/jeeGeckospa.php'; // chemin de la callback url 
  //$cmd .= ' --user "' . trim(str_replace('"', '\"', config::byKey('user', __CLASS__))) . '"'; // user compte somfy
  //$cmd .= ' --pswd "' . trim(str_replace('"', '\"', config::byKey('password', __CLASS__))) . '"'; // et password compte Somfy
  $cmd .= ' --apikey ' . jeedom::getApiKey(__CLASS__); // l'apikey pour authentifier les échanges suivants
  $cmd .= ' --pid ' . jeedom::getTmpFolder(__CLASS__) . '/geckospad.pid'; // et on précise le chemin vers le pid file (ne pas modifier)
  //$cmd .= ' --pincode "' . trim(str_replace('"', '\"', config::byKey('pincode', __CLASS__))) . '"'; // Pin code box Somfy
  //$cmd .= ' --boxLocalIp "' . trim(str_replace('"', '\"', config::byKey('boxLocalIp', __CLASS__))) . '"'; // IP box somfy
  $cmd .= ' --clientId "' . trim(str_replace('"', '\"', self::guidv4())) . '"'; // IP box somfy
  
  log::add(__CLASS__, 'info', 'Lancement démon');
  $result = exec($cmd . ' >> ' . log::getPathToLog('geckospa_daemon') . ' 2>&1 &'); 
  $i = 0;
  while ($i < 20) {
      $deamon_info = self::deamon_info();
      log::add(__CLASS__, 'info', 'Daemon_info -> '. json_encode($deamon_info));
      if ($deamon_info['state'] == 'ok') {
          break;
      }
      sleep(1);
      $i++;
  }
  if ($i >= 30) {
      log::add(__CLASS__, 'error', __('Impossible de lancer le démon, vérifiez le log', __FILE__), 'unableStartDeamon');
      return false;
  }
  message::removeAll(__CLASS__, 'unableStartDeamon');
  return true;
}

private static function guidv4() {
    $data = random_bytes(16);
    assert(strlen($data) == 16);

    $data[6] = chr(ord($data[6]) & 0x0f | 0x40);
    $data[8] = chr(ord($data[8]) & 0x3f | 0x80);
    
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($data), 4));
}

/* Stop daemon */
public static function deamon_stop() {
  $pid_file = jeedom::getTmpFolder(__CLASS__) . '/geckospad.pid'; // ne pas modifier
  if (file_exists($pid_file)) {
      $pid = intval(trim(file_get_contents($pid_file)));
      system::kill($pid);
  }
  system::kill('geckospad.py'); // nom du démon à modifier
  sleep(1);
}

public static function synchronize() {
    self::sendToDaemon(['action' => 'synchronize']);
    sleep(5);
}

protected static function getSocketPort() {
    return config::byKey('socketport', __CLASS__, 55009);
}

  /*
public function getImage() {
    //$typeMef=str_replace(array('internal:','io:'),array(''),$this->getConfiguration('type'));
    //$path='/var/www/html/plugins/geckospa/data/img/custom/' . $typeMef . '.png';

    if (!(file_exists($path))) {
        $path = '/var/www/html/plugins/geckospa/data/img/' . $typeMef . '.png';
        if (!(file_exists($path))) {
            $path = 'plugins/geckospa/data/img/io_logo.png';
        }
    }

    
    //log::add(__CLASS__, 'debug', 'getImage '. $this->getConfiguration('type') . ' -> ' . $path);
    return 'plugins/geckospa/data/img//gecko_equipment.png';
  	//return str_replace(array('/var/www/html/'),array(''),$path);
}
*/

/* Send data to daemon */
public static function sendToDaemon($params) {
  $deamon_info = self::deamon_info();
  if ($deamon_info['state'] != 'ok') {
      throw new Exception("Le démon n'est pas démarré");
  }
  $port = self::getSocketPort();
  $params['apikey'] = jeedom::getApiKey(__CLASS__);  
  $payLoad = json_encode($params);
  log::add(__CLASS__, 'debug', 'sendToDaemon -> ' . $payLoad);
  $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
  socket_connect($socket, '127.0.0.1', $port);
  socket_write($socket, $payLoad, strlen($payLoad));
  socket_close($socket);
}

  /*     * *************************Attributs****************************** */

  public static function create_or_update_devices($spas) {
    log::add(__CLASS__, 'debug', 'create_or_update_devices -> '. $spas);
    $aSpas=json_decode($spas,true);
    $eqLogics=eqLogic::byType(__CLASS__);
    foreach ($aSpas['spas'] as $spa) {
        log::add(__CLASS__, 'debug', '  - spa : ' . json_encode($spa));

        $found = false;
        foreach ($eqLogics as $eqLogic) {
            if ($spa['id'] == $eqLogic->getLogicalId()) {
                $eqLogic_found = $eqLogic;
                $found = true;
                break;
            }
        }

        if (!$found) {
            log::add(__CLASS__, 'debug', '      -> spa not exist -> create it');
             $eqLogic = new eqLogic();
             $eqLogic->setEqType_name(__CLASS__);
             $eqLogic->setIsEnable(1);
             $eqLogic->setIsVisible(1);
             $eqLogic->setName($spa['name']);
             $eqLogic->setConfiguration('id', $spa['id']);
             $eqLogic->setLogicalId($spa['id']);
             $eqLogic->save();

             $eqLogic = self::byId($eqLogic->getId());

        } else {
            $eqLogic=$eqLogic_found;
            
        }
      

        foreach($spa['cmds'] as $cmd) {
            log::add(__CLASS__, 'debug', '          * Cmd name : ' . $cmd['name'] . ' -> ' . $cmd['state']);
          	if (array_key_exists('state',$cmd) && array_key_exists('name',$cmd)) {

               	$cmdName=$cmd['name'].'_state';
              	$geckoSpaCmd = $eqLogic->getCmd(null, $cmdName);

              	if ($cmd['name'] == 'waterHeater') {
                	log::add(__CLASS__, 'debug', '                  -> Create cmds linked to waterheater function');
                } else {
                  	//create cmd info state
                    if (!(is_object($geckoSpaCmd))) {
                        log::add(__CLASS__, 'debug', '                  -> Create cmd : ' . $cmdName);
                        $geckoSpaCmd = new geckospaCmd();
                        $geckoSpaCmd->setName(self::buildCmdName($cmdName));
                        $geckoSpaCmd->setLogicalId($cmdName);
                        $geckoSpaCmd->setEqLogic_id($eqLogic->getId());
                        $geckoSpaCmd->setIsVisible(1); 
                        $geckoSpaCmd->setType('info');
                        if(is_bool($cmd['state'])) {
                          $geckoSpaCmd->setSubType('binary');
                        } else {
                          $geckoSpaCmd->setSubType('string');
                        }  

                        $geckoSpaCmd->save();
                    } else {
                        log::add(__CLASS__, 'debug', '                  -> cmd exist : ' . $geckoSpaCmd->getName() . '|' . $geckoSpaCmd->getType(). '|'.$geckoSpaCmd->getSubType());
                    }


                    //set or update value
                    if ($cmd['state'] != '') {
                        if(is_bool($cmd['state'])) {
                            $geckoSpaCmd->event((boolean) $cmd['state']);
                        } else {
                            $geckoSpaCmd->event($cmd['state']);
                        }
                    }
                }  
              
            }
          
          	//create cmd action 
          	if (array_key_exists('stateList',$cmd) && array_key_exists('name',$cmd)) {
              	foreach($cmd['stateList'] as $state) {
                    $cmdName=$cmd['name'].'_'.$state;
                    $geckoSpaCmd = $eqLogic->getCmd(null, $cmdName);
                    if (!(is_object($geckoSpaCmd))) {
                        $geckoSpaCmd = new geckospaCmd();
                        $geckoSpaCmd->setType('action');
                        $geckoSpaCmd->setIsVisible(1);
                        $geckoSpaCmd->setSubType('other');
                        $geckoSpaCmd->setName(self::buildCmdName($cmdName));
                        $geckoSpaCmd->setLogicalId($cmdName);
                        $geckoSpaCmd->setEqLogic_id($eqLogic->getId());
                        $geckoSpaCmd->save();
                    }
                }
            }
          
        }
      
     }

  }

  private function buildCmdName($cmdName) {
    $aCmdName=explode('_',$cmdName);
    if (sizeof($aCmdName) > 2) {
        return self::getcmdName($aCmdName[0]) . ' ' . $aCmdName[1] . ' ' . self::getCmdState($aCmdName[2]);
    } else {
        return self::getcmdName($aCmdName[0]) . ' ' . self::getCmdState($aCmdName[1]);
    }    
  }

  public static function updateItems($item){
    log::add(__CLASS__, 'debug', 'updateItems -> '. json_encode($item));
    $eqLogics=eqLogic::byType(__CLASS__);
    if (array_key_exists('deviceURL', $item)) {        
        $found = false;
        $eqLogic_found;        

        foreach ($eqLogics as $eqLogic) {
            if ($item['deviceURL'] == $eqLogic->getConfiguration('deviceURL')) {
                $eqLogic_found = $eqLogic;
                $found = true;
                break;
            }
        }
    
        if (!$found) {
            log::add(__CLASS__, 'error', ' - évènement sur équipement :' .$item['deviceURL'].' non géré par le plugin ... relancer le daemon pour forcer sa création');
        } else {
            foreach ($item['deviceStates'] as $state) {
                log::add(__CLASS__, 'debug','   - maj equipement ' . $item['deviceURL'] . ' | commande : ' . $state['name'] . '| valeur : '.$state['value']);
                $cmd=$eqLogic_found->getCmd('info',$state['name'],true, false);
            
                if (is_object($cmd)){            
                    if ($state['name'] == $cmd->getConfiguration('type')) {
                        $cmd->setCollectDate('');

                        $value = $state['value'];
                        if ($state['name'] == "core:ClosureState") {
                            $value = 100 - $value;
                        }
                        log::add(__CLASS__, 'debug','       -> valeur MAJ : ' . $value);
                        $cmd->event($value);
                    }
                }
            }    
        }
    } elseif (array_key_exists('execId', $item)) { 
        if (array_key_exists('actions',$item)) {
            foreach($item['actions'] as $action) {
                if (array_key_exists('deviceURL',$action)) {               
                    foreach ($eqLogics as $eqLogic) {   
                        if ($action['deviceURL'] == $eqLogic->getConfiguration('deviceURL')) {
                            //log::add(__CLASS__, 'debug','   - store execution id  ' . $action['execId'] . ' for device ' . $action['deviceURL']);
                            $eqLogic->setConfiguration('execId',$action['execId']);
                            $eqLogic->save();
                            break;
                        }
                    }
                }
            }
        } else {
            if (array_key_exists('newState',$item) && $item['newState'] == 'COMPLETED') {
                foreach ($eqLogics as $eqLogic) {   
                    if ($item['execId'] == $eqLogic->getConfiguration('execId')) {
                        $eqLogic->setConfiguration('execId','');
                        $eqLogic->save();
                        break;
                    }
                }
            }
        }
    }
  }
  /*
  * Permet de définir les possibilités de personnalisation du widget (en cas d'utilisation de la fonction 'toHtml' par exemple)
  * Tableau multidimensionnel - exemple: array('custom' => true, 'custom::layout' => false)
  public static $_widgetPossibility = array();
  */

  /*
  * Permet de crypter/décrypter automatiquement des champs de configuration du plugin
  * Exemple : "param1" & "param2" seront cryptés mais pas "param3"
  public static $_encryptConfigKey = array('param1', 'param2');
  */

  /*     * ***********************Methode static*************************** */

  /*
  * Fonction exécutée automatiquement toutes les minutes par Jeedom
  public static function cron() {}
  */

  /*
  * Fonction exécutée automatiquement toutes les 5 minutes par Jeedom
  public static function cron5() {}
  */

  /*
  * Fonction exécutée automatiquement toutes les 10 minutes par Jeedom
  public static function cron10() {}
  */

  /*
  * Fonction exécutée automatiquement toutes les 15 minutes par Jeedom
  public static function cron15() {}
  */

  /*
  * Fonction exécutée automatiquement toutes les 30 minutes par Jeedom
  public static function cron30() {}
  */

  /*
  * Fonction exécutée automatiquement toutes les heures par Jeedom
  public static function cronHourly() {}
  */

  /*
  * Fonction exécutée automatiquement tous les jours par Jeedom
  public static function cronDaily() {}
  */
  
  /*
  * Permet de déclencher une action avant modification d'une variable de configuration du plugin
  * Exemple avec la variable "param3"
  public static function preConfig_param3( $value ) {
    // do some checks or modify on $value
    return $value;
  }
  */

  /*
  * Permet de déclencher une action après modification d'une variable de configuration du plugin
  * Exemple avec la variable "param3"
  public static function postConfig_param3($value) {
    // no return value
  }
  */

  /*
   * Permet d'indiquer des éléments supplémentaires à remonter dans les informations de configuration
   * lors de la création semi-automatique d'un post sur le forum community
   public static function getConfigForCommunity() {
      return "les infos essentiel de mon plugin";
   }
   */

  /*     * *********************Méthodes d'instance************************* */

  // Fonction exécutée automatiquement avant la création de l'équipement
  public function preInsert() {
  }

  // Fonction exécutée automatiquement après la création de l'équipement
  public function postInsert() {
  }

  // Fonction exécutée automatiquement avant la mise à jour de l'équipement
  public function preUpdate() {
  }

  // Fonction exécutée automatiquement après la mise à jour de l'équipement
  public function postUpdate() {
  }

  // Fonction exécutée automatiquement avant la sauvegarde (création ou mise à jour) de l'équipement
  public function preSave() {
  }

  // Fonction exécutée automatiquement après la sauvegarde (création ou mise à jour) de l'équipement
  public function postSave() {
  }

  // Fonction exécutée automatiquement avant la suppression de l'équipement
  public function preRemove() {
  }

  // Fonction exécutée automatiquement après la suppression de l'équipement
  public function postRemove() {
  }

  /*
  * Permet de crypter/décrypter automatiquement des champs de configuration des équipements
  * Exemple avec le champ "Mot de passe" (password)
  public function decrypt() {
    $this->setConfiguration('password', utils::decrypt($this->getConfiguration('password')));
  }
  public function encrypt() {
    $this->setConfiguration('password', utils::encrypt($this->getConfiguration('password')));
  }
  */

  /*
  * Permet de modifier l'affichage du widget (également utilisable par les commandes)
  public function toHtml($_version = 'dashboard') {}
  */

  /*     * **********************Getteur Setteur*************************** */
}

class geckospaCmd extends cmd {
  /*     * *************************Attributs****************************** */

  /*
  public static $_widgetPossibility = array();
  */

  /*     * ***********************Methode static*************************** */


  /*     * *********************Methode d'instance************************* */

  /*
  * Permet d'empêcher la suppression des commandes même si elles ne sont pas dans la nouvelle configuration de l'équipement envoyé en JS
  public function dontRemoveCmd() {
    return true;
  }
  */

  // Exécution d'une commande
  public function execute($_options = array()) {
    $eqlogic = $this->getEqLogic();
    $logicalId=$this->getLogicalId();

    $deviceUrl=$this->getConfiguration('deviceURL');
    $commandName=$this->getConfiguration('commandName');
    $parameters=$this->getConfiguration('parameters');
    $execId=$eqlogic->getConfiguration('execId');

    $type=$this->type;
    $subType=$this->subType;
    log::add('geckospa', 'debug','   - Execution demandée ' . $deviceUrl . ' | commande : ' . $commandName . '| parametres : '.$parameters . '| type : ' . $type . '| Sous type : '. $subType . '| exec id : ' . $execId);

    if ($this->type == 'action') {
        switch ($this->subType) {
            case 'slider':
                $type = $this->getConfiguration('request');
                $parameters = str_replace('#slider#', $_options['slider'], $parameters);

                $newEventValue = $parameters;

                switch ($type) {
                    case 'orientation':
                        if ($commandName == "setOrientation") {
                            $parameters = array_map('intval', explode(",", $parameters));
                            $eqlogic->sendToDaemon(['action' => 'execCmd', 'deviceUrl' => $deviceURL, 'commandName'=>$commandName, 'parameters' =>  $parameters, 'name' =>  $this->getName(), 'execId' => $execId]);
                              return;
                        }
                        break;
                    case 'closure':
                        if ($commandName == "setClosure") {
                            $parameters = 100 - $parameters;

                            $parameters = array_map('intval', explode(",", $parameters));
                            $eqlogic->sendToDaemon(['action' => 'execCmd', 'deviceUrl' => $deviceURL, 'commandName'=>$commandName, 'parameters' =>  $parameters, 'name' =>  $this->getName(), 'execId' => $execId]);

                            return;
                        }
                        break;
                }
            case 'select':
                if ($commandName == 'setLockedUnlocked') {
                    $parameters = str_replace('#select#', $_options['select'], $parameters);
                }
                break;
          	case 'other':
            	//$parameters = array_map('intval', explode(",", $parameters));
            	$eqlogic->sendToDaemon(['action' => 'execCmd', 'deviceUrl' => $deviceUrl, 'commandName'=>$commandName, 'parameters' =>  $parameters, 'name' =>  $this->getName(), 'execId' => $execId]);
            	return;
           
        }

        if ($this->getConfiguration('nparams') == 0) {
            $parameters = "";
        } else if ($commandName == "setClosure") {
            $parameters = array_map('intval', explode(",", $parameters));
        } else {
            $parameters = explode(",", $parameters);
        }

        if ($commandName == "cancelExecutions") {
            $execId = $parameters[0];

            log::add('geckospa', 'debug', "will cancelExecutions: (" . $execId . ")");
            
        }
        return;
    }

    if ($this->type == 'info') {
        return;
    }

  }

  /*     * **********************Getteur Setteur*************************** */
}