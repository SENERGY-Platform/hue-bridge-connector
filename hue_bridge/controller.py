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
from threading import Thread
from queue import Queue, Empty
import time, json, cc_lib


logger = root_logger.getChild(__name__.split(".", 1)[-1])


class Worker(Thread):
    def __init__(self, device, client: cc_lib.client.Client):
        super().__init__(name="worker-{}".format(device.id), daemon=True)
        self.__device = device
        self.__client = client
        self.__stop = False
        self.__command_queue = Queue()

    def run(self) -> None:
        logger.debug("'{}': starting ...".format(self.name))
        while not self.__stop:
            try:
                command: cc_lib.client.message.CommandEnvelope = self.__command_queue.get(timeout=30)
                if time.time() - command.timestamp <= config.Controller.max_command_age:
                    logger.debug("{}: '{}'".format(self.name, command))
                    try:
                        if command.message.data:
                            data = self.__device.getService(command.service_uri, **json.loads(command.message.data))
                        else:
                            data = self.__device.getService(command.service_uri)
                        cmd_resp = cc_lib.client.message.Message(json.dumps(data))
                    except json.JSONDecodeError as ex:
                        logger.error("{}: could not parse command data - {}".format(self.name, ex))
                        cmd_resp = cc_lib.client.message.Message(json.dumps({"status": 1}))
                    except TypeError as ex:
                        logger.error("{}: could not parse command response data - {}".format(self.name, ex))
                        cmd_resp = cc_lib.client.message.Message(json.dumps({"status": 1}))
                    command.message = cmd_resp
                    logger.debug("{}: '{}'".format(self.name, command))
                    if command.completion_strategy == cc_lib.client.CompletionStrategy.pessimistic:
                        self.__client.sendResponse(command, asynchronous=True)
                else:
                    logger.warning(
                        "{}: dropped command - max age exceeded - correlation id: {}".format(
                            self.name,
                            command.correlation_id
                        )
                    )
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
                    time.sleep(config.Bridge.delay)
                except KeyError:
                    logger.error("received command for unknown device '{}'".format(command.device_id))
            except cc_lib.client.CommandQueueEmptyError:
                if time.time() - garbage_collector_time > 120:
                    self.__collectGarbage()
                    garbage_collector_time = time.time()

    def __collectGarbage(self):
        garbage_workers = set(self.__worker_pool) - set(self.__device_manager.devices)
        for worker_id in garbage_workers:
            worker = self.__worker_pool[worker_id]
            logger.debug("stopping '{}'".format(worker.name))
            worker.stop()
            del self.__worker_pool[worker_id]
