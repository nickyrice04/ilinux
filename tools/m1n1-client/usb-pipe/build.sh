#!/bin/sh
# Build usb-pipe on macOS from the SDK alone (Command Line Tools or Xcode; nothing to install):
# build/control/usb-pipe (ignored by Git). On Linux, the same relay with the test backends only:
#   cc -O2 -Wall -Wextra -pthread -o usb-pipe usb-pipe.c relay.c
set -eu
cd "$(dirname "$0")/../../.."
xcrun --show-sdk-path > /dev/null
mkdir -p build/control
S=tools/m1n1-client/usb-pipe
clang -O2 -Wall -Wextra -std=gnu11 -c -o build/control/usb-pipe-relay.o "$S/relay.c"
clang -O2 -Wall -Wextra -std=gnu11 -c -o build/control/usb-pipe-main.o "$S/usb-pipe.c"
clang -O2 -Wall -Wextra -fobjc-arc -c -o build/control/usb-pipe-iousbhost.o "$S/iousbhost.m"
clang -o build/control/usb-pipe build/control/usb-pipe-relay.o build/control/usb-pipe-main.o \
    build/control/usb-pipe-iousbhost.o -framework Foundation -framework IOKit -framework IOUSBHost
rm -f build/control/usb-pipe-*.o
shasum -a 256 build/control/usb-pipe
build/control/usb-pipe --version
