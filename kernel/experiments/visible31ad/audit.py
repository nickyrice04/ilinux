#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Original 31AC audit adapted for the ordered 31AD ELF geometry."""
from __future__ import annotations
import hashlib
import struct

SIZE = 0x24000


def require(value, message):
    if not value:
        raise ValueError(message)


def audit(data: bytes, base: int):
    require(64 <= len(data) <= 4 * 1024 * 1024, "ELF size")
    require(data[:7] == b"\x7fELF\x02\x01\x01", "ELF64 little-endian required")
    fields = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    kind,machine,version,entry,po,so,flags,eh,ps,pn,ss,sn,si = fields
    require((kind,machine,version,entry,eh,ps,ss) == (2,183,1,base+0x14000,64,56,64), "ELF identity")
    require(po + ps*pn <= len(data) and so + ss*sn <= len(data) and si < sn, "ELF table bounds")
    sections = [struct.unpack_from("<IIQQQQIIQQ", data, so+i*ss) for i in range(sn)]
    names = sections[si]
    require(names[4]+names[5] <= len(data), "section names bounds")
    def string(offset, size, index):
        require(index < size and offset+size <= len(data), "string bounds")
        end = data.find(b"\0", offset+index, offset+size)
        require(end >= 0, "unterminated string")
        return data[offset+index:end].decode("ascii")
    allocated = []
    symbols = {}
    functions = []
    for s in sections:
        name,typ,sf,addr,off,size,link,info,align,entsize = s
        label = string(names[4], names[5], name)
        require(not (typ in (4,9) and size), "retained relocations")
        require(not (typ in (6,11) and size), "dynamic linkage")
        if sf & 2 and size:
            require(typ == 1 and off+size <= len(data), "unexpected allocated section")
            allocated.append((label,addr-base,size,sf))
        if typ != 2:
            continue
        require(entsize == 24 and size%24 == 0 and off+size <= len(data) and link < sn, "symbol table bounds")
        strings = sections[link]
        for pos in range(off,off+size,24):
            ni,kind,other,index,value,extent = struct.unpack_from("<IBBHQQ",data,pos)
            label = string(strings[4],strings[5],ni)
            require(not label or index != 0, "undefined symbol: "+label)
            if not label or label.startswith("$"):
                continue
            if label in symbols:
                require(symbols[label] == (value,extent), "duplicate symbol: "+label)
            symbols[label]=(value,extent)
            if kind & 15 == 2 and extent:
                functions.append((label,value,extent))
    require(allocated == [(".late",0x4000,0x4000,6),(".data",0x8000,0xc000,3),(".boot",0x14000,0x10000,6)], "allocated section geometry")
    payload = bytearray(SIZE)
    loads=[]
    for i in range(pn):
        typ,perm,off,va,pa,fs,ms,align = struct.unpack_from("<IIQQQQQQ",data,po+i*ps)
        if typ != 1:
            continue
        require(va==pa and fs==ms and off+fs <= len(data) and va>=base and va+ms <= base+SIZE, "load bounds")
        loads.append((va-base,ms,perm))
        payload[va-base:va-base+fs]=data[off:off+fs]
    require(loads == [(0x4000,0x4000,5),(0x8000,0xc000,6),(0x14000,0x10000,5)], "load geometry")
    require(not any(payload[:0x4000]), "header canvas not zero")
    require(not any(payload[0x8000:0x14000]), "owned storage not zero")
    require(not any(payload[0x4004:0x8000]), "unused normal executable padding not zero")
    for name,offset in (("native_image_base",0),("native_record",0x8000),
            ("native_stack_bottom",0xc000),("native_stack_top",0x14000),
            ("native_entry",0x14000),("native_vectors",0x14800),
            ("native_late_park",0x4000),("native_image_end",SIZE)):
        require(symbols[name][0]==base+offset, "symbol geometry: "+name)
    for name in ("native_park","native_fault_park","native_late_park"):
        offset=symbols[name][0]-base
        require(struct.unpack_from("<I",payload,offset)[0]==0x14000000, "park must self-branch")
    for slot in range(16):
        offset=0x14800+slot*128
        move,branch=struct.unpack_from("<II",payload,offset)
        delta=(symbols["native_fatal"][0]-base-offset-4)//4
        require(move==0xd2800011+(slot<<5) and branch==0x14000000+(delta & 0x3ffffff),
                "vector slot instructions")
        require(not any(payload[offset+8:offset+128]), "vector slot padding")
    for name,at in (("visible31ac_read_at",0xd50c7800),("visible31ac_write_at",0xd50c7820)):
        addr,size=symbols[name]
        words=struct.unpack_from("<7I",payload,addr-base)
        require(size==28 and words==(0xd5387402,at,0xd5033fdf,0xd5387400,0xd5187402,0xd5033fdf,0xd65f03c0), "AT helper body")
    # Code generated from the reviewed C uses no indirect calls or privileged
    # transitions. This is a system-operation check, not a proof of all C logic.
    count=0
    allowed_system={0xd5034fdf,0xd50041bf,0xd5033f9f,0xd5033fdf,0xd503201f,
                    0xd50c7800,0xd50c7820,0xd50b7a20}
    for label,addr,size in functions:
        require(size%4==0 and base+0x14000 <= addr and addr+size <= base+0x24000, "function bounds: "+label)
        for off in range(addr-base,addr-base+size,4):
            word=struct.unpack_from("<I",payload,off)[0]
            count+=1
            require(word not in (0x00201420,0x00201000), "guarded transition")
            require(word & 0xffe0001f not in (0xd4000001,0xd4000002,0xd4000003), "supervisor call")
            require(word & 0xfffffc1f not in (0xd61f0000,0xd63f0000), "indirect branch/call")
            if word >> 24 == 0xd5:
                is_read=(word & 0xfff00000)==0xd5300000
                permitted_write=(word & ~31) in (0xd5187400,0xd51cc000)
                require(is_read or permitted_write or word in allowed_system,
                        "unapproved system instruction in "+label+" at "+hex(off))
            if word & 0x7c000000 == 0x14000000:
                delta=word & 0x3ffffff
                if delta & 0x2000000:delta-=0x4000000
                target=off+delta*4
                require(0x14000 <= target < 0x24000, "branch outside boot executable")
    metadata={"payload_bytes":SIZE,"payload_sha256":hashlib.sha256(payload).hexdigest(),
              "symbols":{k:{"offset":v[0]-base,"bytes":v[1]} for k,v in sorted(symbols.items()) if k.startswith(("native_","visible31ac_"))},
              "load_segments":loads,"function_instruction_words_checked":count,
              "entry_offset":0x14000,"vectors_offset":0x14800,"body_offset":0x16000,
              "normal_executable_range":[0x4000,0x8000],"boot_executable_range":[0x14000,0x24000],
              "owned_data_range":[0x8000,0x14000],"normal_text_before_boot_text":True,
              "undefined_symbols":0,"retained_relocations":0,"guarded_transitions":0,
              "system_operation_allowlist":True,"complete_C_behavior_proof":False}
    return bytes(payload),metadata
