#!/usr/bin/env python3

# Copyright (C) 2016  Stefan Mandl

# Display debug messages from rephone
# Shows only vm_log* messages from the device.
# Only works with firmware version W15.19.p2

# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA 02110-1301 USA.

# TODO: rewrite using kaitai with `doc/MTK_2502_vmlog.ksy`

import serial
import time
import sys
import re
import argparse
import traceback
import os
import struct
from serial import serial_for_url


class MTKModem(object):
    
    def __init__(self, OsxMode= False):
        
        
        self.OsxMode = OsxMode

    def open(self, port):
        print ('Switch on the device and connect it to the USB port')
        print ('Try to open port {0}. Press ctrl + c for break'.format(port))
        while 1:
            try:
                if self.OsxMode:
                    # select hangs on OS x.....
                    # use only read as workaround
                    self.ser = serial.VTIMESerial(port, 115200, timeout=2, dsrdtr=True, rtscts=True)
                else:
                    #self.ser = serial_for_url('spy:///dev/ttyACM1', 115200, timeout=2, dsrdtr=True, rtscts=True)
                    self.ser = serial.Serial(port, 115200, timeout=2, dsrdtr=True)
                break
            except:
                #time.sleep(0.2)
                continue
    
    def close(self):
        self.ser.close()
        
 
    #
    # read with optional byte logging
    #
    def read(self, size=1):
        data = bytearray()
        
        data = self.ser.read(size)
        
        return bytes(data)
    #        
    # read and handle A5 messages
    #
    def readHandleA5(self): 
        data = bytearray()
        data = self.read(1)
        while data == b'\xA5':
            self.getA5msg()
            data = self.ser.read(1)
        return bytes(data)
    
    # reveive a paket
    #   
    #   (Header)      (lenght)   (paket id) (data)   (checksum)
    #   55 00            45         71                 2
    
    def syncStream(self):
        print ('Wait sync ...')
        while 1:
            data = self.read(1)
            print ("x", end='')
            if data ==  b'\x55':
                data2 = self.read(1)
                if data2 == b'\x00':
                    # found frame start                  
                    self.getmsgclean()
                    break
        print ('Sync')
        
    def receivePaket(self):
        data = bytearray()
        data2 = bytearray()
        flagNew = True
        while 1:
            data = self.read(1)
            if data == None:
                continue
            if data == b'\x55':
                data2 = self.read(1)
                if data2 == b'\x00':
                    # found frame start
                    flagNew = True
                    self.getmsgclean()
        
            elif data == b'\xA5':
                flagNew = True
                self.getA5msg()
    
            else:
                print (".", end='')
                if flagNew == True:
                   
                    flagNew = False
                    #print ("New {0:x}".format(16))
                

    #
    # got a high priority messages
    #
    def getA5msg(self):
        # print 'A5'
        length, = struct.unpack('B', self.read(1))  # 0x0A
        data = self.read(length)    
        FrameNumber = self.read(1) #FrameNumber ?
        checksum = self.read(1)    
        
    def getmsgclean(self):
        msg = bytearray()
        a=0
        # get msg length
        data = self.readHandleA5()
        length, = struct.unpack('B', data)
        i = 0
        while i < length:
            data = self.readHandleA5()
            msg += data
            i = i + 1
        id = msg[:1]
        
        if id == b'\x71':
            # vm_log* messages 
            try:
                a = msg.index(b'\t', 10)
                
            except ValueError as e:   
                print (a)
                return
            debug_msg = msg[a + 1:]
            debug_msg = debug_msg.strip(b'\x00')
            debug_msg = debug_msg.strip(b'\x0a')
          
            print (debug_msg.decode("utf-8","backslashreplace"))
            
       
            
            
        elif id == b'\x61':
            debug_msg = msg[a + 1:]
            #no text
            
        elif id == b'\x62':
            #BT Module debug
            debug_msg = msg[a + 9:]
            print (debug_msg.decode("utf-8", "ignore"))
             
        elif id == b'\x65':
            #AT* messages
            debug_msg = msg[a + 13:]
            debug_msg = debug_msg.strip(b'\x00')
            debug_msg = debug_msg.strip(b'\x0a')
            print (debug_msg.decode("utf-8", "ignore"))
        elif id == b'\x78':
            debug_msg = msg[a + 5:]  
            print (debug_msg.decode("utf-8", "ignore")) 
        elif id == b'\x94':
            Nop = None   
        elif id == b'\x81':  
            debug_msg = msg[a + 1:] 
        elif id == b'\x83':  
            # GPS Messages
            debug_msg = msg[a + 9:]
            debug_msg = debug_msg.replace(b'\x00',b'')
            debug_msg = debug_msg.replace(b'\x0a',b'')
            debug_msg = debug_msg.replace(b'\x0d',b'')
            print (debug_msg.decode("utf-8", "ignore"))
              
        else:
            print ('New ID: ')        
            print("".join(" %02x" % i for i in msg))
            
        # read checksum
        checksum = self.readHandleA5()
        checksum = self.readHandleA5()    

    #
    # connect to catcher in the device
    #
    def switchOn(self):
        print ('Send switchOn')

        step1 =  bytearray(b'\x55\x00\x0c\x63\x30\x00\x08\x00\x01\x00\x00\x00\x0b\x00\x00\x00\x08')

        step2 =  bytearray(b'\x55\x00\x35\x63\x02\x00\x31\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\x00\x00\x00\x00\x00\x00\x00\x00\x32')

        step3 =  bytearray(b'\x55\x03\x06\x63\x04\x00\x02\x03\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x36')

        step4 =  bytearray(b'\x55\x00\x88\x63\x06\x00\x84\x00\x70\x00\x00\x56\x52\x45\x49\x4e\x49\x54\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x17')

        step5 =  bytearray(b'\x55\x00\x88\x63\x06\x00\x84\x00\x03\x00\x00\x50\x6f\x6c\x6c\x69\x6e\x67\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x60')

        self.ser.write(step1)
        time.sleep(0.2)
        self.ser.write(step2)
        time.sleep(0.2)
        self.ser.write(step3)
        time.sleep(0.2)
        self.ser.write(step5)
        time.sleep(0.2)
        
    

    def flushCom(self):
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()()


def main():


    parser = argparse.ArgumentParser(description='Mon Application Utility', prog='mon')

    parser.add_argument('--port', '-p', help='Serial port device', default='/dev/ttyACM1')
    parser.add_argument('--osx', help='Select osx mode.',action="store_true")
    
    osx= False
    args = parser.parse_args()
    if args.osx:
        osx= True
    
    h = MTKModem( osx)
    
    while 1:
        try:
            h.open(args.port);
            time.sleep(1)
            print("Port open")
            h.switchOn()
            h.syncStream()
            h.receivePaket()
        except serial.SerialException as e:
            # Disconnect of USB->UART occured
            h.close()
            print ("USB disconnect")
        except OSError as e:
            h.close()
            print ("USB not ready. wait 2s....")
            time.sleep(2)
        
if __name__ == '__main__':
    try:
        main()
       
    except (Exception):
        #sys.stderr.write('ERROR: %s\n' % str(err))
        traceback.print_exc()

