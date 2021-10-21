#!/usr/bin/env python
# Copyright 2017-present WonderLabs, Inc. <support@wondertechlabs.com>
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
import pexpect
import sys
from bluepy.btle import Scanner, DefaultDelegate
import binascii
import copy
import datetime


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)


class DevScanner(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)
        # print('Scanner inited')

    def dongle_start(self):
        self.con = pexpect.spawn('hciconfig hci0 up')
        time.sleep(1)

    def dongle_restart(self):
        print('restart bluetooth dongle')
        self.con = pexpect.spawn('hciconfig hci0 down')
        time.sleep(3)
        self.con = pexpect.spawn('hciconfig hci0 up')
        time.sleep(3)

    def scan_loop(self):
        service_uuid = 'cba20d00-224d-11e6-9fb8-0002a5d5c51b'
        company_id = '6909'  # actually 0x0969
        dev_list = []
        bot_list = []
        meter_list = []
        curtain_list = []
        contact_list = []
        motion_list = []
        param_list = []

        pir_tip = ['No movement detected', 'Movement detected']
        hall_tip = ['Door closed', 'Door opened', 'Timeout no closed']
        light_tip = ['Dark', 'Bright']

        self.con = pexpect.spawn('hciconfig')
        pnum = self.con.expect(['hci0', pexpect.EOF, pexpect.TIMEOUT])
        if pnum == 0:
            self.con = pexpect.spawn('hcitool lescan')
            # self.con.expect('LE Scan ...', timeout=5)
            scanner = Scanner().withDelegate(DevScanner())
            devices = scanner.scan(10.0)
            print('Scanning...')
        else:
            raise Error('no bluetooth error')

        for dev in devices:
            mac = 0
            param_list[:] = []
            for (adtype, desc, value) in dev.getScanData():
                # print(adtype, desc, value)
                if desc == '16b Service Data':
                    dev_type = binascii.a2b_hex(value[4:6])
                    if dev_type == 'H':
                        param_list.append(binascii.a2b_hex(value[6:8]))
                    elif dev_type == 'T':
                        # celsius
                        tempFra = int(value[11:12].encode('utf-8'), 16) / 10.0
                        tempInt = int(value[12:14].encode('utf-8'), 16)
                        if tempInt < 128:
                            tempInt *= -1
                            tempFra *= -1
                        else:
                            tempInt -= 128
                        param_list.append(tempInt + tempFra)
                        param_list.append(
                            int(value[14:16].encode('utf-8'), 16) % 128)
                        # print('meter:', param1, param2)
                    elif dev_type == 'd':
                        # print(adtype, desc, value)
                        pirSta = (
                            int(value[6:7].encode('utf-8'), 16) >> 2) & 0x01
                        # TODO:
                        # diffSec = (
                        #     int(value[10:11].encode('utf-8'), 16) >> 2) & 0x02
                        diffSec = 0
                        hallSta = (
                            int(value[11:12].encode('utf-8'), 16) >> 1) & 0x03
                        lightSta = int(value[11:12].encode('utf-8'), 16) & 0x01
                        param_list.extend([hallSta, pirSta, lightSta, diffSec])
                        # print(pirSta, diffSec, hallSta, lightSta)
                    elif dev_type == 's':
                        # print(adtype, desc, value)
                        pirSta = (
                            int(value[6:7].encode('utf-8'), 16) >> 2) & 0x01
                        lightSta = (int(value[15:16].encode('utf-8'), 16) & 0x03) - 1
                        # TODO:
                        diffSec = 0
                        param_list.extend([pirSta, lightSta, diffSec])
                    else:
                        param_list[:] = []
                elif desc == 'Local name':
                    if value == 'WoHand':
                        mac = dev.addr
                        dev_type = 'H'
                    elif value == 'WoMeter':
                        mac = dev.addr
                        dev_type = 'T'
                    elif value == 'WoCurtain':
                        mac = dev.addr
                        dev_type = 'c'
                    elif value == 'WoContact':
                        mac = dev.addr
                        dev_type = 'd'
                    elif value == 'WoMotion':
                        mac = dev.addr
                        dev_type = 's'
                elif desc == 'Complete 128b Services' and value == service_uuid:
                    mac = dev.addr
                elif desc == 'Manufacturer' and value[0:4] == company_id:
                    mac = dev.addr

            if mac != 0:
                dev_list.append([mac, dev_type, copy.deepcopy(param_list)])

        # print(dev_list)
        for (mac, dev_type, params) in dev_list:
            if dev_type == 'H':
                if int(binascii.b2a_hex(params[0]), 16) > 127:
                    bot_list.append([mac, 'Bot', 'Turn On'])
                    bot_list.append([mac, 'Bot', 'Turn Off'])
                    bot_list.append([mac, 'Bot', 'Up'])
                    bot_list.append([mac, 'Bot', 'Down'])
                else:
                    bot_list.append([mac, 'Bot', 'Press'])
            elif dev_type == 'T':
                meter_list.append([mac, 'Meter', "%.1f'C %d%%" %
                                  (params[0], params[1])])
            elif dev_type == 'c':
                curtain_list.append([mac, 'Curtain', 'Open'])
                curtain_list.append([mac, 'Curtain', 'Close'])
                curtain_list.append([mac, 'Curtain', 'Pause'])
            elif dev_type == 'd':
                # TODO:
                # timeTirgger = datetime.datetime.now() + datetime.timedelta(0, params[3])
                # contact_list.append([mac, 'Contact', "%s, %s, %s, Last trigger: %s" %
                #                      (hall_tip[params[0]], pir_tip[params[1]], light_tip[params[2]], timeTirgger.strftime("%Y-%m-%d %H:%M"))])
                contact_list.append([mac, 'Contact', "%s, %s, %s" %
                                     (hall_tip[params[0]], pir_tip[params[1]], light_tip[params[2]])])
            elif dev_type == 's':
                motion_list.append([mac, 'Motion', "%s, %s" %
                                    (pir_tip[params[0]], light_tip[params[1]])])
        print('Scan timeout.')
        return bot_list + meter_list + curtain_list + contact_list + motion_list
        pass

    def register_cb(self, fn):
        self.cb = fn
        return

    def close(self):
        # self.con.sendcontrol('c')
        self.con.close(force=True)


