# This file is part of Jeedom.
#
# Jeedom is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Jeedom is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Jeedom. If not, see <http://www.gnu.org/licenses/>.

import logging
import string
import sys
import os
import time
import datetime
import traceback
import re
import signal
from optparse import OptionParser
from os.path import join
import json
import argparse
import time

from geckolib import GeckoLocator
from geckolib import GeckoConstants

try:
	from jeedom.jeedom import *
except ImportError:
	print("Error: importing module jeedom.jeedom")
	sys.exit(1)

def read_socket():
	global JEEDOM_SOCKET_MESSAGE
	if not JEEDOM_SOCKET_MESSAGE.empty():
		logging.debug("Message received in socket JEEDOM_SOCKET_MESSAGE")
		message = json.loads(JEEDOM_SOCKET_MESSAGE.get().decode('utf-8'))
		if message['apikey'] != _apikey:
			logging.error("Invalid apikey from socket: %s", message)
			return
		try:
			if message['action'] == 'execCmd':				
				logging.info('== action execute command ==')
				execCmd(message)
			elif message['action'] == 'synchronize':
				logging.info('== action synchronize ==')
				getDevicesList()
			else:
				logging.info('== other action not manage yes : ' + message['action']  + ' ==')
		except Exception as e:
			logging.error('Send command to demon error: %s' ,e)

def listen():
	logging.debug('Listen socket jeedom for client id' + _client_id)
	jeedom_socket.open()

	locator = GeckoLocator(_client_id)
	locator = spaDiscover(locator)
	
	try:
		while 1:
			#time.sleep(0.5)
			time.sleep(5)
			read_socket()
			fetchStatesForallSpa(locator)

	except KeyboardInterrupt:
		shutdown()


def spaDiscover(locator):
	logging.debug("Discovering spa ...")
	locator.start_discovery()

	# We can perform other operations while this is progressing, like output a dot
	while not locator.has_had_enough_time:
		# Could also be `await asyncio.sleep(1)`
		locator.wait(1)		
		print(".", end="", flush=True)
	
	locator.complete()

	if len(locator.spas) == 0:
		logging.error("Cannot continue as there were no spas detected")
		shutdown()

	logging.debug("Number of spas discover : %i", int(len(locator.spas)))
	return locator

def fetchStatesForallSpa(locator):
	logging.debug("Get all states for each spa")
	response={}
	response['spas']=[]

	for i in range(len(locator.spas)):
		spa={}
		spa['name']=locator.spas[i].name
		spa['id']=locator.spas[i].identifier_as_string
		#spa['cmds']=[]
		#spa['cmds'].append(state({locator.spas[i].identifier_as_string}))
		spa['cmds']=state({locator.spas[i].identifier_as_string})
		response['spas'].append(spa)

	logging.debug("List of spa and states : %s", json.dumps(response))
	jeedom_com.send_change_immediate({'devicesList' : json.dumps(response)})

