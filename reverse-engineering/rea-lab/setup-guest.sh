#!/bin/sh
set -eu
mkdir -p /mnt/lab/evidence /mnt/lab/apk-cache
if ! command -v javac >/dev/null; then
    apk --cache-dir /mnt/lab/apk-cache add openjdk21-jdk nodejs build-base linux-headers zlib-dev bash unzip python3 procps
    tar -czf /mnt/lab/tool-root.tar.gz -C / bin sbin usr lib etc/apk
fi
apk --cache-dir /mnt/lab/apk-cache add procps
apk info -v > /mnt/lab/evidence/packages.txt
uname -srvmo > /mnt/lab/evidence/guest.txt
java -version 2>> /mnt/lab/evidence/guest.txt
javac -version >> /mnt/lab/evidence/guest.txt
node --version >> /mnt/lab/evidence/guest.txt
g++ --version >> /mnt/lab/evidence/guest.txt
cd /mnt/lab
if [ ! -d ghidra_12.1.4_PUBLIC ]; then
    echo 'ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db  downloads/ghidra_12.1.4_PUBLIC_20260921.zip' | sha256sum -c -
    unzip -q downloads/ghidra_12.1.4_PUBLIC_20260921.zip
fi
export GHIDRA_INSTALL_DIR=/mnt/lab/ghidra_12.1.4_PUBLIC
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk
ln -sfn /mnt/rea /mnt/node_modules
if [ ! -x "$GHIDRA_INSTALL_DIR/Ghidra/Features/Decompiler/os/linux_arm_64/decompile" ]; then
    cd "$GHIDRA_INSTALL_DIR/Ghidra/Features/Decompiler/src/decompile/cpp"
    # The bundled Makefile defaults non-x86 Linux to -m32: explicitly override.
    make -j2 ARCH_TYPE= OSDIR=linux_arm_64 ghidra_opt > /mnt/lab/evidence/decompiler-build.log 2>&1
    mkdir -p ../../../os/linux_arm_64
    cp ghidra_opt ../../../os/linux_arm_64/decompile
fi
cat > /usr/local/bin/rea <<'EOF'
#!/bin/sh
export GHIDRA_INSTALL_DIR=/mnt/lab/ghidra_12.1.4_PUBLIC
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk
exec node /mnt/rea/rea-agents/scripts/rea.mjs "$@"
EOF
chmod +x /usr/local/bin/rea
# Audit-wide doctor also reports optional providers and Alpine distro support.
# Retain its status; actual native operation is verified by the smoke test.
if rea doctor --format json > /mnt/lab/evidence/rea-doctor.json 2>&1; then
    echo 'REA audit-wide doctor passed'
else
    echo 'REA audit-wide doctor has limitations; inspect evidence/rea-doctor.json'
fi
