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


from .logger import root_logger
from .configuration import config
from subprocess import call, check_output, DEVNULL
from socket import gethostbyname, getfqdn
from threading import Thread
from platform import system
from urllib.parse import urlparse
from urllib3 import disable_warnings as urllib3DisableWarnings
from urllib3.exceptions import InsecureRequestWarning as urllib3InsecureRequestWarning
import time, io, socket, requests
import http.client as HTTPclient

logger = root_logger.getChild(__name__.split(".", 1)[-1])

urllib3DisableWarnings(urllib3InsecureRequestWarning)

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

def discoverNUPnP() -> str:
    response = requests.get('https://{}/{}/nupnp'.format(config.Cloud.host, config.Cloud.api_path), verify=False, retries=3, retry_delay=1)
    if response.status_code == 200:
        host_list = response.json()
        for host in host_list:
            try:
                if host.get('id').upper() in config.Bridge.id:
                    return host.get('internalipaddress')
            except AttributeError:
                logger.error("could not extract host ip from '{}'".format(host))
    return str()

class DummySocket(io.BytesIO):
    # add 'makefile' and return self to satisfy http.client.HTTPResponse
    def makefile(self, *args, **kwargs):
        return self

def discoverSSDP() -> str:
    broadcast_msg = \
        'M-SEARCH * HTTP/1.1\r\n' \
        'HOST: 239.255.255.250:1900\r\n' \
        'ST: ssdp:all\r\n' \
        'MX: 10\r\n' \
        'MAN: "ssdp:discover"\r\n' \
        '\r\n'
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udp_socket.settimeout(20)
        udp_socket.sendto(broadcast_msg.encode(), ('239.255.255.250', 1900))
        try:
            while True:
                response = udp_socket.recv(65507)
                response = HTTPclient.HTTPResponse(DummySocket(response))
                response.begin()
                if response.getheader('hue-bridgeid') and response.getheader('hue-bridgeid') in config.Bridge.id and response.getheader('LOCATION'):
                    udp_socket.close()
                    return urlparse(response.getheader('LOCATION')).hostname
        except socket.timeout:
            pass
    except Exception as ex:
        logger.error(ex)
    return str()

def validateHost(host) -> bool:
    response = requests.get('http://{}:{}/{}/na/config'.format(host, config.Bridge.port, config.Bridge.api_path), verify=False)
    if response.status_code == 200:
        try:
            host_info = response.json()
            if host_info.get('bridgeid') in config.Bridge.id:
                return True
        except Exception:
            pass
    return False

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

def discoverBridge():
    if config.Bridge.host:
        if validateHost(config.Bridge.host):
            return
    host = None
    while not host:
        host = discoverNUPnP()
        if host:
            if not validateHost(host):
                host = None
        if not host:
            logger.warning("could not retrieve host from cloud - reverting to SSDP")
            host = discoverSSDP()
            if not host:
                logger.warning("could not discover host via SSDP - reverting to ip range scan")
                valid_hosts = validateHosts(discoverHosts())
                if valid_hosts:
                    host = valid_hosts[config.Bridge.id]
                    continue
                else:
                    logger.warning("ip range scan yielded no results")
            else:
                continue
        else:
            continue
        time.sleep(10)
    config.Bridge.host = host
    logger.info("discovered hue bridge at '{}'".format(host))
