#!/bin/sh
# Job 017: Linux guest uses the Mac's GPU through ggml RPC.
#   guest llama.cpp --rpc 127.0.0.1:50052 -> socat -> vsock CID 2 port 5052
#   -> vzrun bridge -> host ggml-rpc-server (Metal, bound to 127.0.0.1)
set -x
OUT=/mnt/job/out
uname -r; systemctl is-active ufw NetworkManager; timeout 8 getent hosts arm-mirror.omarchy.org || echo DNS-FAIL
pacman -S --needed --noconfirm socat cmake ninja git > /dev/null 2>&1
mkdir -p /mnt/models && mount -t virtiofs models /mnt/models || exit 1
cd /root/llama.cpp || exit 1
git log -1 --format=%h > $OUT/llamacpp-commit.txt
CC=clang CXX=clang++ cmake -S . -B build-rpc -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_RPC=ON \
  -DGGML_NATIVE=OFF -DGGML_CPU_ARM_ARCH=armv8.6-a+dotprod+i8mm+sme -DGGML_BLAS=OFF \
  -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_TESTS=OFF > $OUT/cmake.log 2>&1 || exit 1
cmake --build build-rpc --target llama-bench -j 18 > $OUT/build.log 2>&1 || { tail -20 $OUT/build.log; exit 1; }
socat TCP-LISTEN:50052,bind=127.0.0.1,fork,reuseaddr,nodelay VSOCK-CONNECT:2:5052 &
sleep 1
B=build-rpc/bin/llama-bench
$B --rpc 127.0.0.1:50052 --list-devices > $OUT/devices.txt 2>&1
for q in q4_0; do
  $B -m /mnt/models/synth-llama3-8b-$q.gguf --rpc 127.0.0.1:50052 -ngl 99 -p 512 -n 128 -r 3 -o jsonl \
    >> $OUT/llamacpp-rpc.jsonl 2>> $OUT/llamacpp-rpc.log
done
