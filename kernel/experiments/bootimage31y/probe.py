#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original, non-bootable Mach-O fixtures and read-only kmutil inspection.

No installer, privileged operation, target connection or image execution exists
in this module. One-page regions are test geometry, not a firmware layout.
"""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
PAGE = 0x4000
BASE = 0xfffffe0007004000
STAGES = ('baseline', 'metadata', 'collection-id', 'exec-segment',
          'linkedit', 'ordered', 'boot-segments')
PROPERTIES = frozenset(('kclo', 'kcep', 'kcrf', 'kcrz', 'kcsf', 'kcsz',
                        'kcxf', 'kcxz', 'kcbf', 'kcbz', 'kcwf', 'kcwz',
                        'kclf', 'kclz'))
SUCCESS = 'Mach-O boot properties derived for boot kernel collection:'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def segment(name, address, offset, size, protection):
    return struct.pack('<II16sQQQQiiII', 0x19, 72, name.encode(), address,
                       size, offset, size, protection, protection, 0, 0)


def thread(entry):
    state = bytearray(272)
    struct.pack_into('<Q', state, 256, entry)
    return struct.pack('<IIII', 5, 288, 6, 68) + state


def header(kind, commands):
    body = b''.join(commands)
    return struct.pack('<8I', 0xfeedfacf, 0x100000c, 2, kind,
                       len(commands), len(body), 1, 0) + body


def plain(stage, kind, address=BASE, offset=0):
    split = stage in ('exec-segment', 'linkedit', 'ordered')
    size = 2 * PAGE if split else PAGE
    blob = bytearray(size)
    commands = [segment('__TEXT', address, offset, PAGE, 1 if split else 5)]
    if split:
        commands.append(segment('__TEXT_EXEC', address + PAGE, offset + PAGE, PAGE, 5))
    pc_offset = (PAGE if split else 0) + 0x800
    commands.append(thread(address + pc_offset))
    h = header(kind, commands)
    blob[:len(h)] = h
    struct.pack_into('<I', blob, pc_offset, 0x14000000)  # Original branch-to-self.
    return blob


def fileset(stage):
    name = b'com.apple.kernel\0'  # Format identifier; no Apple kernel is included.
    size = (32 + len(name) + 7) & ~7
    entry = struct.pack('<IIQQII', 0x80000035, size, BASE + PAGE, PAGE, 32, 0)
    entry += name + bytes(size - 32 - len(name))
    split = stage in ('exec-segment', 'linkedit', 'ordered')
    blob = bytearray(PAGE)
    if split:
        commands = [segment('__TEXT', BASE, 0, 2 * PAGE, 1),
                    segment('__TEXT_EXEC', BASE + 2 * PAGE, 2 * PAGE, PAGE, 5),
                    thread(BASE + 2 * PAGE + 0x800), entry]
    else:
        commands = [segment('__TEXT', BASE, 0, PAGE, 1),
                    segment('__TEXT_BOOT_EXEC', BASE + PAGE, PAGE, PAGE, 5),
                    thread(BASE + PAGE + 0x800), entry]
    h = header(12, commands)
    blob[:len(h)] = h
    return blob + plain(stage, 2, BASE + PAGE, PAGE)


def append_command(blob, command):
    result = bytearray(blob)
    count, size = struct.unpack_from('<II', result, 16)
    end = 32 + size
    if end + len(command) >= 0x800:
        raise ValueError('fixture commands overlap marker')
    result[end:end+len(command)] = command
    struct.pack_into('<II', result, 16, count + 1, size + len(command))
    return result


def with_info(stage, blob):
    metadata = {'_PrelinkInfoDictionary': []}
    if stage not in ('baseline', 'metadata'):
        metadata['_PrelinkKCID'] = hashlib.sha256(blob).digest()[:16]
    data = plistlib.dumps(metadata, fmt=plistlib.FMT_XML)
    offset = len(blob)
    section = struct.pack('<16s16sQQIIIIIIII', b'__info', b'__PRELINK_INFO',
                          BASE + offset, len(data), offset, 0, 0, 0, 0, 0, 0, 0)
    command = struct.pack('<II16sQQQQiiII', 0x19, 152, b'__PRELINK_INFO',
                          BASE + offset, PAGE, offset, PAGE, 1, 1, 1, 0)
    return append_command(blob, command + section) + data + bytes(PAGE - len(data))


def with_linkedit(blob):
    command = segment('__LINKEDIT', BASE + len(blob), len(blob), PAGE, 1)
    return append_command(blob, command) + bytes(PAGE)


def boot_segments(kind):
    blob = bytearray(4 * PAGE)
    commands = [segment('__TEXT', BASE, 0, PAGE, 1),
                segment('__DATA_SPTM', BASE + PAGE, PAGE, PAGE, 3),
                segment('__TEXT_BOOT_EXEC', BASE + 2 * PAGE, 2 * PAGE, PAGE, 5),
                segment('__TEXT_EXEC', BASE + 3 * PAGE, 3 * PAGE, PAGE, 5),
                thread(BASE + 2 * PAGE + 0x800)]
    h = header(kind, commands)
    blob[:len(h)] = h
    for offset in (2 * PAGE + 0x800, 3 * PAGE + 0x800):
        struct.pack_into('<I', blob, offset, 0x14000000)
    return blob


def fixtures(stage):
    if stage not in STAGES:
        raise ValueError('unknown fixture stage')
    if stage == 'boot-segments':
        cases = {'flat-execute': boot_segments(2), 'flat-fileset': boot_segments(12)}
    else:
        cases = {'flat-execute': plain(stage, 2), 'flat-fileset': plain(stage, 12),
                 'one-entry-fileset': fileset(stage)}
    if stage == 'linkedit':
        cases = {k: with_linkedit(v) for k, v in cases.items()}
    if stage != 'baseline':
        cases = {k: with_info(stage, v) for k, v in cases.items()}
    if stage in ('ordered', 'boot-segments'):
        cases = {k: with_linkedit(v) for k, v in cases.items()}
    return {k: bytes(v) for k, v in cases.items()}


def classify(exit_code, stdout, stderr):
    """A zero tool exit is insufficient: it also accompanies property errors."""
    unknown = {'classification': 'UNRECOGNIZED_OUTPUT', 'properties': None}
    notice = 'No variant specified, falling back to release'
    if exit_code == 71:
        error = (r'(?:Could not parse binary: [^\r\n]+|'
                 r'An error occurred while loading boot kernel collection: [^\r\n]+)')
        if stdout or re.fullmatch(r'(?:' + re.escape(notice) + r'\n)?' + error + r'\n?', stderr) is None:
            return unknown
        return {'classification': 'TOOL_ERROR', 'properties': None}
    if exit_code != 0:
        return {'classification': 'TOOL_ERROR', 'properties': None}
    if stderr.strip() not in ('', notice):
        return unknown
    banner = (r'boot kernel collection at [^\r\n]+ '
              r'\([0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}\):\s*')
    if re.fullmatch(r'(?:' + banner + r')?Mach-O boot properties could not be derived: '
                    r'[^\r\n]+\n*', stdout):
        return {'classification': 'PROPERTY_ERROR', 'properties': None}
    if stdout.count(SUCCESS) != 1:
        return unknown
    prefix, tail = stdout.split(SUCCESS, 1)
    if prefix and re.fullmatch(banner, prefix) is None:
        return {'classification': 'UNRECOGNIZED_OUTPUT', 'properties': None}
    match = re.fullmatch(r'\s*\{\s*(.*?)\s*\}\s*', tail, re.DOTALL)
    if match is None:
        return {'classification': 'UNRECOGNIZED_OUTPUT', 'properties': None}
    values = {}
    for line in match[1].splitlines():
        item = re.fullmatch(r'\s*([a-z]{4})\s*:\s*([0-9]+)\s*', line)
        if item is None or item[1] in values or len(item[2]) > 20:
            return {'classification': 'UNRECOGNIZED_OUTPUT', 'properties': None}
        value = int(item[2])
        if not 0 <= value < 1 << 64:
            return {'classification': 'UNRECOGNIZED_OUTPUT', 'properties': None}
        values[item[1]] = value
    if set(values) != PROPERTIES:
        return {'classification': 'UNRECOGNIZED_OUTPUT', 'properties': None}
    return {'classification': 'PROPERTIES_DERIVED', 'properties': values}


def diagnostic(stdout, stderr):
    """Keep only the fixture parser diagnostic, excluding path/ID banner lines."""
    prefixes = ('Could not parse binary:', 'An error occurred while loading boot kernel collection:',
                'Mach-O boot properties could not be derived:')
    return [line for line in (stdout + '\n' + stderr).splitlines() if line.startswith(prefixes)]


def signature(row):
    return {k: row[k] for k in ('stage', 'case', 'bytes', 'sha256', 'exit',
                                'classification', 'properties', 'diagnostic')}


def inspect(path, output):
    command = ['/usr/bin/kmutil', 'inspect', '-B', str(path),
               '-S', str(output / 'absent-system.kc'),
               '-A', str(output / 'absent-auxiliary.kc'),
               '--allow-missing-collections', '--show-mach-boot-properties']
    try:
        result = subprocess.run(command, capture_output=True, timeout=20, check=False)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
        parsed = classify(code, stdout.decode(errors='replace'), stderr.decode(errors='replace'))
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, code = exc.stdout or b'', exc.stderr or b'', None
        parsed = {'classification': 'TIMEOUT', 'properties': None}
    path.with_suffix('.stdout').write_bytes(stdout)
    path.with_suffix('.stderr').write_bytes(stderr)
    return dict(parsed, exit=code, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr),
                diagnostic=diagnostic(stdout.decode(errors='replace'), stderr.decode(errors='replace')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New directory beneath this repository\'s ignored build/ tree')
    parser.add_argument('--inspect', action='store_true', help='Also run read-only Apple kmutil on macOS')
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to((ROOT / 'build').resolve()) or output.exists():
        parser.error('output must be a new directory below repository build/')
    if args.inspect and sys.platform != 'darwin':
        parser.error('--inspect requires macOS; fixture generation works offline elsewhere')
    output.mkdir(parents=True)
    report = {'schema': 1, 'purpose': 'NON_BOOTABLE_FORMAT_FIXTURES', 'cases': [],
              'image_execution': False, 'image_installation': False,
              'security_changes': False, 'boot_acceptance': 'NOT_TESTED',
              'cpu_startup': 'NOT_TESTED', 'hardware_operations': 0}
    if args.inspect:
        report['kmutil_sha256'] = sha(Path('/usr/bin/kmutil').read_bytes())
    stop = False
    for stage in STAGES:
        folder = output / stage
        folder.mkdir()
        for name, data in fixtures(stage).items():
            path = folder / (name + '.macho')
            path.write_bytes(data)
            path.chmod(0o600)
            row = {'stage': stage, 'case': name, 'bytes': len(data), 'sha256': sha(data)}
            row.update(inspect(path, output) if args.inspect else {'classification': 'NOT_INSPECTED'})
            report['cases'].append(row)
            if args.inspect and (row['exit'] is None or row['exit'] < 0):
                stop = True  # Environment/tool failure is not an image result.
                break
        if stop:
            break
    report['completed_matrix'] = not stop
    matches = None
    if args.inspect:
        reference = json.loads(Path(__file__).with_name('expected-results.json').read_text())
        matches = [signature(row) for row in report['cases']] == reference['cases']
        report['matches_reference'] = matches
    (output / 'results.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    counts = {}
    for row in report['cases']:
        state = row['classification']
        counts[state] = counts.get(state, 0) + 1
    print(json.dumps({'counts': counts, 'completed_matrix': not stop, 'matches_reference': matches,
                      'boot_acceptance': 'NOT_TESTED', 'cpu_startup': 'NOT_TESTED'}))
    return 1 if stop or matches is False else 0


if __name__ == '__main__':
    sys.exit(main())
