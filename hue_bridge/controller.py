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
from .device import Device
from rgbxy import Converter, get_light_gamut
from threading import Thread
from queue import Queue, Empty
import time, json, requests, cc_lib


logger = root_logger.getChild(__name__.split(".", 1)[-1])


converter_pool = dict()

def getConverter(model: str):
    if not model in converter_pool:
        converter = Converter(get_light_gamut(model))
        converter_pool[model] = converter
        return converter
    return converter_pool[model]


class Worker(Thread):
    def __init__(self, device: Device, client: cc_lib.client.Client):
        super().__init__(name="worker-{}".format(device.id), daemon=True)
        self.__device = device
        self.__client = client
        self.__stop = False
        self.__command_queue = Queue()

    def run(self) -> None:
        logger.debug("'{}': starting ...".format(self.name))
        while not self.__stop:
            try:
                command: cc_lib.client.message.Envelope = self.__command_queue.get(timeout=30)
                cmd_resp = cc_lib.client.message.Message("")
                try:
                    data = json.loads(command.message.data)
                    #######
                    data["xy"] = getConverter(self.__device.model).rgb_to_xy(data["r"], data["g"],data["b"])
                    del data["r"]
                    del data["g"]
                    del data["b"]
                    #####
                    bridge_resp = requests.put(
                        url="https://{}/{}/{}/lights/{}/state".format(
                            config.Bridge.host,
                            config.Bridge.api_path,
                            config.Bridge.api_key,
                            self.__device.number
                        ),
                        json=data,
                        verify=False
                    )
                    if not bridge_resp.status_code == 200:
                        logger.error(
                            "{}: error executing command on bridge - {}".format(self.name, bridge_resp.status_code)
                        )
                    cmd_resp.data = json.dumps(bridge_resp.status_code)
                except json.JSONDecodeError as ex:
                    logger.error("{}: could not parse command data - {}".format(self.name, ex))
                    cmd_resp.data = json.dumps(500)
                except requests.exceptions.RequestException as ex:
                    logger.error("{}: could not send command to bridge - {}".format(self.name, ex))
                    cmd_resp.data = json.dumps(500)
                command.message = cmd_resp
                self.__client.sendResponse(command, asynchronous=True)
            except Empty:
                pass
        del self.__device
        del self.__client
        del self.__command_queue
        logger.debug("'{}': quit".format(self.name))

    def stop(self):
        self.__stop = True

    def execute(self, command):
        self.__command_queue.put_nowait(command)


class Controller(Thread):
    def __init__(self, device_manager: DeviceManager, client: cc_lib.client.Client, bridge_id: str):
        super().__init__(name="controller-{}".format(bridge_id), daemon=True)
        self.__device_manager = device_manager
        self.__client = client
        self.__worker_pool = dict()

    def run(self):
        logger.info("starting '{}' ...".format(self.name))
        garbage_collector_time = time.time()
        while True:
            try:
                command = self.__client.receiveCommand(timeout=30)
                try:
                    device = self.__device_manager.get(command.device_id)
                    if not device.id in self.__worker_pool:
                        worker = Worker(device, self.__client)
                        worker.start()
                        self.__worker_pool[device.id] = worker
                    else:
                        worker = self.__worker_pool[device.id]
                    worker.execute(command)
                except KeyError:
                    logger.error("received command for unknown device '{}'".format(command.device_id))
            except cc_lib.client.CommandQueueEmptyError:
                if time.time() - garbage_collector_time > 120:
                    self.__collectGarbage()
                    garbage_collector_time = time.time()

    def __executeCommand(self, command: cc_lib.client.message.Envelope, device: Device):
        response_msg = cc_lib.client.message.Message("ok")
        command.message = response_msg
        self.__client.sendResponse(command)

    def __collectGarbage(self):
        logger.debug("running garbage collector ...")
        garbage_workers = set(self.__worker_pool) - set(self.__device_manager.devices)
        logger.debug("collected '{}' workers".format(len(garbage_workers)))
        for worker_id in garbage_workers:
            worker = self.__worker_pool[worker_id]
            logger.debug("stopping '{}'".format(worker.name))
            worker.stop()
            del self.__worker_pool[worker_id]
