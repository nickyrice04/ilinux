#!/usr/bin/env python3
"""Summarize bounded CPU-side traces without double-counting nested scopes."""
import argparse
import csv
import json
from pathlib import Path
import statistics

TAGS = {'monitor', 'begin', 'output_commit', 'end_render', 'final_copy',
        'texture', 'primitive', 'input', 'keybind', 'surface_commit', 'surface_buffer', 'scene',
        'element', 'finish_wait', 'scene_drain', 'final_drain'}


def read_trace(path):
    rows, ids = [], set()
    with path.open() as f:
        for row in csv.DictReader(f):
            if len(rows) >= 100000 or set(row) != {'id','tag','start_ns','end_ns','cpu_ns','arg0','arg1'}:
                raise ValueError('invalid or oversized trace')
            r = {k:(v if k == 'tag' else int(v)) for k,v in row.items()}
            if (r['tag'] not in TAGS or r['id'] in ids or r['id'] <= 0 or
                r['start_ns'] <= 0 or r['end_ns'] < r['start_ns'] or r['cpu_ns'] < 0):
                raise ValueError('invalid trace row')
            ids.add(r['id'])
            rows.append(r)
    if not rows:
        raise ValueError('empty trace')
    if len(rows)==100000:
        raise ValueError('trace reached its cap; preserve as incomplete evidence')
    return rows


def stats(rows):
    out = {}
    for tag in sorted({r['tag'] for r in rows}):
        group = [r for r in rows if r['tag'] == tag]
        durations = [(r['end_ns']-r['start_ns'])/1e6 for r in group]
        out[tag] = {'n':len(group), 'median_ms':statistics.median(durations),
                    'max_ms':max(durations), 'wall_sum_ms':sum(durations),
                    'thread_cpu_sum_ms':sum(r['cpu_ns'] for r in group)/1e6}
    return out


def occupied_ns(rows, start, end):
    spans=sorted((max(start,r['start_ns']),min(end,r['end_ns'])) for r in rows
                 if r['tag']=='monitor' and r['start_ns']<end and r['end_ns']>start)
    total=0; cursor=start
    for a,b in spans:
        total+=max(0,b-max(a,cursor))
        cursor=max(cursor,b)
    return total


def summarize(rows, actions):
    start = next(r['ns'] for r in actions if r['event'] == 'ready')
    stop = next(r['ns'] for r in actions if r['event'] == 'done')
    active = [r for r in rows if r['start_ns'] >= start and r['end_ns'] <= stop]
    menus=[a for a in actions if a['event']=='menu_layers']
    if len(menus)!=3 or any(not any(layer.get('namespace')=='omarchy-menu'
                                   for monitor in a['layers'].values()
                                   for level in monitor['levels'].values() for layer in level)
                            for a in menus):
        raise ValueError('real menu layer was not observed in all three actions')
    required={'monitor','scene','texture','final_copy','output_commit','surface_buffer'}
    if not required.issubset({r['tag'] for r in active}):
        raise ValueError('missing required rendering/buffer stages')
    result = {'schema':1, 'context':'linux-vm', 'trace_rows':len(rows),
              'active':stats(active), 'terminal':[], 'frames':[],
              'limitations':['CPU submission and callbacks are not physical presentation.',
                            'Nested categories overlap: do not sum across tags.',
                            'A first surface commit can be an empty configure handshake.',
                            'Direct command bypasses physical keyboard. No native hardware validation.']}
    for event in actions:
        if event['event'] == 'terminal_spawn':
            rep = event['rep']
            request = next(a['ns'] for a in actions if a['event']=='terminal_request' and a['rep']==rep)
            commits = sorted((r for r in active if r['tag']=='surface_buffer' and r['arg0']==event['client_pid'] and r['start_ns']>=request),key=lambda r:r['start_ns'])
            result['terminal'].append({'rep':rep,'first_buffer_commit_received_ms':(commits[0]['start_ns']-request)/1e6 if commits else None,
                                       'commits':len(commits),
                                       'render_scope_occupied_ms_before_first_buffer':occupied_ns(rows,request,commits[0]['start_ns'])/1e6 if commits else None})
        if event['event'] == 'frames_end':
            begin = next(a['ns'] for a in actions if a['event']=='frames_start' and a['label']==event['label'])
            selected = [r for r in active if r['start_ns']>=begin and r['end_ns']<=event['ns']]
            frame = {'label':event['label'],'stages':stats(selected)}
            for damage in ('cell','full'):
                values=[r['callback_ms'] for r in event['rows'] if r.get('event')=='frame' and not r['warmup'] and r['damage']==damage]
                if len(values) != 8:
                    raise ValueError('incomplete control frames')
                frame[damage+'_median_ms']=statistics.median(values)
            result['frames'].append(frame)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('trace',type=Path)
    p.add_argument('actions',type=Path)
    a=p.parse_args()
    print(json.dumps(summarize(read_trace(a.trace),[json.loads(s) for s in a.actions.read_text().splitlines()]),indent=2))


if __name__=='__main__':
    main()
