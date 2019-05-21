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
import time, requests, cc_lib


logger = root_logger.getChild(__name__.split(".", 1)[-1])

converter_pool = dict()


class Controller(Thread):
    def __init__(self, device_manager: DeviceManager, client: cc_lib.client.Client):
        super().__init__()
        self.daemon = True
        self.__device_manager = device_manager
        self.__client = client

    def run(self):
        while True:
            command = self.__client.receiveCommand()