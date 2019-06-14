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


from simple_conf import configuration, section
import os, inspect


@configuration
class HueConf:

    @section
    class Bridge:
        host = None
        api_path = "api"
        api_key = None
        id = None

    @section
    class Cloud:
        host = "www.meethue.com"
        api_path = "api"

    @section
    class Senergy:
        dt_extended_color_light = None
        st_set_color = None
        st_set_on = None
        st_set_off = None
        st_set_brightness = None
        st_get_status = None

    @section
    class Logger:
        level = "info"


config = HueConf('bridge.conf', os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))


if not all((config.Bridge.id, config.Bridge.api_path, config.Bridge.api_key, config.Cloud.host, config.Cloud.api_path)):
    exit('Please provide Hue Bridge information')

if not config.Senergy.device_type:
    exit('Please provide a SENERGY device type')
