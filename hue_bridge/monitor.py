"""
   Copyright 2019 InfAI (CC SES)

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


from .configuration import config
from .logger import root_logger
from .device_manager import DeviceManager
from .types.device import device_type_map
from threading import Thread
import time, requests, cc_lib


logger = root_logger.getChild(__name__.split(".", 1)[-1])


class Monitor(Thread):
    def __init__(self, device_manager: DeviceManager, client: cc_lib.client.Client, bridge_id: str):
        super().__init__(name="monitor-{}".format(bridge_id), daemon=True)
        self.__device_manager = device_manager
        self.__client = client

    def run(self):
        logger.info("starting '{}' ...".format(self.name))
        while True:
            queried_devices = self.__queryBridge()
            if queried_devices:
                self.__evaluate(queried_devices)
            time.sleep(10)

    def __queryBridge(self):
        try:
            response = requests.get(
                "https://{}/{}/{}/lights".format(config.Bridge.host, config.Bridge.api_path, config.Bridge.api_key),
                verify=False
            )
            if response.status_code == 200:
                response = response.json()
                devices = dict()
                for number, device in response.items():
                    try:
                        devices[device["uniqueid"]] = (
                            {
                                "name": device["name"],
                                "model": device["modelid"],
                                "state": device["state"],
                                "number": number
                            },
                            {
                                "product_name": device["productname"],
                                "manufacturer": device["manufacturername"],
                                "product_type": device["type"]
                            }
                        )
                    except KeyError as ex:
                        logger.error("could not parse device - {}".format(ex))
                        logger.debug(device)
                return devices
            else:
                logger.error("could not query bridge - '{}'".format(response.status_code))
        except requests.exceptions.RequestException as ex:
            logger.error("could not query bridge - '{}'".format(ex))

    def __diff(self, known: dict, unknown: dict):
        known_set = set(known)
        unknown_set = set(unknown)
        missing = known_set - unknown_set
        new = unknown_set - known_set
        changed = {key for key in known_set & unknown_set if dict(known[key]) != unknown[key][0]}
        return missing, new, changed

    def __evaluate(self, queried_devices):
        missing_devices, new_devices, changed_devices = self.__diff(self.__device_manager.devices, queried_devices)
        updated_devices = list()
        if missing_devices:
            futures = list()
            for device_id in missing_devices:
                logger.info("can't find '{}' with id '{}'".format(
                    self.__device_manager.get(device_id).name, device_id)
                )
                futures.append((device_id, self.__client.deleteDevice(device_id, asynchronous=True)))
            for device_id, future in futures:
                future.wait()
                try:
                    future.result()
                    self.__device_manager.delete(device_id)
                except cc_lib.client.DeviceDeleteError:
                    try:
                        self.__client.disconnectDevice(device_id)
                    except (cc_lib.client.DeviceDisconnectError, cc_lib.client.NotConnectedError):
                        pass
        if new_devices:
            futures = list()
            for device_id in new_devices:
                device = device_type_map[queried_devices[device_id][1]["product_type"]](device_id, **queried_devices[device_id][0])
                logger.info("found '{}' with id '{}'".format(device.name, device.id))
                futures.append((device, self.__client.addDevice(device, asynchronous=True)))
            for device, future in futures:
                future.wait()
                try:
                    future.result()
                    self.__device_manager.add(device)
                    if device.state["reachable"]:
                        self.__client.connectDevice(device, asynchronous=True)
                except (cc_lib.client.DeviceAddError, cc_lib.client.DeviceUpdateError):
                    pass
        if changed_devices:
            futures = list()
            for device_id in changed_devices:
                device = self.__device_manager.get(device_id)
                prev_device_name = device.name
                prev_device_reachable_state = device.state["reachable"]
                device.name = queried_devices[device_id][0]["name"]
                device.model = queried_devices[device_id][0]["model"]
                device.state = queried_devices[device_id][0]["state"]
                device.number = queried_devices[device_id][0]["number"]
                if device.state["reachable"] != prev_device_reachable_state:
                    if device.state["reachable"]:
                        self.__client.connectDevice(device, asynchronous=True)
                    else:
                        self.__client.disconnectDevice(device, asynchronous=True)
                if device.name != prev_device_name:
                    futures.append((device, prev_device_name, self.__client.updateDevice(device, asynchronous=True)))
            for device, prev_device_name, future in futures:
                future.wait()
                try:
                    future.result()
                    updated_devices.append(device.id)
                except cc_lib.client.DeviceUpdateError:
                    device.name = prev_device_name
        if any((missing_devices, new_devices, updated_devices)):
            try:
                self.__client.syncHub(list(self.__device_manager.devices.values()), asynchronous=True)
            except cc_lib.client.HubError:
                pass
