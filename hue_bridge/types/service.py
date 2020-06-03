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


__all__ = ('SetPower', 'SetBrightness', 'SetKelvin', 'SetColor', 'GetStatus', 'PlugSetPower', 'PlugGetStatus', 'GetStatusCL')


if __name__ == '__main__':
    exit('Please use "client.py"')


from ..configuration import config
from ..logger import root_logger
from rgbxy import Converter, GamutB, GamutC, GamutA
from requests import put, get, exceptions
import cc_lib, colorsys, datetime


logger = root_logger.getChild(__name__.split(".", 1)[-1])

converter_pool = dict()


def getGamut(model_id):
    # https://developers.meethue.com/develop/hue-api/supported-devices/
    if model_id in ("LCT001", "LCT007", "LCT002", "LCT003", "LLM001"):
        return GamutB
    elif model_id in ("LCT010", "LCT014", "LCT015", "LCT016", "LCT011", "LLC020", "LST002", "LCT012", "LCT024"):
        return GamutC
    elif model_id in ("LLC010", "LLC006", "LST001", "LLC011", "LLC012", "LLC005", "LLC007", "LLC014"):
        return GamutA
    else:
        logger.warning("Model '{}' not supported - defaulting to Gamut C")
        return GamutC


def getConverter(model: str):
    if not model in converter_pool:
        converter = Converter(getGamut(model))
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


class SetColor(cc_lib.types.Service):
    local_id = "setColor"

    @staticmethod
    def task(device, hue: int, saturation: int, brightness: int, duration: float):
        err, body = hueBridgePut(
            device.number,
            {
                "on": True,
                "xy": getConverter(device.model).rgb_to_xy(*convertHSBToRGB(hue, saturation, brightness or 1)),
                "bri": round(brightness * 255 / 100),
                "transitiontime": int(duration * 10)
            }
        )
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, body))
        return {"status": int(err)}


# class SetOn(cc_lib.types.Service):
#     local_id = "setOn"
#
#     @staticmethod
#     def task(device, duration):
#         err, body = hueBridgePut(device.number, {"on": True, "transitiontime": int(duration * 10)})
#         if err:
#             logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
#         return {"status": int(err)}
#
#
# class SetOff(cc_lib.types.Service):
#     local_id = "setOff"
#
#     @staticmethod
#     def task(device, duration):
#         err, body = hueBridgePut(device.number, {"on": False, "transitiontime": int(duration * 10)})
#         if err:
#             logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
#         return {"status": int(err)}


# class SetPower(cc_lib.types.Service):
#     local_id = "setPower"
#
#     @staticmethod
#     def task(device, power, duration):
#         err, body = hueBridgePut(device.number, {"on": power, "transitiontime": int(duration * 10)})
#         if err:
#             logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, body))
#         return {"status": int(err)}


class SetPower(cc_lib.types.Service):
    local_id = "setPower"

    @staticmethod
    def task(device, power):
        err, body = hueBridgePut(device.number, {"on": power})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, body))
        return {"status": int(err)}


class SetBrightness(cc_lib.types.Service):
    local_id = "setBrightness"

    @staticmethod
    def task(device, brightness, duration):
        err, body = hueBridgePut(
            device.number,
            {"on": True, "bri": round(brightness * 255 / 100), "transitiontime": int(duration * 10)}
        )
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, body))
        return {"status": int(err)}


class SetKelvin(cc_lib.types.Service):
    local_id = "setKelvin"

    @staticmethod
    def task(device, kelvin, brightness, duration):
        err, body = hueBridgePut(
            device.number,
            {
                "on": True,
                "ct": round(1000000 / kelvin),
                "bri": round(brightness * 255 / 100),
                "transitiontime": int(duration * 10)
            }
        )
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, body))
        return {"status": int(err)}


class GetStatus(cc_lib.types.Service):
    local_id = "getStatus"

    @staticmethod
    def task(device):
        payload = {
                "status": 0,
                "on": False,
                "hue": 0,
                "saturation": 0,
                "brightness": 0,
                "kelvin": 0,
                "time": "{}Z".format(datetime.datetime.utcnow().isoformat())
            }
        err, body = hueBridgeGet(device.number)
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, body))
        else:
            hsb = convertRGBToHSB(*getConverter(device.model).xy_to_rgb(body["xy"][0], body["xy"][1]))
            payload["on"] = body["on"]
            payload["hue"] = hsb[0]
            payload["saturation"] = hsb[1]
            payload["brightness"] = hsb[2]
            payload["kelvin"] = round(round(1000000 / body["ct"]) / 10) * 10
        payload["status"] = int(err)
        return payload


class GetStatusCL(cc_lib.types.Service):
    local_id = "getStatus"

    @staticmethod
    def task(device):
        payload = {
                "status": 0,
                "on": False,
                "hue": 0,
                "saturation": 0,
                "brightness": 0,
                "time": "{}Z".format(datetime.datetime.utcnow().isoformat())
            }
        err, body = hueBridgeGet(device.number)
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, body))
        else:
            hsb = convertRGBToHSB(*getConverter(device.model).xy_to_rgb(body["xy"][0], body["xy"][1]))
            payload["on"] = body["on"]
            payload["hue"] = hsb[0]
            payload["saturation"] = hsb[1]
            payload["brightness"] = hsb[2]
        payload["status"] = int(err)
        return payload


### On/Off plug-in unit ###


# class PlugSetOn(cc_lib.types.Service):
#     local_id = "setOn"
#
#     @staticmethod
#     def task(device):
#         err, body = hueBridgePut(device.number, {"on": True})
#         if err:
#             logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
#         return {"status": int(err)}
#
#
# class PlugSetOff(cc_lib.types.Service):
#     local_id = "setOff"
#
#     @staticmethod
#     def task(device):
#         err, body = hueBridgePut(device.number, {"on": False})
#         if err:
#             logger.error("'{}' for '{}' failed - {}".format(__class__.name, device.id, body))
#         return {"status": int(err)}


class PlugSetPower(cc_lib.types.Service):
    local_id = "setPower"

    @staticmethod
    def task(device, power):
        err, body = hueBridgePut(device.number, {"on": power})
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, body))
        return {"status": int(err)}


class PlugGetStatus(cc_lib.types.Service):
    local_id = "getStatus"

    @staticmethod
    def task(device):
        payload = {
                "status": 0,
                "on": False,
                "time": "{}Z".format(datetime.datetime.utcnow().isoformat())
            }
        err, body = hueBridgeGet(device.number)
        if err:
            logger.error("'{}' for '{}' failed - {}".format(__class__.__name__, device.id, body))
        else:
            payload["on"] = body["on"]
        payload["status"] = int(err)
        return payload
