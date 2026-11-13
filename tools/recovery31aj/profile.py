# SPDX-License-Identifier: MIT
"""Strict public transaction profile; no discovery, commands or writes."""
import hashlib
import json
import re

SCHEMA = 'ilinux31aj-recovery-profile-v1'
TARGET = {'model':'Mac17,6','board':'j716c','chip_id':'0x6050'}
ROLLBACK_BYTES = 3932160
ROLLBACK_SHA = 'ff75f4a919d8469530834787d4e53f378892d4f4e80aed4f9affbf5172072664'
INITIAL_SHA = '166bea74bf515473057dfd29dc89127d04768945a451e497cc80a9fc53d4951b'
OLD_CANDIDATE = '0d43feada6d758fcfea2ce78b4fd9f21ae4b7a7450ab06ba9e8c6c06b834dc4d'
NAMES = {'candidate':'candidate.macho','rollback':'m1n1-boot021.bin','helper':'ilinux31aj-reader'}


def require(value, reason):
    if not value:raise ValueError(reason)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result,'duplicate JSON key')
        result[key] = value
    return result


def sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def validate(value):
    require(type(value) is dict and set(value)=={'schema','target','files','native_deadline_ms',
            'raw_policy_strategy','initial_payload','final_payload','publication_authorizes_writes'},'profile schema')
    require(value['schema']==SCHEMA and value['target']==TARGET,'profile target')
    require(value['publication_authorizes_writes'] is False,'publication is not authorization')
    require(value['raw_policy_strategy']=='ctrr_only','only the documented -c strategy is supported')
    require(value['initial_payload']=='31AF' and value['final_payload']=='BOOT021','profile transition')
    require(type(value['native_deadline_ms']) is int and 0<value['native_deadline_ms']<=90000,'native deadline')
    files = value['files']
    require(type(files) is dict and set(files)==set(NAMES),'profile files')
    for role, name in NAMES.items():
        item = files[role]
        require(type(item) is dict and set(item)=={'name','bytes','sha256'},'file record')
        require(item['name']==name and sha(item['sha256']),'file binding')
        limit = 160*1024*1024 if role=='candidate' else 8*1024*1024
        require(type(item['bytes']) is int and 0<item['bytes']<=limit,'file byte bound')
    require((files['rollback']['bytes'],files['rollback']['sha256'])==(ROLLBACK_BYTES,ROLLBACK_SHA),'rollback pin')
    require(files['candidate']['sha256'] not in (ROLLBACK_SHA,INITIAL_SHA,OLD_CANDIDATE),'new readable candidate required')
    require(files['candidate']['sha256']!=files['helper']['sha256'],'role collision')
    return value


def load(data):
    require(type(data) is bytes and 0<len(data)<=16384,'profile input bound')
    return validate(json.loads(data,object_pairs_hook=pairs))


def canonical(value):
    return (json.dumps(validate(value),sort_keys=True,indent=2)+'\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()
