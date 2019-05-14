"""
   Copyright 2018 InfAI (CC SES)

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

try:
    from simple_conf import configuration, section
    from connector_lib.modules.logger import connector_lib_log_handler
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
import logging, os, inspect


logger = logging.getLogger('simple-conf')
logger.addHandler(connector_lib_log_handler)


@configuration
class HueConf:

    @section
    class Bridge:
        host = None
        port = 80
        api_path = 'api'
        api_key = None
        id = None

    @section
    class Cloud:
        host = 'www.meethue.com'
        api_path = 'api'

    @section
    class Senergy:
        device_type = None


config = HueConf('bridge.conf', os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))


if not all((config.Bridge.id, config.Bridge.port, config.Bridge.api_path, config.Bridge.api_key, config.Cloud.host, config.Cloud.api_path)):
    exit('Please provide Hue Bridge information')

if not config.Senergy.device_type:
    exit('Please provide a SENERGY device type')