def state(spaIdentifier):
	logging.debug("Get states for spa identifier : %s", spaIdentifier)

	facade = GeckoLocator.find_spa(_client_id, spaIdentifier).get_facade(False)

	logging.debug("	- Connectiong to : %s", facade.name)
	#print(f"	* Connecting to {facade.name} ", end="", flush=True)
	while not facade.is_connected:
		# Could also be `await asyncio.sleep(1)`
		facade.wait(1)
		print(".", end="", flush=True)
	#spa={}
	#spa['name']=facade.name
	#spa['id']=facade.identifier
	#spa['cmds']=[]
	cmds=[]

	logging.debug("		-> Connected")
	

	#print(f"		- Watercare mode : {facade.water_care.mode} ;list: {facade.water_care.modes}")
	cmdWaterCare={}
	cmdWaterCare['name'] = 'waterCare'
	cmdWaterCare['state'] = facade.water_care.mode
	cmdWaterCare['stateString'] = facade.water_care.monitor
	cmdWaterCare['stateList'] = facade.water_care.modes
	#cmdWaterCare['on_watercar'] = facade.water_care.on_watercar
	#cmdWaterCare['stateString']=GeckoConstants.WATERCARE_MODE_STRING.index({cmdWaterCare['state']})
	cmds.append(cmdWaterCare)
    

	#print(f"		- Lights mode : {len(facade.lights)} |{facade.lights[0].is_on}")
	for i in range(len(facade.lights)):
		cmdLights = {}
		cmdLights['name'] = "lights_" + str(i)
		cmdLights['state'] = facade.lights[i].is_on
		cmdLights['stateList'] = ['ON', 'OFF']
		cmds.append(cmdLights)

	#print(f"		- Heater : {facade.water_heater.min_temp} | {facade.water_heater.max_temp} | {facade.water_heater.current_temperature} | {facade.water_heater.temperature_unit} ")
	cmdHeater={}
	cmdHeater['name'] = 'waterHeater'
	cmdHeater['min_temp'] = facade.water_heater.min_temp
	cmdHeater['max_temp'] = facade.water_heater.max_temp
	cmdHeater['current_temp'] = facade.water_heater.current_temperature
	cmdHeater['current_operation'] = facade.water_heater.current_operation
	cmdHeater['target_temperature'] = facade.water_heater.target_temperature    
	cmdHeater['unit'] = facade.water_heater.temperature_unit
	cmds.append(cmdHeater)
    
    
	#print(f"		- Pump : {len(facade.pumps)} | {facade.pumps[0].is_on} | {facade.pumps[0].mode} | {facade.pumps[0].modes} ")
	for i in range(len(facade.pumps)):
		cmdPumps={}
		cmdPumps['name'] = "pumps_" + str(i)
		cmdPumps['state'] = facade.pumps[i].is_on
		cmdPumps['mode'] = facade.pumps[i].mode
		cmdPumps['stateList'] = facade.pumps[i].modes
		cmds.append(cmdPumps)

	for i in range(len(facade.blowers)):
		cmdBlowers = {}
		cmdBlowers['name'] = "blower_" + str(i)
		cmdBlowers['state'] = facade.blowers[i].is_on
		cmds.append(cmdBlowers)

	for i in range(len(facade.reminders)):
		print(f"aa {facade.reminders[i].type}")

	for i in range(len(facade.sensors)):
		cmdSensors = {}
		cmdSensors['name'] = "sensor_" + str(i)
		cmdSensors['label'] = facade.sensors[i].accessor.tag        
		cmdSensors['state'] = facade.sensors[i].state
		cmdSensors['unit'] = facade.sensors[i].unit_of_measurement
		cmds.append(cmdSensors)
		#print(cmdSensors)

		del cmdSensors
	for i in range(len(facade.binary_sensors)):
		cmdSensors = {}
		cmdSensors['name'] = "sensorBinary_" + str(i)
		cmdSensors['label'] = facade.binary_sensors[i].accessor.tag
		cmdSensors['state'] = facade.binary_sensors[i].state
		cmdSensors['unit'] = facade.binary_sensors[i].unit_of_measurement
		cmds.append(cmdSensors)        

		del cmdSensors

	facade.complete()
	return cmds	

def handler(signum=None, frame=None):
	logging.debug("Signal %i caught, exiting...", int(signum))
	shutdown()

def shutdown():
	logging.debug("Shutdown")
	logging.debug("Removing PID file %s", _pidfile)
	try:
		if _listenerId:
			unregisterListener()
	except:
		pass
	try:
		os.remove(_pidfile)
	except:
		pass
	try:
		jeedom_socket.close()
	except:
		pass
	# try:
	# 	jeedom_serial.close()
	# except:
	# 	pass
	logging.debug("Exit 0")
	sys.stdout.flush()
	os._exit(0)

