import argparse
import struct
import sys
import time

import bluetooth
from bluetooth.ble import DiscoveryService, GATTRequester


class Scanner(object):
    service_uuid = '1bc5d5a5-0200b89f-e6114d22-000da2cb'

    def __init__(self, bt_interface=None, timeout_secs=None):
        self.bt_interface = bt_interface
        self.timeout_secs = timeout_secs if timeout_secs else 2


    def scan(self):
        service = DiscoveryService(self.bt_interface) \
            if self.bt_interface else DiscoveryService()

        devices = service.discover(self.timeout_secs)
        return list(devices.keys())



class Driver(object):
    handle = 0x16
    commands = {
        'press' : '\x57\x01\x00',
        'on'    : '\x57\x01\x01',
        'off'   : '\x57\x01\x02',
    }

    def __init__(self, device, bt_interface=None, timeout_secs=None):
        self.device = device
        self.bt_interface = bt_interface
        self.timeout_secs = timeout_secs if timeout_secs else 5
        self.req = None


    def connect(self):
        if self.bt_interface:
            self.req = GATTRequester(self.device, False, self.bt_interface)
        else:
            self.req = GATTRequester(self.device, False)

        self.req.connect(True, 'random')
        connect_start_time = time.time()
        while not self.req.is_connected():
            if time.time() - connect_start_time >= self.timeout_secs:
                raise RuntimeError('Connection to {} timed out after {} seconds'
                                   .format(self.device, self.timeout_secs))

    def run_command(self, command):
        return self.req.write_by_handle(self.handle, self.commands[command])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', '-s', dest='scan', required=False, default=False, action='store_true',
                        help="Run Switchbot in scan mode - scan devices to control")

    parser.add_argument('--scan-timeout', dest='scan_timeout', type=int,
                        required=False, default=None,
                        help="Device scan timeout (default: 2 seconds)")

    parser.add_argument('--connect-timeout', dest='connect_timeout', required=False, default=None,
                        help="Device connection timeout (default: 5 seconds)")

    parser.add_argument('--device', '-d', dest='device', required=False, default=None,
                        help="Specify the address of a device to control")

    parser.add_argument('--interface', '-i', dest='interface', required=False, default=None,
                        help="Name of the bluetooth adapter (default: hci0 or whichever is the default)")

    parser.add_argument('--command', '-c', dest='command', required=False, default='press',
                        choices=['press', 'on', 'off'], help="Command to be sent to device (default: press)")

    opts, args = parser.parse_known_args(sys.argv[1:])

    if opts.scan:
        scanner = Scanner(opts.interface, opts.scan_timeout)
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
    driver.connect()
    print('Connected!')

    driver.run_command(opts.command)
    print('Command execution successful')


if __name__ == '__main__':
    main()


# vim:sw=4:ts=4:et:

