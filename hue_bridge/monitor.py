"""
   Copyright 2018 SEPL Team

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

if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from connector_client.modules.http_lib import Methods as http
    from connector_client.client import Client
    from connector_client.device import Device
    from hue_bridge.configuration import BRIDGE_API_KEY, BRIDGE_API_PATH, BRIDGE_HOST, BRIDGE_PORT, SEPL_DEVICE_TYPE
    from connector_client.modules.device_pool import DevicePool
    from hue_bridge.logger import root_logger
    from rgbxy import Converter, get_light_gamut
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json, time
from threading import Thread


logger = root_logger.getChild(__name__)


class Monitor(Thread):
    bridge_map = dict()
    _known_devices = dict()

    def __init__(self):
        super().__init__()
        unknown_devices= self._queryBridge()
        self._evaluate(unknown_devices, True)
        self.start()


    def run(self):
        while True:
            time.sleep(30)
            unknown_devices = self._queryBridge()
            self._evaluate(unknown_devices, False)


    def _queryBridge(self):
        unknown_lights = dict()
        response = http.get(
            'http://{}:{}/{}/{}/lights'.format(
                BRIDGE_HOST,
                BRIDGE_PORT,
                BRIDGE_API_PATH,
                BRIDGE_API_KEY
            )
        )
        if response.status == 200:
            lights = json.loads(response.body)
            for light_key in lights:
                light = lights.get(light_key)
                light['LIGHT_KEY'] = light_key
                light_id = light.get('uniqueid')
                unknown_lights[light_id] = light
        else:
            logger.error("could not query lights - '{}'".format(response.status))
        return unknown_lights


    def _diff(self, known, unknown):
        known_set = set(known)
        unknown_set = set(unknown)
        missing = known_set - unknown_set
        new = unknown_set - known_set
        changed = {k for k in known_set & unknown_set if known[k] != unknown[k]}
        return missing, new, changed


    def _evaluate(self, unknown_devices, init):
        missing_devices, new_devices, changed_devices = self._diff(__class__._known_devices, unknown_devices)
        if missing_devices:
            for missing_device_id in missing_devices:
                logger.info("can't find '{}' with id '{}'".format(__class__._known_devices[missing_device_id].get('name'), missing_device_id))
                del __class__.bridge_map[missing_device_id]
                if init:
                    DevicePool.remove(missing_device_id)
                else:
                    Client.disconnect(missing_device_id)
        if new_devices:
            for new_device_id in new_devices:
                name = unknown_devices[new_device_id].get('name')
                logger.info("found '{}' with id '{}'".format(name, new_device_id))
                __class__.bridge_map[new_device_id] = (unknown_devices[new_device_id].get('LIGHT_KEY'), Converter(get_light_gamut(unknown_devices[new_device_id].get('modelid'))))
                device = Device(new_device_id, SEPL_DEVICE_TYPE, name)
                device.addTag('type', unknown_devices[new_device_id].get('type'))
                device.addTag('manufacturer', unknown_devices[new_device_id].get('manufacturername'))
                if init:
                    DevicePool.add(device)
                else:
                    Client.add(device)
        if changed_devices:
            for changed_device_id in changed_devices:
                device = DevicePool.get(changed_device_id)
                name = unknown_devices[changed_device_id].get('name')
                if not name == device.name:
                    device.name = name
                    if init:
                        DevicePool.update(device)
                    else:
                        Client.update(device)
                    logger.info("name of '{}' changed to {}".format(changed_device_id, name))
        __class__._known_devices = unknown_devices
