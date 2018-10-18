"""
   Copyright 2018 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

try:
    from connector_client.modules.http_lib import Methods as http
    from connector_client.modules.device_pool import DevicePool
    from connector_client.client import Client
    from hue_bridge.configuration import BRIDGE_API_KEY, BRIDGE_API_PATH, BRIDGE_HOST, BRIDGE_PORT
    from hue_bridge.monitor import Monitor
    from hue_bridge.logger import root_logger
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from time import sleep
import json


logger = root_logger.getChild(__name__)


def bridgeController():
    while True:
        if Monitor.bridge_map:
            task = Client.receive()
            try:
                for part in task.payload.get('protocol_parts'):
                    if part.get('name') == 'data':
                        command = part.get('value')
                command = json.loads(command)
                command['xy'] = Monitor.bridge_map.get(task.payload.get('device_url'))[1].rgb_to_xy(command.get('r'), command.get('g'), command.get('b'))
                del command['r']
                del command['g']
                del command['b']
                command = json.dumps(command)
                http_resp = http.put(
                    'http://{}:{}/{}/{}/lights/{}/state'.format(
                        BRIDGE_HOST,
                        BRIDGE_PORT,
                        BRIDGE_API_PATH,
                        BRIDGE_API_KEY,
                        Monitor.bridge_map.get(task.payload.get('device_url'))[0]
                    ),
                    command,
                    headers={'Content-Type': 'application/json'}
                )
                if not http_resp.status == 200:
                    logger.error("could not route message to hue bridge - '{}'".format(http_resp.status))
                response = str(http_resp.status)
            except Exception as ex:
                logger.error("error handling task - '{}'".format(ex))
                response = '500'
            Client.response(task, response)
        else:
            logger.debug("waiting for device map to be populated")
            sleep(0.5)


if __name__ == '__main__':
    bridge_monitor = Monitor()
    connector_client = Client(device_manager=DevicePool)
    bridgeController()