def execCmd(params):	
	logging.debug(' * Execute command')
	try:

		if params['action'] != "":
			logging.debug("Action : %s",params['action'])

		if params['cmd'] != "":
			logging.debug("cmd : %s",params['cmd'])

		if params['ind'] != "":
			logging.debug("Indice : %s",params['ind'])

		if params['value'] != "":
			logging.debug("value : %s",params['value'])
			

	except requests.exceptions.HTTPError as err:
		logging.error("Error when executing cmd to tahoma -> %s",err)
		shutdown()

"""
def httpLog():
	logging.getLogger("requests").setLevel(logging.ERROR)
	logging.getLogger("urllib3").setLevel(logging.ERROR)
	requests.packages.urllib3.disable_warnings()
	

# ----------------------------------------------------------------------------





def loginTahoma():
	logging.debug(' * logging tahoma')

	try:
		url = _overkizUrl +'/login'

		payload ={
			'userId' : _user,
			'userPassword' : _pwd
		}

		headers = {
			'Content-Type': 'application/x-www-form-urlencoded'
		}

		response = requests.request("POST", url, headers=headers, data=payload)

		if response.status_code and (response.status_code == 200):
			if response.cookies.get("JSESSIONID"):
				global _jsessionid
				_jsessionid =  response.cookies.get("JSESSIONID")			
		else:
			logging.error("Http code : %s", response.status_code)
			logging.error("Response : %s", response.json())
			logging.error("Response header : %s", response.headers)
			shutdown()
			
	except requests.exceptions.HTTPError as err:
		logging.error("Error when logging to tahoma -> %s",err)

def tahoma_token():
	logging.debug(' * retrieve tahoma_token')
	try:

		url = _overkizUrl +'/config/' + _pincode + '/local/tokens/generate'

		headers = {
			'Content-Type' : 'application/json',
			'Cookie' : 'JSESSIONID=' + _jsessionid
		}

		response = requests.request("GET", url, headers=headers)

		if response.status_code and (response.status_code == 200):
			if response.json().get('token'):
				global _tokenTahoma
				_tokenTahoma = response.json().get('token')
		else:
			logging.error("Http code : %s", response.status_code)
			logging.error("Response : %s", response.json())
			logging.error("Response header : %s", response.headers)
			shutdown()
	except requests.exceptions.HTTPError as err:
		logging.error("Error when retrieving tahoma token -> %s",err)
		shutdown()

def getDevicesList():	
	logging.debug(' * Retrieve devices list')
	try:

		url = _ipBox +'/enduser-mobile-web/1/enduserAPI/setup/devices'
		
		
		headers = {
			'Content-Type' : 'application/json',
			'Authorization' : 'Bearer ' + _tokenTahoma
		}

		response = requests.request("GET", url, verify=False, headers=headers)

		if response.status_code and (response.status_code == 200):
			jeedom_com.send_change_immediate({'devicesList' : response.json()})
		else:
			logging.error("Http code : %s", response.status_code)
			logging.error("Response : %s", response.json())
			logging.error("Response header : %s", response.headers)	
			shutdown()	

	except requests.exceptions.HTTPError as err:
		logging.error("rror when retrieving tahoma devices list -> %s",err)
		shutdown()

def validateToken():
	logging.debug(' * validate tahoma token')
	try:
	
		url = _overkizUrl + '/config/' + _pincode + '/local/tokens'
		
		headers = {
			'Content-Type' : 'application/json',
			'Cookie' : 'JSESSIONID=' + _jsessionid
		}

		payload=json.dumps({
				"label": "JeedomTahomaLocalApi_token",				
				"token": _tokenTahoma ,
				"scope": "devmode"
		})		

		response = requests.request("POST", url, headers=headers, data=payload)

		if not response.status_code and not (response.status_code == 200):
			logging.error("Http code : %s", response.status_code)
			logging.error("Response : %s", response.json())
			logging.error("Response header : %s", response.headers)
			shutdown()
		

	except requests.exceptions.HTTPError as err:
		logging.error("Error when validate tahoma token -> %s",err)
		shutdown()

def downloadTahomaCertificate():
	logging.debug(' * Download Tahoma certificate')
	try:

		url = 'https://ca.overkiz.com/overkiz-root-ca-2048.crt'
		
		response = requests.request("GET", url)

		logging.debug("Http code : %s", response.status_code)

		open('/var/www/html/plugins/tahomalocalapi/resources/tahomalocalapid/overkiz-root-ca-2048.crt', "wb").write(response.content)

	except requests.exceptions.HTTPError as err:
		logging.error("Error when downloading tahoma certificate -> %s",err)

def registerListener():
	logging.debug(' * Register listener')
	try:

		url = _ipBox +'/enduser-mobile-web/1/enduserAPI/events/register'
		
		
		headers = {
			'Content-Type' : 'application/json',
			'Authorization' : 'Bearer ' + _tokenTahoma
		}

		
		response = requests.request("POST", url, verify=False, headers=headers)



		if response.status_code and (response.status_code == 200):
			if response.json().get('id'):
				global _listenerId
				_listenerId = response.json().get('id')
		else:
			logging.error("Http code : %s", response.status_code)
			logging.error("Response : %s", response.json())
			logging.error("Response header : %s", response.headers)	
			shutdown()	

	except requests.exceptions.HTTPError as err:
		logging.error("Error when register listener tahoma -> %s",err)
		shutdown()

def fetchListener():
	try:

		url = _ipBox +'/enduser-mobile-web/1/enduserAPI/events/' + _listenerId + '/fetch'		
		
		headers = {
			'Content-Type' : 'application/json',
			'Authorization' : 'Bearer ' + _tokenTahoma
		}
		
		response = requests.request("POST", url, verify=False, headers=headers)		

		if response.status_code and (response.status_code == 200):
			if response.json():
				logging.debug("Response : %s", response.json())
				json_data = response.json()
				for item in json_data:
					#logging.debug(item['name'] + ' -> ' + item['deviceURL'])
					jeedom_com.send_change_immediate({'eventItem' : item})
					#getDeviceStates(item['deviceURL'])	
		else:
			logging.error("Http code : %s", response.status_code)
			logging.error("Response header : %s", response.headers)		
			shutdown()

	except requests.exceptions.HTTPError as err:
		logging.error("Error when fetch listener tahoma -> %s",err)
		shutdown()

def getDeviceStates(deviceUrl):
	
	logging.debug(' * getDeviceStates | '  + deviceUrl)
	try:

		url = _ipBox +'/enduser-mobile-web/1/enduserAPI/setup/devices/'+ quote(deviceUrl) +'/states'
		logging.debug(' 	* url :  '  + url)
		
		headers = {
			'Content-Type' : 'application/json',
			'Authorization' : 'Bearer ' + _tokenTahoma
		}
		
		response = requests.request("POST", url, verify=False, headers=headers)

		logging.debug("Http code : %s", response.status_code)

		if response.status_code and (response.status_code == 200):
			if response.json():
				logging.debug("Response : %s", response.json())
				

		#logging.debug("Response header : %s", response.headers)		
		#return response.json().get('id')

	except requests.exceptions.HTTPError as err:
		logging.error("Error when retrieving tahoma device states -> %s",err)
		shutdown()

def unregisterListener():
	#logging.debug(' * Tahoma fetchListener | '  + listenerId)
	try:

		url = _ipBox +'/enduser-mobile-web/1/enduserAPI/events/' + _listenerId + '/unregister'	
		
		headers = {
			'Content-Type' : 'application/json',
			'Authorization' : 'Bearer ' + _tokenTahoma
		}
		
		response = requests.request("POST", url, verify=False, headers=headers)		
	except requests.exceptions.HTTPError as err:
		logging.error("Error when unregister listener to tahoma -> %s",err)



def deleteExecutionForADevice(deviceUrl):
	logging.debug(' * Delete execution for a device: ' + deviceUrl)
	try:
		url = _ipBox +'/enduser-mobile-web/1/enduserAPI/exec/current'

		headers = {
			'Content-Type' : 'application/json',
			'Authorization' : 'Bearer ' + _tokenTahoma
		}

		response = requests.request("GET", url, verify=False, headers=headers)

		if response.status_code and (response.status_code == 200):
			json_data = response.json()
			for item in json_data:
				for act in item['actionGroup']['actions']:
					if (deviceUrl == act['deviceURL']):
						deleteExecution(item['id'])
		else:
			logging.error("Http code : %s", response.status_code)
			logging.error("Response : %s", response.json())
			logging.error("Response header : %s", response.headers)
			#shutdown()
	except requests.exceptions.HTTPError as err:
		logging.error("Error when deleting execution for a deviceto tahoma -> %s",err)
		shutdown()

def deleteExecution(executionId):
	logging.debug(' * Delete execution : ' + executionId)
	try:
		url = _ipBox +'/enduser-mobile-web/1/enduserAPI/exec/current/setup/' + executionId

		headers = {
			'Content-Type' : 'application/json',
			'Authorization' : 'Bearer ' + _tokenTahoma
		}

		response = requests.request("DELETE", url, verify=False, headers=headers)

		if response.status_code and (response.status_code == 200):
			logging.debug('Delete execution ok')
		else:
			logging.error("Http code : %s", response.status_code)
			logging.error("Response : %s", response.json())
			logging.error("Response header : %s", response.headers)
			#shutdown()
	except requests.exceptions.HTTPError as err:
		logging.error("Error when deleting execution cmd to tahoma -> %s",err)
		shutdown()
"""
# ----------------------------------------------------------------------------

