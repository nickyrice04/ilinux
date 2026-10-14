#!/usr/bin/env python3
"""Offline decode of literal D/C/B panel values; never contacts hardware."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--device',required=True,help='Literal D hex value (root retry)')
p.add_argument('--current',required=True,help='Literal C hex value (most recent marked device)')
p.add_argument('--phase',required=True,help='Literal B hex value')
p.add_argument('--pin',help='Optional literal I hex pin index (FFF means inactive)')
a=p.parse_args();here=Path(__file__).resolve().parent
nodes={n['id']:n for n in json.loads((here/'device-identities.json').read_text())['nodes']}
phases=json.loads((here/'phases.json').read_text())
def device(v):
 i=int(v,16)
 if not 0<=i<=65535: p.error('device IDs must fit four hex digits')
 return nodes.get(i,{'id':i,'meaning':'UNKNOWN: unbound/dynamic/non-OF node or unreadable value; do not guess'})
b=int(a.phase,16)
if not 0<=b<=255:p.error('phase must fit two hex digits')
pin = int(a.pin,16) if a.pin is not None else None
if pin is not None and not (0<=pin<512 or pin==4095):p.error('pin must be 000..1FF or FFF')
print(json.dumps({'I':a.pin,'pin_index_decimal':pin if pin!=4095 else None,'root_retry':device(a.device),'current_operation_device':device(a.current),'B':f'{b:02X}','next_operation':phases.get(f'{b:02X}','UNKNOWN / no marked operation'),'limits':'Last boundaries only; not a blocking PC, coherent snapshot, driver-fault proof or hardware identifier.'},indent=2))
