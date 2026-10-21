#!/bin/bash
set -euo pipefail
I=/mnt/ilinux O=/mnt/job/out W=/run/smp31d
mkdir -p "$I" /mnt/m1n1-source "$O" "$W"
mountpoint -q "$I" || mount -t virtiofs ilinux "$I"
mountpoint -q /mnt/m1n1-source || mount -t virtiofs m1n1-source /mnt/m1n1-source
exec > "$O/validation.log" 2>&1
python3 -I "$I/kernel/experiments/smp31/audit_console31d.py" --image "$O/boot021.bin" --source /mnt/m1n1-source
python3 -I "$I/native/boot/test_smp31d.py" --real-parser /mnt/m1n1-source/proxyclient
python3 -I "$I/tools/m1n1-client/test_attempt31d_supervise.py"
python3 -I "$I/kernel/experiments/smp31/test_client31d_vm.py" /mnt/m1n1-source/proxyclient
python3 -I - "$I" "$W" <<'PY'
import hashlib,importlib.util,re,sys
from pathlib import Path
root=Path(sys.argv[1]);work=Path(sys.argv[2]);source=Path('/mnt/m1n1-source/src')
spec=importlib.util.spec_from_file_location('audit',root/'kernel/experiments/smp31/audit_console31d.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
for file,names,output,variable in [('uart.c',('uart_putbyte','uart_write'),'uart31d.inc','serial_base'),
 ('dockchannel_uart.c',('dockchannel_uart_putbyte','dockchannel_uart_write'),'dock31d.inc','dock_base'),
 ('iodev.c',('_iodev_console_write_helper',),'console31d.inc',None)]:
 data=(source/file).read_bytes();assert hashlib.sha256(data).hexdigest()==audit.SOURCES[file]
 functions=[]
 for name in names:
  match=re.search(r'^(?:static )?void '+name+r'\([^;]*?\n\{.*?^}\n',data.decode(),re.M|re.S)
  assert match is not None
  functions.append(match.group().replace('uart_base',variable) if variable else match.group())
 (work/output).write_text('\n'.join(functions))
PY
cp "$I/kernel/experiments/smp31/test_console31d.c" "$W/"
gcc -O2 -std=c11 -Wall -Wextra -Werror -o "$W/console" "$W/test_console31d.c"
gcc -O1 -g -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -o "$W/console-san" "$W/test_console31d.c"
timeout -k 1 5 "$W/console"
timeout -k 1 5 "$W/console-san"
objdump -D -b binary -m aarch64 --start-address=0x347a0 --stop-address=0x347cc "$O/boot021.bin" > "$O/uart-disassembly.txt"
objdump -D -b binary -m aarch64 --start-address=0x1a360 --stop-address=0x1a3a0 "$O/boot021.bin" > "$O/dock-disassembly.txt"
python3 -I "$I/native/boot/test_smp31c.py" --real-parser /mnt/m1n1-source/proxyclient
python3 -I "$I/native/boot/test_smp31b.py"
python3 -I "$I/tools/m1n1-client/test_attempt31b_supervise.py"
python3 -I "$I/tools/m1n1-client/test_attempt31c_supervise.py"
python3 -I "$I/native/boot/test_smp31_census.py"
python3 -I "$I/kernel/experiments/smp31/test_audit_boot021.py"
python3 -I "$I/kernel/experiments/smp31/test_renderer.py"
{ gcc --version | head -1; python3 --version; uname -srm; } > "$O/toolchain.txt"
echo SMP31D-OFFLINE-PASS
