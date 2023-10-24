<?php

try {
    require_once dirname(__FILE__) . "/../../../../core/php/core.inc.php";

    if (!jeedom::apiAccess(init('apikey'), 'geckospa')) { //remplacez template par l'id de votre plugin
        echo __('Vous n\'etes pas autorisé à effectuer cette action', __FILE__);
        die();
    }
    if (init('test') != '') {
        echo 'OK';
        die();
    }
    $result = json_decode(file_get_contents("php://input"), true);
    if (!is_array($result)) {
        die();
    }

    log::add('geckospa', 'debug', '*-----------------------------------------------------------------------------*');
    log::add('geckospa', 'debug', '| received message from daemon -> ' . json_encode($result));
    if (isset($result['updateItems'])) {
        $jsonMefUpdateItems=str_replace(array('\\','"{','}"'), array('','{','}'),json_encode($result['updateItems']));
        
        log::add('geckospa', 'debug', 'Message receive for evenItem -> ' . $jsonMefUpdateItems);
        geckospa::updateItems($jsonMefUpdateItems);
    } elseif (isset($result['devicesList'])) {
        $jsonMefListDevices=str_replace(array('\\','"{','}"'), array('','{','}'),json_encode($result['devicesList']));

        log::add('geckospa', 'debug', 'Message receive for devicesList -> ' . $jsonMefListDevices);        
        geckospa::create_or_update_devices($jsonMefListDevices);
    }
    log::add('geckospa', 'debug', '*-----------------------------------------------------------------------------*');
} catch (Exception $e) {
    log::add('geckospa', 'error', displayException($e)); //remplacez template par l'id de votre plugin
}