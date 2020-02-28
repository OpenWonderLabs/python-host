#!/usr/bin/env python3
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

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

class DevScanner(DefaultDelegate):
    def __init__( self ):
        DefaultDelegate.__init__(self)
        #print("Scanner inited")

    def dongle_start(self):
        self.con = pexpect.spawn('hciconfig hci0 up')
        time.sleep(1)

    def dongle_restart(self):
        print("restart bluetooth dongle")
        self.con = pexpect.spawn('hciconfig hci0 down')
        time.sleep(3)
        self.con = pexpect.spawn('hciconfig hci0 up')
        time.sleep(3)

    def scan_loop(self):
        # service_uuid = '1bc5d5a50200b89fe6114d22000da2cb'
        service_uuid = 'cba20d00-224d-11e6-9fb8-0002a5d5c51b'
        menufacturer_id = '5900f46d2c8a5f31'
        dev_list =[]
        bot_list =[]
        enc_list =[]
        link_list =[]
        meter_list=[]
        self.con = pexpect.spawn('hciconfig')
        pnum = self.con.expect(["hci0",pexpect.EOF,pexpect.TIMEOUT])
        if pnum==0:
            self.con = pexpect.spawn('hcitool lescan')
            #self.con.expect('LE Scan ...', timeout=5)
            scanner = Scanner().withDelegate(DevScanner())
            devices = scanner.scan(10.0)
            print("Start scanning...")
        else:
            raise Error("no bluetooth error")

        for dev in devices:
            mac = 0
            for (adtype, desc, value) in dev.getScanData():
                # print(adtype,desc,value)
                if desc == '16b Service Data':
                    model = binascii.a2b_hex(value[4:6])
                    mode  = binascii.a2b_hex(value[6:8])
                    if len(value) == 16:
                        # print(adtype,desc,value,len(value))
                        # celsius
                        tempFra = int(value[11:12].encode('utf-8'), 16) / 10.0
                        tempInt = int(value[12:14].encode('utf-8'), 16)
                        if tempInt < 128:
                            tempInt *= -1
                            tempFra *= -1
                        else:
                            tempInt -= 128
                        meterTemp = tempInt + tempFra
                        meterHumi = int(value[14:16].encode('utf-8'), 16) % 128
                        # print("meter:", meterTemp, meterHumi)
                    else:
                        meterTemp = 0
                        meterHumi = 0
                elif desc == 'Local name':
                    if value == "WoHand":
                        mac   = dev.addr
                        model = 'H'
                        mode  = 0
                    elif value == "WoMeter":
                        mac   = dev.addr
                        model = 'T'
                        mode = 0
                elif desc == 'Complete 128b Services' and value == service_uuid :
                    mac = dev.addr

            if mac != 0 :
                #print(binascii.b2a_hex(model),binascii.b2a_hex(mode))
                dev_list.append([mac, model.decode('utf-8'), mode, meterTemp, meterHumi])

        # print(dev_list)
        for (mac, dev_type,mode,meterTemp, meterHumi) in dev_list:
            if dev_type == 'L':
                link_list.append(mac)
            if dev_type == 'H'  or ord(dev_type) == ord('L') + 128:
                #print(int(binascii.b2a_hex(mode),16))
                if int(binascii.b2a_hex(mode),16) > 127 :
                    bot_list.append([mac,"Turn On"])
                    bot_list.append([mac,"Turn Off"])
                    bot_list.append([mac,"Up"])
                    bot_list.append([mac,"Down"])
                else :
                    bot_list.append([mac,"Press"])
            elif dev_type == 'T':
                meter_list.append([mac,"Humiture:%.1f'C %d%%"%(meterTemp, meterHumi)])
            if ord(dev_type) == ord('L') + 128:
                enc_list.append([mac,"Press"])
        # print(bot_list)
        print("Scan timeout.")
        return bot_list + meter_list
        pass

    def register_cb( self, fn ):
        self.cb=fn
        return

    def close(self):
        #self.con.sendcontrol('c')
        self.con.close(force=True)

