#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the COMPLETE original ordered31AE payload with synthetic cold inputs only."""
import argparse,hashlib,importlib.util,json,struct,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('qmp31ab',ROOT/'kernel/experiments/translation31ab/run.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
BASE=0x40400000; FB=0x44000000; VA=0x80000000; ARGS=0x45000000
RECORD=0x4000; ENTRY=0x14000; STACK_TOP=0x10000; VECTORS=0x14800

def sha(b):return hashlib.sha256(b).hexdigest()
def emit(p,j):p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def tables(mode,kind):
    b=bytearray(0x10000)
    def q(o,v):struct.pack_into('<Q',b,o,v)
    if mode=='16k-vhe':
        # 39bitVA,16K L1(11bits),L2,L3. L1[0]->L2; L2[32..39] identity32MiBblocks.
        q(0,0x43004003)
        for i in range(32,40):q(0x4000+i*8,(i<<25)|0x701)
        q(0x4000+64*8,0x43008003)
        for i in range(4):q(0x8000+i*8,(FB+i*0x4000)|(0x707 if kind in ('wb','wb30') else 0x703))
    else:
        q(8,0x40000701);q(16,0x43001003);q(0x1000,0x43002003)
        for i in range(16):q(0x2000+i*8,(FB+i*0x1000)|0x703)
        if kind=='ro-last':q(0x2000+3*8,(FB+0x3000)|0x783)
        if kind=='unmapped-last':q(0x2000+3*8,0)
        if kind in ('wb','wb30'):
            for i in range(16):q(0x2000+i*8,(FB+i*0x1000)|0x707)
        if kind=='device':
            for i in range(16):q(0x2000+i*8,(FB+i*0x1000)|0x70b)
        if kind=='wrong-pa':q(0x2000,(FB+0x10000)|0x703)
        if kind=='image-alias':
            for i in range(16):q(0x2000+i*8,(BASE+i*0x1000)|0x703)
    return bytes(b)

def args(kind):
    b=bytearray(0x10000)
    struct.pack_into('<HH',b,0,2,2)
    for off,v in [(8,0x40000000),(16,0x40000000),(24,0x10000000),(40,FB|3),(48,1),(56,1024),(64,256),(72,64),(80,32)]:struct.pack_into('<Q',b,off,v)
    struct.pack_into('<I',b,0x4000+416,10)
    struct.pack_into('<QQ',b,0x4000+424,ARGS+0x8000,ARGS+0xc000)
    struct.pack_into('<I',b,0x8000,1)
    struct.pack_into('<QQI',b,0xc000,FB,VA,4)
    reason,boot,monitor=0,ARGS,ARGS+0x4000
    if kind in ('depth30','wb30'):struct.pack_into('<Q',b,80,30)
    if kind=='reason':reason=1
    if kind=='reason-wide':reason=0x100000000
    if kind=='boot-unmapped':boot=0xa0000000
    if kind=='monitor-unmapped':monitor=0xa0004000
    if kind=='count-unmapped':struct.pack_into('<Q',b,0x4000+424,0xa0008000)
    if kind=='table-unmapped':struct.pack_into('<Q',b,0x4000+432,0xa000c000)
    if kind=='count-zero':struct.pack_into('<I',b,0x8000,0)
    if kind=='count-large':struct.pack_into('<I',b,0x8000,65)
    if kind=='version':struct.pack_into('<I',b,0x4000+416,9)
    if kind=='video-version':struct.pack_into('<H',b,0,1)
    if kind=='range-wrap':struct.pack_into('<QQI',b,0xc000,0xffffffffffffc000,VA,2)
    if kind=='image-alias':
        struct.pack_into('<Q',b,40,BASE|3);struct.pack_into('<Q',b,0xc000,BASE)
    return bytes(b),reason,boot,monitor

def case(qemu,payload,output,label,mode,kind,status,park_offset):
    out=output/label;out.mkdir();code=bytearray(payload);code[RECORD:RECORD+512]=b'\xa5'*512
    if kind=='fault-after-paint':
        if struct.unpack_from('<I',code,park_offset)[0]!=0x14000000:raise ValueError('park symbol mismatch')
        struct.pack_into('<I',code,park_offset,0xd4200000)
    (out/'payload.bin').write_bytes(code)
    t=tables(mode,kind);(out/'tables.bin').write_bytes(t)
    a,reason,boot,monitor=args(kind);(out/'args.bin').write_bytes(a)
    target=bytes([0x35])*0x10000;(out/'target.bin').write_bytes(target)
    hcr=0x488000000 if 'vhe' in mode else 0x80000000
    # Low-only fixture TCR:39VA/40PA. EPD1 disables unused high VA half in VHE.
    tcr=0x28099b519 if mode=='16k-vhe' else 0x280993519 if mode=='4k-vhe' else 0x80823519
    for cmd in [["cc",'-ffreestanding',f'-DTEST_ENTRY={BASE+ENTRY}',f'-DTEST_HCR={hcr}',f'-DTEST_TCR={tcr}',f'-DTEST_REASON={reason}',f'-DTEST_BOOT={boot}',f'-DTEST_MONITOR={monitor}','-c',str(HERE/'bootstrap.S'),'-o',str(out/'bootstrap.o')],['ld','--no-undefined','--build-id=none','-e','test_bootstrap','-Ttext=0x42000000',str(out/'bootstrap.o'),'-o',str(out/'bootstrap.elf')],['objcopy','-O','binary','-j','.text',str(out/'bootstrap.elf'),str(out/'bootstrap.bin')]]:
        subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    sock=out/'q.sock'
    if len(str(sock).encode())>100:raise ValueError('QMP path too long')
    cmd=[qemu,'-machine','virt,secure=off,virtualization=on','-cpu','max','-accel','tcg','-smp','1','-m','256M','-nodefaults','-display','none','-nic','none','-serial','none','-monitor','none','-S','-qmp',f'unix:{sock},server=on,wait=off']
    for f,pa in [('payload.bin',BASE),('bootstrap.bin',0x42000000),('tables.bin',0x43000000),('args.bin',ARGS),('target.bin',FB)]:cmd+=['-device',f'loader,file={out/f},addr={pa:#x},force-raw=on']
    cmd+=['-device','loader,addr=0x42000000,cpu-num=0'];emit(out/'command.json',cmd)
    p=None;qm=None;start=time.monotonic()
    with (out/'qemu.log').open('wb') as log:
        try:
            p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT);deadline=time.monotonic()+10
            while qm is None:
                if p.poll() is not None or time.monotonic()>deadline:raise RuntimeError('QEMU startup failed')
                try:qm=m.QMP(sock)
                except (FileNotFoundError,ConnectionRefusedError):time.sleep(.02)
            qm.call('cont')
            while True:
                raw=qm.memory(BASE+RECORD,512,out/'capture.bin');w=struct.unpack('<64Q',raw)
                if w[2] in ((0xdead,) if kind=='fault-after-paint' else (7,0x80,0xdead)):break
                if time.monotonic()>deadline:raise RuntimeError(f'no terminal phase: {w[:8]}')
                time.sleep(.01)
            qm.call('stop');raw=qm.memory(BASE+RECORD,512,out/'capture.bin');w=struct.unpack('<64Q',raw)
            if w[0]!=0x4341313347495356 or w[1]!=1:raise RuntimeError('record magic/version')
            if w[7]!=8 or w[8]!=0x3c0 or w[9]!=0x40301000 or w[10]!=BASE+STACK_TOP or w[11]!=BASE+VECTORS:raise RuntimeError('entry register profile mismatch')
            if w[12]!=hcr or not w[13]&1 or w[14]!=tcr:raise RuntimeError('HCR/TCR/MMU actual profile mismatch')
            if (w[4],w[5],w[6])!=(reason,boot,monitor):raise RuntimeError('entry arguments not preserved')
            if w[3]!=status or w[2]!=(0xdead if kind=='fault-after-paint' else 7 if status==0 else 0x80):raise RuntimeError(f'{label} phase/status {w[2:4]} expected {status}')
            after=qm.memory(FB,len(target),out/'target-after.bin')
            if qm.memory(ARGS,len(a),out/'args-after.bin')!=a:raise RuntimeError('input record changed')
            if qm.memory(0x43000000,len(t),out/'tables-after.bin')!=t:raise RuntimeError('fixture tables changed')
            expected=bytearray(target)
            if status==0 or kind=='fault-after-paint':
                if w[24]!=1 or w[25]!=512:raise RuntimeError('incomplete paint')
                if kind in ('wb','wb30'):
                    line=4<<((w[38]>>16)&15)
                    expected_lines=len({(VA+y*1024+x)//line*line for y in range(16) for x in range(128)})
                    if w[39]!=line or w[40]!=expected_lines or w[41]!=expected_lines:raise RuntimeError('WB cache-clean coverage incomplete')
                elif w[39] or w[40] or w[41]:raise RuntimeError('NC unexpectedly cleaned cache')
                # Independent write-footprint check: exactly selected32x16 rawpixels.
                for y in range(16):
                    for x in range(32):
                        off=y*1024+x*4
                        expected[off:off+4]=after[off:off+4]
                if after==target:raise RuntimeError('no framebuffer change')
                for y in range(16):
                    for x in range(32):
                        v=struct.unpack_from('<I',after,y*1024+x*4)[0]
                        foreground=(y==0 or y==15 or x==0 or x==31 or ((y^x)&1))
                        if v!=((0x3ff55555 if kind in ('depth30','wb30') else 0x00ff55aa) if foreground else 0):raise RuntimeError('marker pattern differs')
                if bytes(expected)!=after:raise RuntimeError('paint escaped selected rectangle')
                if kind=='fault-after-paint' and (w[26]!=4 or w[27]>>26!=0x3c or w[28]!=BASE+park_offset):raise RuntimeError('fatal vector capture mismatch')
                if w[22]!=FB or w[23]!=VA:raise RuntimeError('framebuffer identity')
            else:
                if w[24] or w[25] or w[40] or after!=target:raise RuntimeError('refusal performed a partial paint')
            result={'case':label,'mode':mode,'status':'PASS','expected_refusal':status,'record_words':[hex(x) for x in w],'capture_sha256':sha(raw),'framebuffer_sha256':sha(after),'painted_pixels':w[25],'seconds':time.monotonic()-start,'native':'NOT_RUN'};emit(out/'result.json',result);return result
        finally:
            if qm:
                try:qm.call('quit')
                except (OSError,RuntimeError,ValueError):pass
                qm.close()
            if p:
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--payload',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--qemu',required=True);p.add_argument('--layout',type=Path,required=True);a=p.parse_args();o=a.output.resolve();o.mkdir(parents=True,exist_ok=False)
    bound=[HERE/'bootstrap.S',HERE/'run.py',ROOT/'kernel/experiments/translation31ab/run.py']
    bindings=[{'file':str(p.relative_to(ROOT)),'sha256':sha(p.read_bytes())} for p in bound]
    emit(o/'source-bindings.json',bindings)
    payload=a.payload.read_bytes();assert len(payload)==0x24000
    layout=json.loads(a.layout.read_text());park_offset=layout['symbols']['native_park']['offset']
    for name,offset in [('native_image_base',0),('native_record',RECORD),('native_stack_bottom',0x8000),('native_stack_top',STACK_TOP),('native_entry',ENTRY),('native_vectors',VECTORS),('native_late_park',0x10000),('native_image_end',0x24000)]:
        if layout['symbols'][name]['offset']!=offset:raise ValueError('ordered payload symbol mismatch: '+name)
    if layout['payload_sha256']!=sha(payload):raise ValueError('payload/layout binding mismatch')
    report={'status':'FAIL','native':'NOT_RUN','apple_firmware':False,'payload_sha256':sha(payload),'cases':[]}
    trials=[('4k','valid',0),('4k-vhe','valid',0),('16k-vhe','valid',0),('16k-vhe','wb',0),('4k','reason',1),('4k','reason-wide',1),('4k','boot-unmapped',8),('4k','monitor-unmapped',9),('4k','count-unmapped',11),('4k','table-unmapped',13),('4k','count-zero',12),('4k','count-large',12),('4k','version',10),('4k','video-version',15),('4k','range-wrap',14),('4k','ro-last',17),('4k','unmapped-last',17),('4k','wb',0),('4k-vhe','wb',0),('4k-vhe','depth30',0),('4k-vhe','wb30',0),('4k','device',19),('4k','wrong-pa',18),('4k','image-alias',20),('4k','fault-after-paint',22),('4k-vhe','fault-after-paint',22)]
    try:
        report['qemu_version']=subprocess.check_output([a.qemu,'--version'],text=True)
        for mode,kind,status in trials:report['cases'].append(case(a.qemu,payload,o,mode+'-'+kind,mode,kind,status,park_offset))
        report['status']='PASS'
    finally:
        report['source_bindings_sha256']=sha((o/'source-bindings.json').read_bytes())
        report['source_files_unchanged']=all(sha(p.read_bytes())==b['sha256'] for p,b in zip(bound,bindings))
        if not report['source_files_unchanged']:report['status']='FAIL'
        emit(o/'results.json',report)
    print(json.dumps({'status':report['status'],'cases':len(report['cases'])}))
    return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
