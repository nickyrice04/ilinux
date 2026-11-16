# SPDX-License-Identifier: MIT
"""Small bounded FDT reader/writer for offline input qualification."""
import struct
from dataclasses import dataclass, field

MAGIC = 0xd00dfeed
MAX_BYTES = 4 * 1024 * 1024

@dataclass
class Node:
    name: str
    props: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

def text(value):
    if not value or value[-1:] != b'\0':
        raise ValueError('unterminated string property')
    return value[:-1].decode('ascii').split('\0')

def walk(node, path=''):
    here = path + ('/' + node.name if node.name else '')
    yield here or '/', node
    for child in node.children:
        yield from walk(child, here)

def parse(blob):
    if not 40 <= len(blob) <= MAX_BYTES:
        raise ValueError('FDT size outside bound')
    magic,total,so,stro,ro,version,last,boot,strlen,slen=struct.unpack_from('>10I',blob)
    if magic != MAGIC or total != len(blob) or version < 17 or last > 17:
        raise ValueError('unsupported FDT header')
    for off,size in ((so,slen),(stro,strlen)):
        if off < 40 or off+size > total:
            raise ValueError('FDT region outside file')
    if not (so+slen <= stro or stro+strlen <= so):
        raise ValueError('overlapping FDT regions')
    if so%4 or ro%8:
        raise ValueError('unaligned FDT regions')
    reservations=[]
    pos=ro
    for _ in range(65536):
        if pos < 40 or pos+16 > total:
            raise ValueError('invalid reservation table')
        addr,size=struct.unpack_from('>2Q',blob,pos);pos+=16
        if not addr and not size:break
        if not size or addr+size > 1<<64:raise ValueError('bad reservation')
        reservations.append((addr,size))
    else:raise ValueError('unterminated reservation table')
    if not all(pos<=off or off+size<=ro for off,size in ((so,slen),(stro,strlen))):
        raise ValueError('reservation table overlaps another region')
    strings=blob[stro:stro+strlen]
    stack=[];root=None;pos=so;end=so+slen
    def aligned(p):return (p+3)&~3
    while pos+4 <= end:
        token,=struct.unpack_from('>I',blob,pos);pos+=4
        if token==1:
            stop=blob.find(b'\0',pos,end)
            if stop<0:raise ValueError('unterminated node name')
            name=blob[pos:stop].decode('ascii');pos=aligned(stop+1)
            if '/' in name:raise ValueError('invalid node name')
            node=Node(name)
            if stack:
                if any(c.name==name for c in stack[-1].children):raise ValueError('duplicate node')
                stack[-1].children.append(node)
            else:
                if root is not None or name:raise ValueError('invalid root')
                root=node
            stack.append(node)
            if len(stack)>256:raise ValueError('excessive FDT depth')
        elif token==2:
            if not stack:raise ValueError('unbalanced end-node')
            stack.pop()
        elif token==3:
            if not stack or pos+8>end:raise ValueError('invalid property')
            size,no=struct.unpack_from('>2I',blob,pos);pos+=8
            stop=strings.find(b'\0',no)
            if stop<0 or no>=len(strings) or pos+size>end:raise ValueError('invalid property bounds')
            name=strings[no:stop].decode('ascii')
            if not name or name in stack[-1].props:raise ValueError('duplicate property')
            stack[-1].props[name]=blob[pos:pos+size];pos=aligned(pos+size)
        elif token==4:continue
        elif token==9:
            if root is None or stack:raise ValueError('unbalanced tree')
            if any(blob[pos:end]):raise ValueError('data after FDT end')
            return root,reservations,boot
        else:raise ValueError('unknown structure token')
    raise ValueError('missing FDT end')

def encode(root,reservations,boot):
    strings=bytearray();names={};body=bytearray()
    def u32(*v):return struct.pack('>'+str(len(v))+'I',*v)
    def pad():body.extend(b'\0'*(-len(body)%4))
    def emit(n):
        body.extend(u32(1)+n.name.encode('ascii')+b'\0');pad()
        for name,value in n.props.items():
            if name not in names:
                names[name]=len(strings);strings.extend(name.encode('ascii')+b'\0')
            body.extend(u32(3,len(value),names[name])+value);pad()
        for child in n.children:emit(child)
        body.extend(u32(2))
    emit(root);body.extend(u32(9))
    reserve=b''.join(struct.pack('>2Q',*r) for r in reservations)+bytes(16)
    ro=40;so=ro+len(reserve);stro=so+len(body);total=stro+len(strings)
    if total>MAX_BYTES:raise ValueError('encoded FDT exceeds bound')
    return struct.pack('>10I',MAGIC,total,so,stro,ro,17,16,boot,len(strings),len(body))+reserve+body+strings
