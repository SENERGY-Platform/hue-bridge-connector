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


__all__ = ('device_type_map', 'ExtendedColorLight')

if __name__ == '__main__':
    exit('Please use "client.py"')


from .service import SetColor, SetOn, SetOff, SetBrightness, GetStatus, PlugSetOn, PlugSetOff, PlugGetStatus
from threading import Lock
from ..configuration import config
import cc_lib


class ExtendedColorLight(cc_lib.types.Device):
    uri = config.Senergy.dt_extended_color_light
    description = "Device type for Hue color lamp and lightstrip plus"
    services = {
        'setOn': SetOn,
        'setOff': SetOff,
        'setColor': SetColor,
        'setBrightness': SetBrightness,
        'getStatus': GetStatus
    }

    def __init__(self, id: str, name: str, model: str, state: dict, number: str):
        self.id = id
        self.name = name
        self.model = model
        self.number = number
        self.__state_lock = Lock()
        self.state = state

    @property
    def state(self):
        with self.__state_lock:
            return self.__state

    @state.setter
    def state(self, arg):
        with self.__state_lock:
            self.__state = arg

    def getService(self, srv_handler: str, *args, **kwargs):
        service = super().getService(srv_handler)
        return service.task(self, *args, **kwargs)

    def __iter__(self):
        items = (
            ("name", self.name),
            ("model", self.model),
            ("state", self.state),
            ("number", self.number)
        )
        for item in items:
            yield item


class OnOffPlugInUnit(cc_lib.types.Device):
    uri = config.Senergy.dt_on_off_plug_in_unit
    description = "Device type for On/Off plug-in unit"
    services = {
        'setOn': PlugSetOn,
        'setOff': PlugSetOff,
        'getStatus': PlugGetStatus
    }

    def __init__(self, id: str, name: str, model: str, state: dict, number: str):
        self.id = id
        self.name = name
        self.model = model
        self.number = number
        self.__state_lock = Lock()
        self.state = state

    @property
    def state(self):
        with self.__state_lock:
            return self.__state

    @state.setter
    def state(self, arg):
        with self.__state_lock:
            self.__state = arg

    def getService(self, srv_handler: str, *args, **kwargs):
        service = super().getService(srv_handler)
        return service.task(self, *args, **kwargs)

    def __iter__(self):
        items = (
            ("name", self.name),
            ("model", self.model),
            ("state", self.state),
            ("number", self.number)
        )
        for item in items:
            yield item


device_type_map = {
    "Extended color light": ExtendedColorLight,
    "On/Off plug-in unit": OnOffPlugInUnit
}
