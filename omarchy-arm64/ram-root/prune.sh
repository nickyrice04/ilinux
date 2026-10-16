#!/bin/bash
# prune.sh ROOT: delete what the RAM root never reads (documentation, translations, headers,
# static libraries, locale sources, pacman's database, Hyprland's default wallpapers, Mesa's
# TensorFlow Lite delegate, the GCC sanitizer, Fortran and Objective-C runtimes) and keep
# only the four JetBrainsMono Nerd Font faces Omarchy's configuration uses. Python and Perl
# are dependencies of gpsd's tools and glibmm's code generator only; nothing here runs them.
# Job 039 fails the build if a remaining binary loses a shared library it had before.
set -euo pipefail
R=${1:?usage: prune.sh ROOT}
before=$(du -sm --apparent-size "$R" | cut -f1)
rm -rf "$R"/usr/share/{doc,man,info,gtk-doc,help,devhelp,gir-1.0,vala,aclocal,i18n} \
       "$R"/usr/include "$R"/usr/lib/pkgconfig "$R"/usr/share/pkgconfig "$R"/usr/lib/cmake \
       "$R"/var/lib/pacman "$R"/var/cache/pacman "$R"/usr/share/hypr/*.png \
       "$R"/usr/lib/libteflon.so "$R"/usr/lib/lib{asan,hwasan,lsan,tsan,ubsan,gfortran,objc}.so* \
       "$R"/usr/lib/python3.* "$R"/usr/lib/libpython3* "$R"/usr/bin/{python,pydoc,idle}* \
       "$R"/usr/lib/perl5 "$R"/usr/share/perl5 "$R"/usr/bin/{core,site,vendor}_perl "$R"/usr/bin/perl*
find "$R"/usr/share/locale -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
find "$R"/usr/lib -name '*.a' -type f -delete
find "$R"/usr/share/fonts/TTF -name 'JetBrainsMono*' \
     ! -name 'JetBrainsMonoNerdFont-Regular.ttf' ! -name 'JetBrainsMonoNerdFont-Bold.ttf' \
     ! -name 'JetBrainsMonoNerdFont-Italic.ttf' ! -name 'JetBrainsMonoNerdFont-BoldItalic.ttf' \
     -type f -delete
after=$(du -sm --apparent-size "$R" | cut -f1)
echo "prune: ${before} MiB -> ${after} MiB"
