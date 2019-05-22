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


from hue_bridge.logger import root_logger
from hue_bridge.configuration import config
from hue_bridge.discovery import discoverBridge
from hue_bridge.device_manager import DeviceManager
from hue_bridge.monitor import Monitor
from hue_bridge.controller import Controller
from time import sleep
import cc_lib


logger = root_logger.getChild(__name__)

device_manager = DeviceManager()


def on_connect(client: cc_lib.client.Client):
    devices = device_manager.devices
    for device in devices.values():
        try:
            if device.state["reachable"]:
                client.connectDevice(device, asynchronous=True)
        except cc_lib.client.exception.DeviceConnectError:
            pass


connector_client = cc_lib.client.Client()
connector_client.setConnectClbk(on_connect)

bridge_monitor = Monitor(device_manager, connector_client, config.Bridge.id)
bridge_controller = Controller(device_manager, connector_client, config.Bridge.id)


if __name__ == '__main__':
    discoverBridge()
    while True:
        try:
            connector_client.initHub()
            break
        except cc_lib.client.HubInitializationError:
            sleep(10)
    connector_client.connect(reconnect=True)
    bridge_monitor.start()
    bridge_controller.start()
    try:
        bridge_monitor.join()
        bridge_controller.join()
    except KeyboardInterrupt:
        print("\ninterrupted by user\n")
