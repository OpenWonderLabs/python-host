#!/usr/bin/env python
#
# :author: Fabio "BlackLight" Manganiello <info@fabiomanganiello.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Some of the functionalities of the bluetooth LE stack (like
# device scanning) require special user privileges. Solutions:
#
# - Run this script as root
# - Set `cap_net` capabilities on your Python interpreter:
#     `[sudo] setcap 'cap_net_raw,cap_net_admin+eip' /path/to/python
#
# Note however that the latter option will set the privileges for any
# script that runs on that Python interpreter. If it's a security concern,
# then you might want to set the capabilities on a Python venv executable
# made specifically for Switchbot instead.

import argparse
import sys
import time
from contextlib import contextmanager

import bluetooth
from bluetooth.ble import DiscoveryService, GATTRequester


@contextmanager
def connect(device: str, bt_interface: str, timeout: float):
    if bt_interface:
        req = GATTRequester(device, False, bt_interface)
    else:
        req = GATTRequester(device, False)

    req.connect(False, 'random')
    connect_start_time = time.time()

    while not req.is_connected():
        if time.time() - connect_start_time >= timeout:
            raise ConnectionError('Connection to {} timed out after {} seconds'.
                                  format(device, timeout))
        time.sleep(0.1)

    yield req

    if req.is_connected():
        req.disconnect()


class Scanner(object):
    service_uuid = 'cba20002-224d-11e6-9fb8-0002a5d5c51b'
    _default_scan_timeout = 8
    _default_connect_timeout = 2.0

    def __init__(self, bt_interface: str = None, scan_timeout: int = None,
                 connect_timeout: float = None):
        self.bt_interface = bt_interface
        self.connect_timeout = connect_timeout or self._default_connect_timeout
        self.scan_timeout = scan_timeout or self._default_scan_timeout

    @classmethod
    def is_switchbot(cls, device: str, bt_interface: str, timeout: float):
        try:
            with connect(device, bt_interface, timeout) as req:
                for chrc in req.discover_characteristics():
                    if chrc.get('uuid') == cls.service_uuid:
                        print(' * Found Switchbot service on device {} handle {}'.
                              format(device, chrc.get('value_handle')))
                        return True
        except ConnectionError:
            return False

    def scan(self):
        if self.bt_interface:
            service = DiscoveryService(self.bt_interface)
        else:
            service = DiscoveryService()

        print('Scanning for bluetooth low-energy devices')
        devices = list(service.discover(self.scan_timeout).keys())
        print('Discovering Switchbot services')
        return [dev for dev in devices
                if self.is_switchbot(dev, self.bt_interface, self.connect_timeout)]


class Driver(object):
    handles = {
        'press': 0x16,
        'on': 0x16,
        'off': 0x16,
        'open': 0x0D,
        'close': 0x0D,
    }
    commands = {
        'press': b'\x57\x01\x00',
        'on': b'\x57\x01\x01',
        'off': b'\x57\x01\x02',
        'open': b'\x57\x0F\x45\x01\x05\xFF\x00',
        'close': b'\x57\x0F\x45\x01\x05\xFF\x64',
    }

    def __init__(self, device, bt_interface=None, timeout_secs=None):
        self.device = device
        self.bt_interface = bt_interface
        self.timeout_secs = timeout_secs if timeout_secs else 5

    def run_command(self, command):
        with connect(self.device, self.bt_interface, self.timeout_secs) as req:
            print('Connected!')
            return req.write_by_handle(self.handles[command], self.commands[command])


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-s', '--scan', dest='scan', required=False, default=False, action='store_true',
                        help="Run Switchbot in scan mode - scan devices to control")

    parser.add_argument('-d', '--device', dest='device', required=False, default=None,
                        help="Specify the address of a device to control")

    parser.add_argument('-c', '--command',  dest='command', required=False, default='press',
                        choices=['press', 'on', 'off', 'open', 'close'], 
                        help="Command to be sent to device. \
                            Noted that press/on/off for Bot and open/close for Curtain. \
                            Required if the controlled device is Curtain (default: %(default)s)")

    parser.add_argument('-i', '--interface',  dest='interface', required=False, default='hci0',
                        help="Name of the bluetooth adapter (default: %(default)s)")

    parser.add_argument('--scan-timeout', dest='scan_timeout', type=int, required=False, default=2,
                        help="Device scan timeout (default: %(default)s second(s))")

    parser.add_argument('--connect-timeout', dest='connect_timeout', type=int, required=False, default=5,
                        help="Device connection timeout (default: %(default)s second(s))")

    opts, args = parser.parse_known_args(sys.argv[1:])

    if opts.scan:
        scanner = Scanner(opts.interface, opts.scan_timeout, opts.connect_timeout)
        devices = scanner.scan()

        if not devices:
            print('No Switchbots found')
            sys.exit(1)

        print('Found {} devices: {}'.format(len(devices), devices))
        print('Enter the number of the device you want to control:')

        for i in range(0, len(devices)):
            print('\t{}\t{}'.format(i, devices[i]))

        i = int(input())
        bt_addr = devices[i]
    elif opts.device:
        bt_addr = opts.device
    else:
        raise RuntimeError('Please specify at least one mode between --scan and --device')

    driver = Driver(device=bt_addr, bt_interface=opts.interface, timeout_secs=opts.connect_timeout)
    driver.run_command(opts.command)
    print('Command execution successful')


if __name__ == '__main__':
    main()


# vim:sw=4:ts=4:et:
