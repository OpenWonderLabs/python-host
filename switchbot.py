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

class DevScanner:
    
    def __init__( self ):
        print("Scanner inited")

    def dongle_start(self):
        self.con = pexpect.spawn('hciconfig hci0 up')
        time.sleep(1)
        
    def dongle_restart(self):
        print "restart bluetooth dongle"
        self.con = pexpect.spawn('hciconfig hci0 down')
        time.sleep(3)
        self.con = pexpect.spawn('hciconfig hci0 up')
        time.sleep(3)

    def scan_loop(self):
        self.con = pexpect.spawn('hciconfig')
        pnum = self.con.expect(["hci0",pexpect.EOF,pexpect.TIMEOUT])
        if pnum==0:
            self.con = pexpect.spawn('hcitool lescan')
            self.con.expect('LE Scan ...', timeout=10)
            print "Start scanning..."
        else:
            raise Error("no bluetooth error")
        exit_counter=0
        #some bluetooth dongles may upload duplicates
        repeat_counter=0
        dev_list  = []
        while True:
            pnum = self.con.expect(["WoHand",pexpect.EOF,pexpect.TIMEOUT], timeout=5)
            if pnum==0:    
                after = self.con.after
                before = self.con.before
                mac = before.split()[-1]
                if mac not in dev_list:
                    dev_list.append(mac)
                    repeat_counter = 0
                else:
                    repeat_counter += 1
                if repeat_counter > 30:
                    print "repeat_counter out"
                    return dev_list
            else:
                print "scan timeout"
                return dev_list
            exit_counter += 1
            if exit_counter > 60:
                print "exit_counter out"
                return dev_list
        pass

    def register_cb( self, fn ):
        self.cb=fn;
        return

    def close(self):
        #self.con.sendcontrol('c')
        self.con.close(force=True)

def trigger_device(add):
    print 'Start to control'
    con = pexpect.spawn('gatttool -b ' + add + ' -t random -I')
    con.expect('\[LE\]>')
    print "Preparing to connect."
    con.sendline('connect')
    #To compatible with different Bluez versions
    con.expect(['\[CON\]','Connection successful.*\[LE\]>'])
    print 'Write command'
    con.sendline('char-write-cmd 0x0016 570100')
    con.expect('\[LE\]>')
    con.sendline('quit')
    print 'Trigger complete'

def main():
    #Check bluetooth dongle
    connect = pexpect.spawn('hciconfig')
    pnum = connect.expect(["hci0",pexpect.EOF,pexpect.TIMEOUT])
    if pnum!=0:
        print 'No bluetooth hardware, exit now'
        sys.exit()
    connect = pexpect.spawn('hciconfig hci0 up')
    
    #Start scanning...
    scan = DevScanner()
    dev_list = scan.scan_loop()
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
    sys.exit()

if __name__ == "__main__":
    main()
