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


# if __name__ == '__main__':
#     exit('Please use "client.py"')


#from .configuration import config
from rgbxy import Converter, get_light_gamut
from threading import Lock
import cc_lib


converter_pool = dict()

def getConverter(model: str):
    if not model in converter_pool:
        converter = Converter(get_light_gamut(model))
        converter_pool[model] = converter
        return converter
    return converter_pool[model]


class ExtendedColorLight(cc_lib.types.Device):
    uri = "iot#94e1bbee-7d04-4117-aba3-968a1b246222"
    description = "Device type for Hue color lamp and lightstrip plus"

    def __init__(self, id: str, name: str, model: str, state: dict, number: str):
        self.id = id
        self.name = name
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

    def __iter__(self):
        items = (
            ("name", self.name),
            ("model", self.model),
            ("state", self.state),
            ("number", self.number)
        )
        for item in items:
            yield item

    class setColorInput:
        red = int
        green = int
        blue = int

    class setColorOutput:
        status = int

    @cc_lib.device.service(input=setColorInput, output=setColorOutput)
    def setColor(self, red: int, green: int, blue: int):
        return {"xy": getConverter(self.model).rgb_to_xy(red, green, blue)}

    class setOnOutput:
        status = int

    @cc_lib.device.service(output=setOnOutput)
    def setOn(self):
        return {"on": True}

    class setOffOutput:
        status = int

    @cc_lib.device.service(output=setOffOutput)
    def setOff(self):
        return {"on": False}

    class setBrightnessInput:
        brightness = int

    class setBrightnessOutput:
        status = int

    @cc_lib.device.service(input=setBrightnessInput, output=setBrightnessOutput)
    def setBrightness(self, brightness):
        return {"bri": brightness}

    class getStateOutput:
        on = bool
        brightness = int
        red = int
        green = int
        blue = int

    @cc_lib.device.service(output=getStateOutput)
    def getState(self):
        pass


device_type_map = {
    "Extended color light": ExtendedColorLight
}
