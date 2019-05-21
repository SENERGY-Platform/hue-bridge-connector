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
from threading import Lock
import cc_lib


class Device(cc_lib.device.Device):
    def __init__(self, id: str, name: str, model: str, state: dict, number: str):
        super().__init__(id, config.Senergy.device_type, name)
        self.__state_lock = Lock()
        self.model = model
        self.state = state
        self.number = number

    @property
    def state(self):
        with self.__state_lock:
            return self.__state

    @state.setter
    def state(self, arg):
        with self.__state_lock:
            self.__state = arg