def trigger_device(device):
    [mac, dev_type, act] = device
    # print 'Start to control'
    con = pexpect.spawn('gatttool -b ' + mac + ' -t random -I')
    con.expect('\[LE\]>')
    print('Preparing to connect.')
    retry = 3
    index = 0
    while retry > 0 and 0 == index:
        con.sendline('connect')
        # To compatible with different Bluez versions
        index = con.expect(
            ['Error', '\[CON\]', 'Connection successful.*\[LE\]>'])
        retry -= 1
    if 0 == index:
        print('Connection error.')
        return
    print('Connection successful.')
    con.sendline('char-desc')
    con.expect(['\[CON\]', 'cba20002-224d-11e6-9fb8-0002a5d5c51b'])
    cmd_handle = con.before.split('\n')[-1].split()[2].strip(',')
    if dev_type == 'Bot':
        if act == 'Turn On':
            con.sendline('char-write-cmd ' + cmd_handle + ' 570101')
        elif act == 'Turn Off':
            con.sendline('char-write-cmd ' + cmd_handle + ' 570102')
        elif act == 'Press':
            con.sendline('char-write-cmd ' + cmd_handle + ' 570100')
        elif act == 'Down':
            con.sendline('char-write-cmd ' + cmd_handle + ' 570103')
        elif act == 'Up':
            con.sendline('char-write-cmd ' + cmd_handle + ' 570104')
    elif dev_type == 'Meter':
        con.sendline('char-write-cmd ' + cmd_handle + ' 570F31')
        con.expect('\[LE\]>')
        con.sendline('char-read-uuid cba20003-224d-11e6-9fb8-0002a5d5c51b')
        index = con.expect(['value:[0-9a-fA-F ]+', 'Error'])
        if index == 0:
            data = con.after.split(':')[1].replace(' ', '')
            tempFra = int(data[3], 16) / 10.0
            tempInt = int(data[4:6], 16)
            if tempInt < 128:
                tempInt *= -1
                tempFra *= -1
            else:
                tempInt -= 128
            meterTemp = tempInt + tempFra
            meterHumi = int(data[6:8], 16) % 128
            print("Meter[%s] %.1f'C %d%%" % (mac, meterTemp, meterHumi))
        else:
            print('Error!')
    elif dev_type == 'Curtain':
        if act == 'Open':
            con.sendline('char-write-cmd ' + cmd_handle + ' 570F450105FF00')
        elif act == 'Close':
            con.sendline('char-write-cmd ' + cmd_handle + ' 570F450105FF64')
        elif act == 'Pause':
            con.sendline('char-write-cmd ' + cmd_handle + ' 570F450100FF')
    else:
        print('Unsupported operations')
    con.expect('\[LE\]>')
    con.sendline('quit')
    print('Complete')


def main():
    # Check bluetooth dongle
    print(
        'Usage: "sudo python switchbot.py [mac dev_type cmd]" or "sudo python switchbot.py"')
    connect = pexpect.spawn('hciconfig')
    pnum = connect.expect(["hci0", pexpect.EOF, pexpect.TIMEOUT])
    if pnum != 0:
        print('No bluetooth hardware, exit now')
        sys.exit()
    connect = pexpect.spawn('hciconfig hci0 up')

    # print(sys.argv, len(sys.argv))

    if len(sys.argv) == 4 or len(sys.argv) == 5:
        dev = sys.argv[1]
        dev_type = sys.argv[2]
        act = sys.argv[3] if len(sys.argv) < 5 else ('Turn ' + sys.argv[4])
        trigger_device([dev, dev_type, act])

    elif len(sys.argv) == 1:
        # Start scanning...
        scan = DevScanner()
        dev_list = scan.scan_loop()
        # dev_number = None

        if not dev_list:
            print("No SwitchBot nearby, exit")
            sys.exit()
        for idx, val in enumerate(dev_list):
            print('%2d' % idx, val)

        dev_number = int(input("Input the device number to control:"))
        if dev_number >= len(dev_list):
            print("Input error, exit")
        else:
            ble_dev = dev_list[dev_number]
            print(ble_dev)

            # Trigger the device to work
            # If the SwitchBot address is known you can run this command directly without scanning

            trigger_device(ble_dev)
    else:
        print('Wrong cmd!')
        print(
            'Usage: "sudo python switchbot.py [mac dev_type cmd]" or "sudo python switchbot.py"')

    connect = pexpect.spawn('hciconfig')

    sys.exit()


if __name__ == "__main__":
    main()
