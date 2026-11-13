#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Linux VM only: compile pinned public payload parser with original fake hooks."""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('direct31ai_inline', HERE / 'inline.py')
inline = importlib.util.module_from_spec(spec); sys.modules[spec.name] = inline; spec.loader.exec_module(inline)


def between(source, first, last):
    position = source.index(first)
    return source[position:source.index(last, position)]


def source_function(source, signature):
    position = source.index(signature)
    return source[position:source.index('\n}\n', position) + 3]


def main():
    if sys.platform != 'linux':
        raise SystemExit('isolated Linux VM required; public source is never executed on macOS')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-tree', type=Path, required=True)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--dtb', type=Path, required=True)
    parser.add_argument('--initramfs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pins = inline.qualify_source(args.source_tree)
    payload = inline.read_regular(args.payload, inline.MAX_RAW)
    image = inline.read_regular(args.image, inline.MAX_IMAGE)
    dtb = inline.read_regular(args.dtb, 4 * inline.MIB)
    initrd = inline.read_regular(args.initramfs, inline.MAX_INITRD)
    positions = inline.verify_payload(payload, image, dtb, initrd)
    args.output.mkdir(parents=True, exist_ok=False)
    source = (args.source_tree / 'src/payload.c').read_text()
    # Public functions remain byte-for-byte; only include/environment glue and
    # excluded unrelated entry helpers are replaced by our named fake backend.
    translation = (HERE / 'mock_prefix.c').read_text() + '\n' + \
        between(source, '// Kernels must be 2MB aligned', 'static void finalize_uncompression(') + \
        between(source, 'static void finalize_uncompression(', '#define MAX_VAR_NAME 64') + \
        between(source, '#define MAX_VAR_NAME 64', 'void do_enable_tso(void)') + \
        source_function(source, 'int payload_run(void)\n{') + \
        (HERE / 'mock_suffix.c').read_text()
    (args.output / 'public-payload-mock.c').write_text(
        '/* Authenticated Aura public parser fragments, MIT AND GPL-2.0-only;\n'
        ' * original surrounding iLinux mock, MIT. Private test translation. */\n' + translation)
    lib = args.source_tree / 'src/libfdt'
    sources = [lib / name for name in ('fdt.c','fdt_ro.c','fdt_rw.c','fdt_sw.c','fdt_wip.c',
                                       'fdt_empty_tree.c','fdt_strerror.c')]
    sources += [args.source_tree / 'src/tinf' / name for name in ('tinflate.c','tinfgzip.c','crc32.c')]
    sources.append(args.source_tree / 'src/stage1_proxy.c')
    command = ['cc','-std=gnu11','-D_GNU_SOURCE','-DSTAGE1_PROXY_HOST_TEST=1','-O2','-Wall','-Wextra','-Werror',
               '-Wno-unused-parameter','-Wno-unused-function','-I',str(args.source_tree / 'src'),
               '-I',str(lib),str(args.output / 'public-payload-mock.c'),
               *map(str,sources),'-o',str(args.output / 'public-payload-mock')]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (args.output / 'compile.log').write_text(compiled.stdout + compiled.stderr)
    inline.require(compiled.returncode == 0, 'mock compilation failed; see compile.log')
    cases = []
    def run(name, data, profile='26.6.2', failure=0, result=0):
        path = args.output / (name + '.payload')
        path.write_bytes(data)
        process = subprocess.run([str(args.output / 'public-payload-mock'),str(path),str(args.image),
                                  str(args.dtb),str(args.initramfs),profile,str(failure)],
                                 capture_output=True,text=True,timeout=30)
        (args.output / (name + '.private.log')).write_text(process.stderr)
        inline.require(process.returncode == 0, 'mock process failed: ' + name)
        record = json.loads(process.stdout)
        inline.require(record['payload_result'] == result, 'unexpected parser outcome: ' + name)
        if result == 0:
            inline.require(record['boot_calls'] == 1 and record['prepare_calls'] == 1 and
                           record['selected_fdt_rank'] == 1 and record['initrd_in_heap'] and
                           record['kernel_in_heap'] and record['chosen_calls'] == 1 and
                           record['no_carrier_payload_action'] == 0,
                           'successful parse lost a required retained payload')
            inline.require(record['events'] == [1,2,3,4,5,6,7,8,9,10], 'unexpected preparation order')
        cases.append({'case':name,'status':'PASS','record':record})
    run('propertyless-dt-26_6_2', payload)
    run('propertyless-dt-other-profile', payload, profile='27.0')
    run('prepare-refusal', payload, failure=1, result=-1)
    run('boot-refusal', payload, failure=2, result=-1)
    run('mitigation-timeout', payload, failure=3, result=-1)
    damaged = bytearray(payload)
    damaged[positions['initrd_envelope_gzip_offset'] - 8] ^= 1  # Image gzip trailer CRC only.
    run('kernel-gzip-crc-refusal', bytes(damaged), result=-1)
    wrong = bytearray(payload)
    needle = b'apple,j716c\0'
    index = wrong.find(needle, 0, len(dtb))
    inline.require(index >= 0, 'fixture board compatible missing')
    wrong[index:index + len(needle)] = b'apple,j716x\0'
    run('wrong-board-dt-refusal', bytes(wrong), result=-1)
    raw_tag = inline.TAG + len(initrd).to_bytes(4,'little') + initrd
    start = positions['initrd_envelope_gzip_offset'];end = positions['config_offset']
    run('retained-inline-initrd-refusal', payload[:start] + raw_tag + payload[end:], result=-1)
    report = {'schema':'ilinux-direct31ai-public-parser-mock-v1','status':'PASS',
              'source_commit':pins['commit'],'case_count':len(cases),'cases':cases,
              'source_pins_sha256':inline.digest((HERE / 'source-pins.json').read_bytes()),
              'payload_sha256':inline.digest(payload),'Image_sha256':inline.digest(image),
              'dtb_sha256':inline.digest(dtb),'initramfs_sha256':inline.digest(initrd),
              'real_components':['payload scan/loaders/run sequence','tinf gzip/CRC','libfdt/profile ranking',
                                 'native-payload selection without proxy carrier'],
              'mocked_components':['firmware/ADT identity','heap backend','CPU setup','NVMe',
                                   'runtime DT fixups','physical window/copy','kernel entry'],
              'native_tested':False,'restart_ready':False}
    (args.output / 'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'PASS','cases':len(cases),'native_tested':False}))


if __name__ == '__main__':
    main()