def trigger_device(device):
    [add,act] = device
    #print('Start to control')
    con = pexpect.spawn('gatttool -b ' + add + ' -t random -I')
    con.expect('\[LE\]>')
    print("Preparing to connect.")
    retry = 3
    index = 0
    while retry>0 and 0==index:
        con.sendline('connect')
        #To compatible with different Bluez versions
        index = con.expect(['Error', '\[CON\]','Connection successful.*\[LE\]>'])
        retry -= 1
    if 0==index:
        print("Connection error.")
        return
    print("Connection successful.")
    con.sendline('char-desc')
    con.expect(['\[CON\]','cba20002-224d-11e6-9fb8-0002a5d5c51b'])
    cmd_handle = con.before.decode('utf-8').split('\n')[-1].split()[2].strip(',')
    if act == "Turn On":
        con.sendline('char-write-cmd ' + cmd_handle + ' 570101')
    elif act == "Turn Off":
        con.sendline('char-write-cmd ' + cmd_handle + ' 570102')
    elif act == "Press":
        con.sendline('char-write-cmd ' + cmd_handle + ' 570100')
    elif act == "Down":
        con.sendline('char-write-cmd ' + cmd_handle + ' 570103')
    elif act == "Up":
        con.sendline('char-write-cmd ' + cmd_handle + ' 570104')
    elif "Humiture" in act:
        con.sendline('char-write-cmd ' + cmd_handle + ' 570F31')
        con.expect('\[LE\]>')
        con.sendline('char-read-uuid cba20003-224d-11e6-9fb8-0002a5d5c51b')
        index = con.expect(['value:[0-9a-fA-F ]+', 'Error'])
        if index == 0:
            data = con.after.decode('utf-8').split(':')[1].replace(' ', '')
            tempFra = int(data[3], 16) / 10.0
            tempInt = int(data[4:6], 16) 
            if tempInt < 128:
                tempInt *= -1
                tempFra *= -1
            else:
                tempInt -= 128
            meterTemp = tempInt + tempFra
            meterHumi = int(data[6:8], 16) % 128
            print("Meter[%s] %.1f'C %d%%"%(add, meterTemp, meterHumi))
        else:
            print('Error!')
    else:
        print("Unsupported operations")
    con.expect('\[LE\]>')
    con.sendline('quit')
    print('Complete')

def main():
    #Check bluetooth dongle
    print('Usage: "sudo python switchbot.py [mac_addr  cmd]" or "sudo python switchbot.py"')
    connect = pexpect.spawn('hciconfig')
    pnum = connect.expect(["hci0",pexpect.EOF,pexpect.TIMEOUT])
    if pnum!=0:
        print('No bluetooth hardware, exit now')
        sys.exit()
    connect = pexpect.spawn('hciconfig hci0 up')

    if len(sys.argv) == 3 or len(sys.argv) == 4:
        dev = sys.argv[1]
        act = sys.argv[2] if len(sys.argv) < 4  else  ('Turn ' + sys.argv[3] )
        trigger_device([dev,act])

    elif len(sys.argv) == 1:
        #Start scanning...
        scan = DevScanner()
        dev_list = scan.scan_loop()
        dev = sys.argv[1] if len(sys.argv) > 1 else None
        dev_number = None

        if not dev_list:
            print("No SwitchBot nearby, exit")
            sys.exit()
        for idx, val in enumerate(dev_list):
            print(idx, val)

        dev_number = int(input("Input the device number to control:"))

        if dev_number >= len(dev_list) :
            print("Input error, exit")
        bluetooth_adr = dev_list[dev_number]

        #Trigger the device to work
        #If the SwitchBot address is known you can run this command directly without scanning

        trigger_device(bluetooth_adr)
    else :
        print('wrong cmd.')
        print('Usage: "sudo python switchbot_meter_py3.py [mac_addr  cmd]" or "sudo python switchbot_meter_py3.py"')

    connect = pexpect.spawn('hciconfig')

    sys.exit()

if __name__ == "__main__":
    main()
