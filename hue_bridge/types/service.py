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


__all__ = ('SetBrightness', 'SetOff', 'SetOn', 'SetKelvin', 'SetColor', 'GetStatus', 'PlugSetOn', 'PlugSetOff', 'PlugGetStatus')


if __name__ == '__main__':
    exit('Please use "client.py"')


from ..configuration import config
from ..logger import root_logger
from rgbxy import Converter, get_light_gamut
from requests import put, get, exceptions
import cc_lib, colorsys


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


def convertHSBToRGB(hue, sat, bri):
    return tuple(round(val * 255) for val in colorsys.hsv_to_rgb(hue / 360, sat / 100, bri / 100))


def convertRGBToHSB(red, green, blue):
    hue, saturation, brightness = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    return (round(hue * 360), round(saturation * 100), round(brightness * 100))


### Extended color light ###


# @cc_lib.types.actuator_service
# class SetColor:
#     uri = config.Senergy.st_set_color
#     name = "Set Color RGB"
#     description = "Set light color via Red, Green and Blue values."
#
#     @staticmethod
#     def task(device, red: int, green: int, blue: int):
#         err, body = hueBridgePut(
#             device.number,
#             {"on": True, "xy": getConverter(device.model).rgb_to_xy(red, green, blue)}
#         )
#         if err:
#             logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
#         return {"status": int(err)}


@cc_lib.types.actuator_service
class SetColor:
    uri = config.Senergy.st_set_color
    name = "Set Color"
    description = "Set light color via Hue, Saturation and Brightness values."

    @staticmethod
    def task(device, hue: int, saturation: int, brightness: int, duration: float):
        err, body = hueBridgePut(
            device.number,
            {
                "on": True,
                "xy": getConverter(device.model).rgb_to_xy(*convertHSBToRGB(hue, saturation, brightness)),
                "bri": round(brightness * 255 / 100),
                "transitiontime": int(duration * 10)
            }
        )
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.actuator_service
class SetOn:
    uri = config.Senergy.st_set_on
    name = "Set On"
    description = "Turn on light."

    @staticmethod
    def task(device, duration):
        err, body = hueBridgePut(device.number, {"on": True, "transitiontime": int(duration * 10)})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.actuator_service
class SetOff:
    uri = config.Senergy.st_set_off
    name = "Set Off"
    description = "Turn off light."

    @staticmethod
    def task(device, duration):
        err, body = hueBridgePut(device.number, {"on": False, "transitiontime": int(duration * 10)})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.actuator_service
class SetBrightness:
    uri = config.Senergy.st_set_brightness
    name = "Set Brightness"
    description = "Set light brightness."

    @staticmethod
    def task(device, brightness, duration):
        err, body = hueBridgePut(device.number, {"on": True, "bri": brightness, "transitiontime": int(duration * 10)})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.actuator_service
class SetKelvin:
    uri = config.Senergy.st_set_kelvin
    name = "Set Kelvin"
    description = "Set light kelvin temperature."

    @staticmethod
    def task(device, kelvin, duration):
        err, body = hueBridgePut(
            device.number,
            {"on": True, "ct": convertKelvinToMired(kelvin), "transitiontime": int(duration * 10)}
        )
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.sensor_service
class GetStatus:
    uri = config.Senergy.st_get_status
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


### On/Off plug-in unit ###


@cc_lib.types.actuator_service
class PlugSetOn:
    uri = config.Senergy.st_plug_set_on
    name = "Set On"
    description = "Turn on plug."

    @staticmethod
    def task(device):
        err, body = hueBridgePut(device.number, {"on": True})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.actuator_service
class PlugSetOff:
    uri = config.Senergy.st_plug_set_off
    name = "Set Off"
    description = "Turn off plug."

    @staticmethod
    def task(device):
        err, body = hueBridgePut(device.number, {"on": False})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        return {"status": int(err)}


@cc_lib.types.sensor_service
class PlugGetStatus:
    uri = config.Senergy.st_plug_get_status
    name = "Get Status"
    description = "Get plug status parameters."

    @staticmethod
    def task(device):
        payload = {
                "status": 0,
                "on": False
            }
        err, body = hueBridgeGet(device.number)
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
        else:
            payload["on"] = body["on"]
        payload["status"] = int(err)
        return payload