if __name__ == '__main__':
    exit('Please use "client.py"')

import os, configparser

conf_path = '{}/hue_bridge'.format(os.getcwd())
conf_file = 'bridge.conf'

config = configparser.ConfigParser()


if not os.path.isfile(os.path.join(conf_path, conf_file)):
    print('No config file found')
    config['BRIDGE'] = {
        'host': '',
        'port': '80',
        'api_path': 'api',
        'api_key': ''
    }
    config['SEPL'] = {
        'device_type': ''
    }
    with open(os.path.join(conf_path, conf_file), 'w') as cf:
        config.write(cf)
    exit("Created blank config file at '{}'".format(conf_path))


try:
    config.read(os.path.join(conf_path, conf_file))
except Exception as ex:
    exit(ex)


BRIDGE_HOST = config['BRIDGE']['host']
BRIDGE_PORT = config['BRIDGE']['port']
BRIDGE_API_PATH = config['BRIDGE']['api_path']
BRIDGE_API_KEY = config['BRIDGE']['api_key']
SEPL_DEVICE_TYPE = config['SEPL']['device_type']

if not BRIDGE_HOST or not BRIDGE_PORT:
    exit('Please provide Hue Bridge host and port')

if not BRIDGE_API_PATH:
    exit('Please provide Hue Bridge API path')

if not BRIDGE_API_KEY:
    exit('Please provide Hue Bridge API key')

if not SEPL_DEVICE_TYPE:
    exit('Please provide a SEPL device type')