#!/bin/sh
set -eu
cd /mnt/lab
cc -O2 -std=c11 -Wall -Wextra -Werror /mnt/source/startup_layout.c /mnt/source/test_startup_layout.c -o startup-layout-test-linux
./startup-layout-test-linux > evidence/startup-layout-linux.txt
python3 -I -m unittest discover -s /mnt/source -p 'test_*.py' > evidence/python-tests-linux.txt 2>&1
cc --version > evidence/linux-compiler.txt
printf '%s\n' 'cc -O2 -std=c11 -Wall -Wextra -Werror startup_layout.c test_startup_layout.c -o startup-layout-test-linux' > evidence/linux-compile-command.txt
