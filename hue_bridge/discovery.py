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

try:
    from connector_lib.modules.http_lib import Methods as http
    from connector_lib.modules.device_pool import DevicePool
    from hue_bridge.logger import root_logger
    from hue_bridge.configuration import config
except ImportError as ex:
    exit("{} - {}".format(__name__, ex.msg))
from subprocess import call, check_output, DEVNULL
from socket import gethostbyname, getfqdn
from threading import Thread
from platform import system
import time, json

logger = root_logger.getChild(__name__)


def ping(host) -> bool:
    return call(['ping', '-c', '2', '-t', '2', host], stdout=DEVNULL, stderr=DEVNULL) == 0

def getLocalIP() -> str:
    sys_type = system().lower()
    try:
        if 'linux' in sys_type:
            local_ip = check_output(['hostname', '-I']).decode()
            local_ip = local_ip.replace(' ', '')
            local_ip = local_ip.replace('\n', '')
            return local_ip
        elif 'darwin' in sys_type:
            local_ip = gethostbyname(getfqdn())
            if type(local_ip) is str and local_ip.count('.') == 3:
                return local_ip
        else:
            logger.critical("platform not supported")
            raise Exception
    except Exception as ex:
        exit("could not get local ip - {}".format(ex))
    return str()

def getIpRange(local_ip) -> list:
    split_ip = local_ip.rsplit('.', 1)
    base_ip = split_ip[0] + '.'
    if len(split_ip) > 1:
        ip_range = [str(base_ip) + str(i) for i in range(2,255)]
        ip_range.remove(local_ip)
        return ip_range
    return list()

def discoverHostsWorker(ip_range, alive_hosts):
    for ip in ip_range:
        if ping(ip):
            alive_hosts.append(ip)

def discoverHosts() -> list:
    ip_range = getIpRange(getLocalIP())
    alive_hosts = list()
    workers = list()
    bin = 0
    bin_size = 3
    if ip_range:
        for i in range(int(len(ip_range) / bin_size)):
            worker = Thread(target=discoverHostsWorker, name='discoverHostsWorker', args=(ip_range[bin:bin+bin_size], alive_hosts))
            workers.append(worker)
            worker.start()
            bin = bin + bin_size
        if ip_range[bin:]:
            worker = Thread(target=discoverHostsWorker, name='discoverHostsWorker', args=(ip_range[bin:], alive_hosts))
            workers.append(worker)
            worker.start()
        for worker in workers:
            worker.join()
    return alive_hosts

def getNUPnP() -> str:
    response = http.get('https://{}/{}/nupnp'.format(config.Cloud.host, config.Cloud.api_path), verify=False, retries=3, retry_delay=1)
    if response.status == 200:
        host_list = json.loads(response.body)
        for host in host_list:
            try:
                if host.get('id').upper() in config.Bridge.id:
                    return host.get('internalipaddress')
            except AttributeError:
                logger.error("could not extract host ip from '{}'".format(host))
    return str()

def validateHostsWorker(hosts, valid_hosts):
    for host in hosts:
        if validateHost(host):
            valid_hosts[config.Bridge.id] = host

def validateHosts(hosts) -> dict:
    valid_hosts = dict()
    workers = list()
    bin = 0
    bin_size = 2
    if len(hosts) <= bin_size:
        worker = Thread(target=validateHostsWorker, name='validateHostsWorker', args=(hosts, valid_hosts))
        workers.append(worker)
        worker.start()
    else:
        for i in range(int(len(hosts) / bin_size)):
            worker = Thread(target=validateHostsWorker, name='validateHostsWorker', args=(hosts[bin:bin + bin_size], valid_hosts))
            workers.append(worker)
            worker.start()
            bin = bin + bin_size
        if hosts[bin:]:
            worker = Thread(target=validateHostsWorker, name='validateHostsWorker', args=(hosts[bin:], valid_hosts))
            workers.append(worker)
            worker.start()
    for worker in workers:
        worker.join()
    return valid_hosts

def validateHost(host) -> bool:
    response = http.get('http://{}:{}/{}/na/config'.format(host, config.Bridge.port, config.Bridge.api_path), verify=False)
    if response.status == 200:
        try:
            host_info = json.loads(response.body)
            if host_info.get('bridgeid') in config.Bridge.id:
                return True
        except Exception:
            pass
    return False

def discoverBridge():
    if config.Bridge.host:
        if validateHost(config.Bridge.host):
            return
    host = None
    while not host:
        host = getNUPnP()
        if not host:
            logger.warning("could not retrieve host from cloud - reverting to ip range scan")
            valid_hosts = validateHosts(discoverHosts())
            if valid_hosts:
                host = valid_hosts[config.Bridge.id]
                continue
        else:
            continue
        time.sleep(10)
    config.Bridge.host = host
    logger.info("discovered hue bridge at '{}'".format(host))