_log_level = "error"
_socket_port = 55009
_socket_host = 'localhost'
_device = 'auto'
_pidfile = '/tmp/geckospapid.pid'
_apikey = ''
_callback = ''
_cycle = 0.3

_client_id=''
_locator=''

parser = argparse.ArgumentParser(
description='Desmond Daemon for Jeedom plugin')
parser.add_argument("--device", help="Device", type=str)
parser.add_argument("--loglevel", help="Log Level for the daemon", type=str)
parser.add_argument("--callback", help="Callback", type=str)
parser.add_argument("--apikey", help="Apikey", type=str)
parser.add_argument("--cycle", help="Cycle to send event", type=str)
parser.add_argument("--pid", help="Pid file", type=str)
parser.add_argument("--socketport", help="Daemon port", type=str)
parser.add_argument("--clientId", help="Client Id", type=str)
args = parser.parse_args()

if args.device:
	_device = args.device
if args.loglevel:
    _log_level = args.loglevel
if args.callback:
    _callback = args.callback
if args.apikey:
    _apikey = args.apikey
if args.pid:
    _pidfile = args.pid
if args.cycle:
    _cycle = float(args.cycle)
if args.socketport:
	_socket_port = args.socketport
if args.clientId:
	_client_id = args.clientId

_socket_port = int(_socket_port)

jeedom_utils.set_log_level(_log_level)

logging.info('*-------------------------------------------------------------------------*')
logging.info('Start demond')
logging.info('Log level: %s', _log_level)
logging.info('Socket port: %s', _socket_port)
logging.info('Socket host: %s', _socket_host)
logging.info('PID file: %s', _pidfile)
logging.info('Apikey: %s', _apikey)
logging.info('Device: %s', _device)
logging.info('Client Id : %s', _client_id)
logging.info('*-------------------------------------------------------------------------*')

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

try:
	jeedom_utils.write_pid(str(_pidfile))
	jeedom_com = jeedom_com(apikey = _apikey,url = _callback,cycle=_cycle) # création de l'objet jeedom_com
	if not jeedom_com.test(): #premier test pour vérifier que l'url de callback est correcte
		logging.error('Network communication issues. Please fixe your Jeedom network configuration.')
		shutdown()

	jeedom_socket = jeedom_socket(port=_socket_port,address=_socket_host)
	listen()
except Exception as e:
	logging.error('Fatal error: %s', e)
	logging.info(traceback.format_exc())
	shutdown()
