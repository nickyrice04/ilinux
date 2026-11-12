"""Bounded format experiment. Fixtures contain no executable bootloader code."""
import hashlib
import importlib.util
import json
import platform
import struct
from pathlib import Path

root = Path('/mnt/ilinux/build/m5-route-nov12')
out = Path('/mnt/job/out')
source = root / 'upstream/macho_boot_object.py'
pin = '3e8fff2c09179fc34f89e6ef453e29f0b3bd7b488be296e9afce2257b67642d0'
assert hashlib.sha256(source.read_bytes()).hexdigest() == pin
assert sorted(p.name for p in Path('/sys/class/net').iterdir()) == ['lo']
spec = importlib.util.spec_from_file_location('aura_wrapper', source)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

def commands(blob, offset=0):
    magic, cpu, subtype, kind, count, size, flags, reserved = struct.unpack_from('<8I', blob, offset)
    assert magic == 0xfeedfacf and cpu == 0x0100000c
    pos = offset + 32
    assert pos + size <= len(blob)
    result = []
    for _ in range(count):
        cmd, length = struct.unpack_from('<2I', blob, pos)
        assert length >= 8 and length % 8 == 0 and pos + length <= offset + 32 + size
        result.append((cmd, blob[pos:pos + length]))
        pos += length
    assert pos == offset + 32 + size
    return kind, result

cases = []
for size in (0x30000, 0x40001, 0x200000):
    raw = bytearray(size)
    raw[0x808:0x810] = b'AURALOAD'
    raw[0x2000:0x2020] = b'OWNED NONEXECUTABLE TEST FIXTURE'.ljust(32, b'\0')
    raw = bytes(raw)
    image = tool.wrap(raw)
    assert image == tool.wrap(raw)
    kind, cmds = commands(image)
    assert kind == 12
    segments = {}
    for cmd, body in cmds:
        if cmd == 0x19:
            name = body[8:24].rstrip(b'\0').decode('ascii')
            assert name not in segments
            segments[name] = struct.unpack_from('<4Q', body, 24)
    assert list(segments) == ['__TEXT', '__PRELINK_TEXT', '__TEXT_EXEC', '__PRELINK_INFO', '__DATA', '__LINKEDIT']
    end = 0
    for vmaddr, vmsize, fileoff, filesize in segments.values():
        assert fileoff == end and vmaddr - tool.VA_BASE == fileoff
        assert filesize == vmsize and filesize % 0x4000 == 0
        assert fileoff + filesize <= len(image)
        end += filesize
    assert end == len(image)
    text = segments['__TEXT_EXEC']
    assert image[text[2]:text[2]+len(raw)] == raw
    threads = [body for cmd, body in cmds if cmd == 5]
    assert len(threads) == 1
    regs = struct.unpack_from('<34Q', threads[0], 16)
    assert regs[32] == text[0] + 0x800 and regs[16] == text[0]
    members = [body for cmd, body in cmds if cmd == 0x80000035]
    assert len(members) == 1
    _, member_offset, name_offset = struct.unpack_from('<QQI', members[0], 8)
    assert members[0][name_offset:].rstrip(b'\0') == b'com.apple.kernel'
    member_kind, member_cmds = commands(image, member_offset)
    assert member_kind == 2
    member_text = [body for cmd,body in member_cmds if cmd == 0x19 and body[8:24].rstrip(b'\0') == b'__TEXT_EXEC']
    assert len(member_text) == 1 and struct.unpack_from('<4Q', member_text[0], 24) == text
    cases.append({'raw_bytes':size, 'wrapped_bytes':len(image), 'raw_roundtrip':True,
                  'deterministic':True, 'entry_offset':hex(regs[32]-tool.VA_BASE),
                  'contains_boot_exec_segment':False,
                  'sha256':hashlib.sha256(image).hexdigest()})
    if size == 0x30000:
        (out/'SYNTHETIC-NONEXECUTABLE.macho').write_bytes(image)

refusals = []
for name, invalid in [('missing-load-header', bytes(0x30000)), ('already-wrapped', image)]:
    try:
        tool.wrap(invalid)
    except ValueError:
        refusals.append(name)
    else:
        raise AssertionError('expected refusal')

report = {'schema':'ilinux-nov12-format-check-v1','scope':'SYNTHETIC_FORMAT_ONLY',
          'source_commit':'bd9f3e8273dc79ae9095c19c2c4f32218446ad4e',
          'source_git_blob':'0a3b111958e3319e743f1676ffbd6d7019f9930b',
          'source_sha256':pin,'kernel':platform.release(),'python':platform.python_version(),
          'network_interfaces':['lo'],'physical_hardware_access':False,
          'cases':cases,'expected_input_refusals':refusals,
          'padded_128m_window_tested':False,'native_boot_tested':False,
          'apple_firmware_executed':False,'restart_ready':False}
(out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
