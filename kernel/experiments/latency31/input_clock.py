#!/usr/bin/env python3
"""Read an explicitly selected Linux evdev device without grabbing/injecting.

Use EVIOCSCLOCKID on this reader's descriptor only. Output contains sequence,
state and timing, never keycode/text. Not a physical-switch timestamp.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import select
import stat
import struct
import sys
import time

EVENT=struct.Struct('@llHHi')
EVIOCSCLOCKID=0x400445a0


def decode(data, received_ns, sequence):
    sec,usec,kind,_code,value=EVENT.unpack(data)
    if kind!=1:
        return None
    if value not in (0,1,2) or sec<0 or not 0<=usec<1000000:
        raise ValueError('invalid input event')
    kernel_ns=sec*1000000000+usec*1000
    if kernel_ns>received_ns:
        raise ValueError('input timestamp is ahead of the selected monotonic clock')
    return {'sequence':sequence,'state':value,'kernel_ns':kernel_ns,
            'reader_ns':received_ns,'reader_delay_ns':received_ns-kernel_ns}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('device',type=Path)
    p.add_argument('--seconds',type=int,default=45,choices=range(1,61))
    a=p.parse_args()
    if sys.platform!='linux' or EVENT.size!=24:
        p.error('requires 64-bit Linux input ABI')
    if not a.device.is_absolute() or a.device.parent!=Path('/dev/input') or not a.device.name.startswith('event'):
        p.error('explicit /dev/input/eventN path required')
    fd=os.open(a.device,os.O_RDONLY|os.O_NONBLOCK|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        st=os.fstat(fd)
        if not stat.S_ISCHR(st.st_mode) or os.major(st.st_rdev)!=13:
            raise ValueError('not a Linux input character device')
        fcntl.ioctl(fd,EVIOCSCLOCKID,struct.pack('i',time.CLOCK_MONOTONIC))
        # Discard any pre-ioctl timestamp-domain backlog without reporting it.
        for _ in range(64):
            try: os.read(fd,24*64)
            except BlockingIOError: break
        else: raise ValueError('input backlog did not clear')
        end=time.monotonic()+a.seconds
        seq=0
        print(json.dumps({'event':'ready','clock':'CLOCK_MONOTONIC','ns':time.monotonic_ns()}),flush=True)
        while time.monotonic()<end and seq<4096:
            if not select.select([fd],[],[],min(0.25,max(0,end-time.monotonic())))[0]:continue
            data=os.read(fd,24*64)
            received=time.monotonic_ns()
            if not data or len(data)%24:raise ValueError('incomplete input read')
            for start in range(0,len(data),24):
                row=decode(data[start:start+24],received,seq)
                if row is not None:
                    print(json.dumps(row),flush=True)
                    seq+=1
                    if seq>=4096:break
        print(json.dumps({'event':'done','events':seq,'limit_hit':seq>=4096}),flush=True)
    finally:os.close(fd)


if __name__=='__main__':main()
