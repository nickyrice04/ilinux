#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an original integrated visible-entry payload; never execute it."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OWN=("layout.h","entry.S","probe.S","bridge.c","runtime.S","image.ld","audit.py","run.py","README.md")
FROZEN={"kernel/experiments/observer31ab/observer.c":"0f5dbef5e8b9497ea792bba1ac4addf8a3c33c32ada62b9da9082c4985706b43",
        "kernel/experiments/observer31ab/observer.h":"58cdd504661afcc06f7bef477315a50bd6e724c477f4eb1b54972eb9a7852868"}
FLAGS=["-ffreestanding","-fno-pic","-fno-pie","-fno-stack-protector","-fno-unwind-tables",
       "-fno-asynchronous-unwind-tables","-fno-jump-tables","-mcmodel=tiny","-mgeneral-regs-only",
       "-mstrict-align","-mbranch-protection=none","-O2"]

def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def command(args,out,label):
    done=subprocess.run(args,cwd=HERE,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=60)
    result={"argv":args,"returncode":done.returncode,"stdout":done.stdout,"stderr":done.stderr}
    save(out/(label+".json"),result)
    if done.returncode:raise RuntimeError(label+" failed; inspect log")
    return result
def bindings():
    rows=[]
    for path in [HERE/n for n in OWN]+[ROOT/n for n in FROZEN]:
        if path.is_symlink():raise ValueError("source symlink")
        name=str(path.relative_to(ROOT));data=path.read_bytes();digest=sha(data)
        if name in FROZEN and digest!=FROZEN[name]:raise ValueError("frozen observer changed")
        rows.append({"file":name,"bytes":len(data),"sha256":digest})
    return rows
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True);p.add_argument("--cc",default="cc")
    p.add_argument("--ld",default="ld");p.add_argument("--target")
    p.add_argument("--compile-only",action="store_true")
    a=p.parse_args();out=a.output.resolve()
    if out.exists() or out==HERE or HERE in out.parents:p.error("fresh output outside sources required")
    out.mkdir(parents=True)
    report={"schema":1,"status":"FAIL","host":platform.platform(),"native":"NOT_QUALIFIED",
            "payload_executed":False,"monitor_calls":0,"images":[]}
    try:
        before=bindings();save(out/"source-bindings.json",before)
        report["source_bindings_sha256"]=sha((out/"source-bindings.json").read_bytes())
        report["compiler"]=command([a.cc,"--version"],out,"compiler")["stdout"]
        objects=[]
        for source in ("entry.S","probe.S","runtime.S","bridge.c","../observer31ab/observer.c"):
            label=Path(source).stem;obj=out/(label+".o")
            args=[a.cc]+(["--target="+a.target] if a.target else [])+FLAGS
            if source.endswith(".c"):args += ["-std=c11","-Wall","-Wextra","-Werror","-pedantic"]
            command(args+["-c",source,"-o",str(obj)],out,label+"-compile")
            objects.append(str(obj))
        report["objects"]=[{"file":Path(n).name,"sha256":sha(Path(n).read_bytes())} for n in objects]
        if a.compile_only:report["status"]="COMPILE_PASS_NOT_LINKED"
        else:
            spec=importlib.util.spec_from_file_location("_visible_audit",HERE/"audit.py")
            checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
            report["linker"]=command([a.ld,"--version"],out,"linker")["stdout"]
            canonical=None
            fields={m.group(1):int(m.group(2),0) for m in re.finditer(r"^#define (V31_[A-Z0-9_]+) (0x[0-9a-fA-F]+|[0-9]+)$",(HERE/"layout.h").read_text(),re.M)}
            for label,base in (("canonical",0),("slid",0x40400000)):
                elf=out/(label+".elf")
                command([a.ld,"--fatal-warnings","--no-undefined","--build-id=none","-z","max-page-size=0x4000",
                         "--defsym",f"visible_image_base={base}","-T","image.ld",*objects,"-o",str(elf)],out,label+"-link")
                payload,metadata=checker.audit(elf.read_bytes(),base)
                if canonical is None:canonical=payload
                elif payload!=canonical:raise ValueError("payload changed across aligned slide")
                metadata["record_fields"]=fields
                save(out/(label+"-layout.json"),metadata)
                (out/(label+"-payload.bin")).write_bytes(payload)
                report["images"].append({"label":label,"base":base,"elf_sha256":sha(elf.read_bytes()),"audit":metadata})
            (out/"payload.bin").write_bytes(canonical)
            save(out/"layout.json",report["images"][0]["audit"])
            report["slide_bytes_identical"]=True
            report["payload_sha256"]=sha(canonical)
            report["status"]="LINK_PASS_NOT_EXECUTED"
        if bindings()!=before:raise ValueError("sources changed during build")
        report["source_files_unchanged"]=True
    except Exception as error:
        report["status"]="FAIL";report["error"]=str(error)
    save(out/"results.json",report)
    print(json.dumps({"status":report["status"],"native":report["native"],"results":str(out/"results.json")}))
    return int(report["status"]=="FAIL")
if __name__=="__main__":raise SystemExit(main())
