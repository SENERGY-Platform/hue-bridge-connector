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


__all__ = ('SetBrightness', 'SetOff', 'SetOn', 'SetColor', 'GetStatus')


if __name__ == '__main__':
    exit('Please use "client.py"')


from ..configuration import config
from ..logger import root_logger
from rgbxy import Converter, get_light_gamut
from requests import put, get, exceptions
import cc_lib


logger = root_logger.getChild(__name__.split(".", 1)[-1])

converter_pool = dict()


def getConverter(model: str):
    if not model in converter_pool:
        converter = Converter(get_light_gamut(model))
        converter_pool[model] = converter
        return converter
    return converter_pool[model]


def hueBridgePut(d_number: str, data: dict):
    try:
        resp = put(
            url="https://{}/{}/{}/lights/{}/state".format(
                config.Bridge.host,
                config.Bridge.api_path,
                config.Bridge.api_key,
                d_number
            ),
            json=data,
            verify=False
        )
        if resp.status_code == 200:
            resp = resp.json()
            if isinstance(resp, list):
                if "success" in resp[0]:
                    return False, "ok"
                if "error" in resp[0]:
                    return True, resp[0]["error"]["description"]
            else:
                return True, "unknown error"
        else:
            return True, resp.status_code
    except exceptions.RequestException:
        return True, "could not send request to hue bridge"


def hueBridgeGet(d_number: str):
    try:
        resp = get(
            url="https://{}/{}/{}/lights/{}".format(
                config.Bridge.host,
                config.Bridge.api_path,
                config.Bridge.api_key,
                d_number
            ),
            verify=False
        )
        if resp.status_code == 200:
            resp = resp.json()
            if isinstance(resp, dict):
                return False, resp["state"]
            elif isinstance(resp, list):
                return True, resp[0]["error"]["description"]
            else:
                return True, "unknown error"
        else:
            return True, resp.status_code
    except exceptions.RequestException:
        return True, "could not send request to hue bridge"


@cc_lib.types.actuator_service
class SetColor:
    uri = "iot#5efb0b6a-041f-4da4-9d38-45ddffc789ad"
    name = "Set Color"
    description = "Set light color via RGB code."

    @staticmethod
    def task(device, red: int, green: int, blue: int):
        err, body = hueBridgePut(device.number, {"xy": getConverter(device.model).rgb_to_xy(red, green, blue)})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.actuator_service
class SetOn:
    uri = "iot#08e5e6f7-6f6a-424e-95ed-cda013b11475"
    name = "Set On"
    description = "Turn on light."

    @staticmethod
    def task(device):
        err, body = hueBridgePut(device.number, {"on": True})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.actuator_service
class SetOff:
    uri = "iot#97dd54ac-0b25-4f89-8442-706de10b30cc"
    name = "Set Off"
    description = "Turn off light."

    @staticmethod
    def task(device):
        err, body = hueBridgePut(device.number, {"on": False})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.actuator_service
class SetBrightness:
    uri = "iot#07d50e8f-e80f-4baa-8a74-debe93942fb6"
    name = "Set Brightness"
    description = "Set light brightness."

    @staticmethod
    def task(device, brightness):
        err, body = hueBridgePut(device.number, {"bri": brightness})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.sensor_service
class GetStatus:
    uri = "iot#ca8f7938-3869-49ec-abb4-34c34f7d8f34"
    name = "Get Status"
    description = "Get light status parameters."

    @staticmethod
    def task(device):
        payload = {
                "status": 0,
                "on": False,
                "red": 0,
                "green": 0,
                "blue": 0,
                "brightness": 0
            }
        err, body = hueBridgeGet(device.number)
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        else:
            rgb = getConverter(device.model).xy_to_rgb(body["xy"][0], body["xy"][1])
            payload["on"] = body["on"]
            payload["red"] = rgb[0]
            payload["green"] = rgb[1]
            payload["blue"] = rgb[2]
            payload["brightness"] = body["bri"]
        payload["status"] = int(err)
        return payload
