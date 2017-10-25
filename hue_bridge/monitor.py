if __name__ == '__main__':
    exit('Please use "client.py"')

try:
    from modules.http_lib import Methods as http
    from modules.logger import root_logger
    from connector.client import Client
    from connector.device import Device
    from hue_bridge.configuration import BRIDGE_API_KEY, BRIDGE_API_PATH, BRIDGE_HOST, BRIDGE_PORT
    from modules.device_pool import DevicePool
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import json, time
from threading import Thread


logger = root_logger.getChild(__name__)


class Monitor(Thread):
    bridge_map = dict()
    _known_devices = dict()
    _known_groups = dict()

    def __init__(self):
        super().__init__()
        unknown_devices, unknown_groups = self._queryDeconz()
        if unknown_devices or unknown_groups:
            self._evaluate(unknown_devices, unknown_groups, True)
        self.start()


    def run(self):
        while True:
            time.sleep(30)
            unknown_devices, unknown_groups = self._queryDeconz()
            if unknown_devices or unknown_groups:
                self._evaluate(unknown_devices, unknown_groups, False)


    def _queryDeconz(self):
        unknown_lights = dict()
        unknown_groups = dict()
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
        """
        response = http.get(
            'http://{}:{}/{}/{}/groups'.format(
                BRIDGE_HOST,
                BRIDGE_PORT,
                BRIDGE_API_PATH,
                BRIDGE_API_KEY
            )
        )
        if response.status == 200:
            groups = json.loads(response.body)
            for group_key in groups:
                group = groups.get(group_key)
                group['GROUP_KEY'] = group_key
                unknown_groups[group_key] = group
        else:
            logger.error("could not query groups - '{}'".format(response.status))
        """
        return unknown_lights, unknown_groups


    def _diff(self, known, unknown):
        known_set = set(known)
        unknown_set = set(unknown)
        missing = known_set - unknown_set
        new = unknown_set - known_set
        changed = {k for k in known_set & unknown_set if known[k] != unknown[k]}
        return missing, new, changed


    def _evaluate(self, unknown_devices, unknown_groups, init):
        missing_devices, new_devices, changed_devices = self._diff(__class__._known_devices, unknown_devices)
        #missing_groups, new_groups, changed_groups = self._diff(__class__._known_groups, unknown_groups)
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
                __class__.bridge_map[new_device_id] = unknown_devices[new_device_id].get('LIGHT_KEY')
                device = Device(new_device_id, 'iot#f730843d-ca6b-48f4-a58b-c53a7f7ee062', name)
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
        """
        if missing_groups:
            for missing_group_id in missing_groups:
                logger.info(
                    "can't find '{}' with id '{}'".format(__class__._known_groups[missing_group_id].get('name'), missing_group_id))
                del __class__.bridge_map[missing_group_id]
                if init:
                    DevicePool.remove(missing_group_id)
                else:
                    Client.disconnect(missing_group_id)
        if new_groups:
            for new_group_id in new_groups:
                name = unknown_groups[new_group_id].get('name')
                logger.info("found '{}' with id '{}'".format(name, new_group_id))
                __class__.bridge_map['{}-{}'.format(BRIDGE_API_KEY, new_group_id)] = unknown_groups[new_group_id].get('GROUP_KEY')
                device_group = Device('{}-{}'.format(BRIDGE_API_KEY, new_group_id), 'iot#e01b3099-7ced-49d7-b660-22103b2bc1e4', name)
                device_group.addTag('type', unknown_groups[new_group_id].get('type'))
                device_group.addTag('manufacturer', 'Philips')
                if init:
                    DevicePool.add(device_group)
                else:
                    Client.disconnect(device_group)
        if changed_groups:
            for changed_group_id in changed_groups:
                device_group = DevicePool.get('{}-{}'.format(BRIDGE_API_KEY, changed_group_id))
                name = unknown_groups[changed_group_id].get('name')
                if not name == device_group.name:
                    device_group.name = name
                    if init:
                        DevicePool.update(device_group)
                    else:
                        Client.update(device_group)
                    logger.info("name of '{}' changed to {}".format(changed_group_id, name))
        """
        __class__._known_devices = unknown_devices
        #__class__._known_groups = unknown_groups
