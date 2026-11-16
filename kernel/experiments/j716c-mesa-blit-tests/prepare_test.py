#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Produce a separately identified test-only derivative; never change a driver."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
TEST='src/gallium/drivers/asahi/tests/test-agx-g17p-blit.c'
DRIVER='src/gallium/drivers/asahi/agx_pipe.c'
PINS={TEST:'ec72462fd0836429d213b0be193f15a28cc798abc353a53cfcdfbdf1f84132ed',
      DRIVER:'157d26f5512f887e5ed27fb4f2aa266c2f133c0d0ef5fd77ee8ecdece1444b9b'}
OLD='''   /* Preserve the public accelerated transfer policy. This shim checks
    * encoding, while BGRA/RGBA pixel conversion needs a hardware check. */
   if (screen->caps.texture_transfer_modes != PIPE_TEXTURE_TRANSFER_BLIT) {
      fprintf(stderr, "Accelerated texture transfers were disabled\\n");
      status = 1;
   }
'''
NEW='''   /* Match the production policy: AGX2 accelerates transfers; AGX3 uses
    * CPU conversion until its GPU BGRA/RGBA path is hardware-grounded.
    * This must not advertise BLIT on AGX3 merely to make this test pass. */
   const unsigned expected_transfer_modes = agx2 ? PIPE_TEXTURE_TRANSFER_BLIT
                                                : PIPE_TEXTURE_TRANSFER_DEFAULT;
   if (screen->caps.texture_transfer_modes != expected_transfer_modes) {
      fprintf(stderr, "Generation-specific texture transfer policy changed\\n");
      status = 1;
   }
'''


def derive(source_root):
    raw={}
    for name,pin in PINS.items():
        path=Path(source_root)/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size>2*1024**2:
            raise ValueError('PINNED_SOURCE_REQUIRED')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=pin:raise ValueError('PINNED_SOURCE_CHANGED')
        raw[name]=data
    source=raw[TEST].decode()
    replacements=[
       ('#include "util/format/u_formats.h"\n', '#include "util/format/u_formats.h"\n#include "util/format/u_format.h"\n'),
       ('static struct pipe_resource *\nmake_buffer(', (HERE/'cpu_roundtrip.inc').read_text()+'static struct pipe_resource *\nmake_buffer('),
       ('   if (!check_g17p_sampler_bias_record())\n', '   if (!check_cpu_transfer_roundtrip(pctx))\n      return 1;\n\n   if (!check_g17p_sampler_bias_record())\n'),
       (OLD,NEW),
    ]
    for before,after in replacements:
        if source.count(before)!=1:raise ValueError('EXACT_TEST_TRANSFORM_REQUIRED')
        source=source.replace(before,after,1)
    result=source.encode()
    return raw[TEST],result,raw[DRIVER]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    original,result,driver=derive(args.source_root)
    output=args.output.absolute()
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError('FRESH_OUTPUT_REQUIRED')
    if args.source_root.resolve() in output.parents:raise ValueError('SEPARATE_OUTPUT_REQUIRED')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as target:target.write(result)
    print(json.dumps({'schema':'ilinux-j716c-mesa-blit-test-derivative-v1',
        'original_test_sha256':hashlib.sha256(original).hexdigest(),
        'derivative_test_sha256':hashlib.sha256(result).hexdigest(),
        'unchanged_driver_sha256':hashlib.sha256(driver).hexdigest(),
        'test_only':True,'shipping_driver_changed':False,'baseline_result_unchanged':True,
        'native_gpu_tested':False,'third_party_execution':False},sort_keys=True))


if __name__=='__main__':main()
