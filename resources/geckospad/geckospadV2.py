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

import datetime
import logging
import argparse
import sys
import os
import signal
import json
import asyncio
import functools
import uuid

from config import Config
from jeedom.utils import Utils
from jeedom.aio_connector import Listener, Publisher
from geckolib import GeckoAsyncSpaMan, GeckoSpaEvent

SPA_ADDRESS = None

class GeckoSpaMan(GeckoAsyncSpaMan):
	async def handle_event(self, event: GeckoSpaEvent, **kwargs) -> None:
		# Uncomment this line to see events generated
		# print(f"{event}: {kwargs}")
		#_LOGGER.info("received event : " + event + " | args : " + kwargs)
		_LOGGER.info("ChD received event -> " + event.name)
		pass

class GeckoSpa:	
	def __init__(self, config: Config) -> None:
		self._config = config
		self._jeedom_publisher = None
		self._listen_task = None
		self._send_task = None
		self._auto_reconnect_task = None
		self._loop = None
		self._logger = logging.getLogger(__name__)
		self._facade = None

	async def main(self):
		_LOGGER.info('   main')
		self._jeedom_publisher = Publisher(self._config.callback_url, self._config.api_key, self._config.cycle)
		if not await self._jeedom_publisher.test_callback():
			return

		self._loop = asyncio.get_running_loop()
		_LOGGER.info('ChD   before _connectingToSpas -> ')
		await self._connectingToSpas()
		_LOGGER.info('ChD    after _connectingToSpas -> ')
		self._listen_task = Listener.create_listen_task(self._config.socket_host, self._config.socket_port, self._on_socket_message)
		_LOGGER.info('ChD    _auto_reconnect_task')        
		#self._auto_reconnect_task = asyncio.create_task(self._auto_reconnect())

		_LOGGER.info('ChD    add_signal_handler') 
		await self.add_signal_handler()
		_LOGGER.info('ChD    asyncio.sleep(1)')         
		await asyncio.sleep(1) # allow  all tasks to start
		_LOGGER.info("Ready")
		#_LOGGER.info('ChD    asyncio.gather')        
		#await asyncio.gather(self._auto_reconnect_task, self._listen_task, self._send_task)
		#_LOGGER.info('ChD    after asyncio.gather')

	async def _auto_reconnect(self):
		_LOGGER.info('   ChD before _auto_reconnect -> ')
		try:
			if self._facade is not None:
				while not self._facade.is_connected:
					_LOGGER.info('   ChD facade not connected ')
					await self._connectingToSpas()
			else:
				_LOGGER.info('   ChD facade connected ')
				#await self._connectingToSpas()
		except asyncio.CancelledError:
			_LOGGER.info('   ChD  error auto_reconnect task ')          		

	async def _connectingToSpas(self):
			async with GeckoSpaMan(self._config.clientId, spa_address=SPA_ADDRESS) as spaman:
				_LOGGER.info("ChD Looking for spas on your network ...")

				# Wait for descriptors to be available
				await spaman.wait_for_descriptors()

				if len(spaman.spa_descriptors) == 0:
					_LOGGER.info("ChD **** There were no spas found on your network.")
					return

				spa_descriptor = spaman.spa_descriptors[0]
				_LOGGER.info("ChD Connecting to " + spa_descriptor.name +" at " + spa_descriptor.ipaddress +" ...")
				await spaman.async_set_spa_info(
					spa_descriptor.ipaddress,
					spa_descriptor.identifier_as_string,
					spa_descriptor.name,
				)

				# Wait for the facade to be ready
				await spaman.wait_for_facade()
				self._facade=spaman.facade

	async def add_signal_handler(self):
		self._loop.add_signal_handler(signal.SIGINT, functools.partial(self._ask_exit, signal.SIGINT))
		self._loop.add_signal_handler(signal.SIGTERM, functools.partial(self._ask_exit, signal.SIGTERM))

	def _ask_exit(self, sig):
		self._logger.info("ChD Signal %i caught, exiting...", sig)
		self.close()

	def close(self):
		self._auto_reconnect_task.cancel()
		self._listen_task.cancel()
		self._send_task.cancel()

	def _on_message(self, name):
		#tmpDevice = self._get_device_to_send(device)
		_LOGGER.debug("ChD _on_message")
		#self._loop.create_task(self.__format_and_send('update::' + device.uuid, tmpDevice))

	async def _on_socket_message(self, message):
		if message['apikey'] != self._config.api_key:
			_LOGGER.error('ChD Invalid apikey from socket : %s', str(message))
			return
		try:
			if message['action'] == 'stop':
				self.close()
			elif message['action'] == 'synchronize':
				_LOGGER.info('ChD  _on_socket_message -> synchronize')	
				#self._worxcloud.fetch()
				#await self._send_devices()
			elif message['action'] == 'get_activity_logs':
				#device = self._worxcloud.get_device_by_serial_number(message['serial_number'])
				#await self.__format_and_send('activity_logs::' + device.uuid, payload)
				_LOGGER.info('ChD  _on_socket_message -> _on_socket_message')				
			else:
				_LOGGER.info('ChD  else _on_socket_message')
				#await self._executeAction(message)
		except Exception as e:
			_LOGGER.error('ChD Send command to daemon error: %s', e)

	async def __format_and_send(self, key, data):
		payload = json.loads(json.dumps(data, default=lambda d: self.__encoder(d)))
		await self._jeedom_publisher.add_change(key, payload)

def shutdown():
	_LOGGER.info("ChD Shuting down")
	try:
		_LOGGER.debug("ChD Removing PID file %s", config.pid_filename)
		os.remove(config.pid_filename)
	except:
		pass

	_LOGGER.debug("Exit 0")
	sys.stdout.flush()
	os._exit(0)
# ----------------------------------------------------------------------------
parser = argparse.ArgumentParser(
description='Desmond Daemon for Jeedom plugin')
parser.add_argument("--device", help="Device", type=str)
parser.add_argument("--loglevel", help="Log Level for the daemon", type=str)
parser.add_argument("--callback", help="Callback", type=str)
parser.add_argument("--apikey", help="Apikey", type=str)
parser.add_argument("--pid", help="Pid file", type=str)
parser.add_argument("--socketport", help="Daemon port", type=str)
parser.add_argument("--clientId", help="Client Id", type=str)

args = parser.parse_args()
config = Config(**vars(args))
Utils.init_logger(config.log_level)
_LOGGER = logging.getLogger(__name__)
logging.getLogger('asyncio').setLevel(logging.WARNING)
#logging.getLogger('pyworxcloud').setLevel(Utils.convert_log_level(config.log_level))

try:
	_LOGGER.info('Starting daemon')
	_LOGGER.info('Log level: %s', config.log_level)
	Utils.write_pid(str(config.pid_filename))

	geckospa = GeckoSpa(config)
	asyncio.run(geckospa.main())
except Exception as e:
	exception_type, exception_object, exception_traceback = sys.exc_info()
	filename = exception_traceback.tb_frame.f_code.co_filename
	line_number = exception_traceback.tb_lineno
	_LOGGER.error('ChD Fatal error: %s(%s) in %s on line %s', e, exception_type, filename, line_number)
shutdown()