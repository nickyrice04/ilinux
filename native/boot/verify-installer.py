#!/usr/bin/env python3
"""Read-only verification of the downloaded 26.6.2 Apple installer.

Does not launch installer code, extract files, mount images, or change policy.
The catalog is data fetched separately from Apple's HTTPS catalog endpoint.
This deliberately does not suppress the outer app's resource-rule error.
"""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import plistlib
import stat
import struct
import subprocess
import xml.etree.ElementTree as ET
import zlib

APP = Path('/Applications/Install macOS Tahoe.app')
PRODUCT = '140-93587'
SMALL_LIMIT = 128 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inflate(data, limit):
    dec = zlib.decompressobj()
    out = dec.decompress(data, limit + 1)
    require(len(out) <= limit and dec.eof and not dec.unused_data,
            'Invalid or excessive zlib stream')
    return out


def pbzx(data):
    require(data[:4] == b'pbzx' and len(data) >= 12, 'Invalid pbzx header')
    flags = struct.unpack('>Q', data[4:12])[0]
    pos, out = 12, bytearray()
    while flags & (1 << 24):
        require(pos + 16 <= len(data), 'Truncated pbzx chunk header')
        flags, length = struct.unpack('>QQ', data[pos:pos + 16])
        pos += 16
        require(0 < length <= SMALL_LIMIT and pos + length <= len(data),
                'Invalid pbzx chunk length')
        chunk = data[pos:pos + length]
        pos += length
        if chunk.startswith(b'\xfd7zXZ\x00'):
            dec = lzma.LZMADecompressor(memlimit=SMALL_LIMIT)
            chunk = dec.decompress(chunk, max_length=(1 << 24) + 1)
            require(dec.eof and not dec.unused_data, 'Incomplete XZ chunk')
        require(len(chunk) <= 1 << 24, 'Excessive pbzx output chunk')
        out.extend(chunk)
        require(len(out) <= SMALL_LIMIT, 'Excessive pbzx output')
    require(pos == len(data), 'Trailing pbzx data')
    return bytes(out)


def cpio_entries(data):
    """Parse the old ASCII CPIO format used by this Apple package."""
    pos, seen = 0, set()
    while True:
        head = data[pos:pos + 76]
        require(len(head) == 76 and head[:6] == b'070707', 'Invalid CPIO header')
        mode = int(head[18:24], 8)
        namesize, size = int(head[59:65], 8), int(head[65:76], 8)
        pos += 76
        require(0 < namesize < 8192 and size <= SMALL_LIMIT, 'Invalid CPIO size')
        require(pos + namesize + size <= len(data), 'Truncated CPIO entry')
        require(data[pos + namesize - 1] == 0, 'Unterminated CPIO name')
        name = data[pos:pos + namesize - 1].decode('utf-8')
        pos += namesize
        content = data[pos:pos + size]
        pos += size
        if name == 'TRAILER!!!':
            require(size == 0 and not any(data[pos:]), 'Invalid CPIO trailer')
            return
        require('\x00' not in name and not name.startswith('/') and
                '..' not in PurePosixPath(name).parts, 'Unsafe CPIO name')
        canonical = str(PurePosixPath(name))
        require(canonical not in seen, 'Duplicate CPIO entry')
        seen.add(canonical)
        yield name, mode, content


def compare_app(data, app):
    expected, counts = set(), {'file': 0, 'directory': 0, 'symlink': 0}
    prefix = './Applications/' + app.name + '/'
    parents = {'.', './Applications', './Applications/' + app.name}
    for name, mode, content in cpio_entries(data):
        if name in parents:
            require(stat.S_ISDIR(mode), 'Invalid app parent entry')
            continue
        require(name.startswith(prefix), 'Payload outside expected app')
        rel = name[len(prefix):]
        expected.add(rel)
        path = app / rel
        actual = path.lstat().st_mode
        if stat.S_ISREG(mode):
            require(stat.S_ISREG(actual) and path.read_bytes() == content,
                    'Installed file mismatch: ' + rel)
            counts['file'] += 1
        elif stat.S_ISDIR(mode):
            require(stat.S_ISDIR(actual), 'Directory mismatch: ' + rel)
            counts['directory'] += 1
        elif stat.S_ISLNK(mode):
            require(stat.S_ISLNK(actual) and os.readlink(path) == content.decode(),
                    'Symlink mismatch: ' + rel)
            counts['symlink'] += 1
        else:
            raise ValueError('Unsupported payload entry type')
    actual = set()
    for directory, dirs, files in os.walk(app, followlinks=False):
        actual.update(str((Path(directory) / n).relative_to(app)) for n in dirs + files)
    # The signed postinstall script links/copies the entire package here.
    added = {'Contents/SharedSupport', 'Contents/SharedSupport/SharedSupport.dmg'}
    require(not (actual - expected - added), 'Unexpected app entries')
    require(stat.S_ISDIR((app / 'Contents/SharedSupport').lstat().st_mode),
            'SharedSupport is not a directory')
    require(stat.S_ISREG((app / 'Contents/SharedSupport/SharedSupport.dmg').lstat().st_mode),
            'SharedSupport package is not a regular file')
    return counts


def checked_tool(argv, marker=None):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    output = result.stdout + result.stderr
    require(result.returncode == 0, 'Verification failed: ' + argv[0] + '\n' + output)
    if marker:
        require(marker in output, 'Unexpected verification result: ' + argv[0])


def verify(catalog_path):
    package = APP / 'Contents/SharedSupport/SharedSupport.dmg'
    catalog = plistlib.loads(catalog_path.read_bytes())
    product = catalog['Products'][PRODUCT]
    candidates = [p for p in product['Packages'] if p['URL'].endswith('/InstallAssistant.pkg')]
    require(len(candidates) == 1, 'Ambiguous catalog package')
    reference = candidates[0]
    require(reference['URL'].startswith('https://swcdn.apple.com/'), 'Non-Apple package URL')
    require(package.stat().st_size == reference['Size'], 'Catalog size mismatch')

    # These tools inspect the package; neither invokes Installer or its scripts.
    checked_tool(['/usr/sbin/pkgutil', '--check-signature', str(package)],
                 'Status: signed Apple Software')
    checked_tool(['/usr/sbin/spctl', '--assess', '--type', 'install', '--verbose=4', str(package)],
                 'source=Apple Installer')

    small, checked = {}, []
    with package.open('rb') as stream:
        header = stream.read(28)
        require(len(header) == 28, 'Truncated XAR header')
        magic, hsize, version, clen, ulen, algorithm = struct.unpack('>4sHHQQI', header)
        require((magic, hsize, version, algorithm) == (b'xar!', 28, 1, 1),
                'Unexpected XAR format')
        require(0 < clen < 1024 * 1024 and ulen < 8 * 1024 * 1024,
                'Excessive XAR table')
        compressed = stream.read(clen)
        digest = hashlib.sha1(compressed).digest()
        catalog_digest = reference['Digest']
        if isinstance(catalog_digest, str):
            catalog_digest = bytes.fromhex(catalog_digest)
        require(digest == catalog_digest, 'Catalog XAR-table digest mismatch')
        xml = inflate(compressed, ulen)
        require(len(xml) == ulen and b'<!DOCTYPE' not in xml, 'Invalid XAR table')
        toc = ET.fromstring(xml).find('toc')
        heap = hsize + clen
        require(toc is not None, 'Missing XAR table')
        checksum = toc.find('checksum')
        require(checksum is not None and checksum.get('style') == 'sha1' and
                checksum.findtext('size') == '20', 'Unexpected XAR checksum')
        stream.seek(heap + int(checksum.findtext('offset')))
        require(stream.read(20) == digest, 'Stored XAR checksum mismatch')
        entries = toc.findall('file')
        require(len(entries) == 5 and {n.findtext('name') for n in entries} ==
                {'Payload', 'Scripts', 'Bom', 'PackageInfo', 'SharedSupport.dmg'},
                'Unexpected package entries')
        for node in entries:
            name, data = node.findtext('name'), node.find('data')
            require(node.findtext('type') == 'file' and data is not None,
                    'Unsupported XAR entry')
            length, offset, size = (int(data.findtext(k)) for k in ['length', 'offset', 'size'])
            require(0 <= offset and 0 < length and heap + offset + length <= reference['Size'],
                    'XAR entry outside package')
            encoding = data.find('encoding').get('style')
            for tag in ['archived-checksum', 'extracted-checksum']:
                require(data.find(tag).get('style') == 'sha1', 'Unexpected checksum algorithm')
            if name != 'SharedSupport.dmg':
                require(length <= SMALL_LIMIT and size <= SMALL_LIMIT, 'Excessive small entry')
            else:
                require(encoding == 'application/octet-stream' and size == length,
                        'Unexpected image encoding')
            stream.seek(heap + offset)
            archived, saved, remaining = hashlib.sha1(), bytearray(), length
            while remaining:
                chunk = stream.read(min(8 * 1024 * 1024, remaining))
                require(bool(chunk), 'Truncated XAR data')
                archived.update(chunk)
                if name != 'SharedSupport.dmg':
                    saved.extend(chunk)
                remaining -= len(chunk)
            require(archived.hexdigest() == data.findtext('archived-checksum'),
                    'Signed archive checksum mismatch: ' + name)
            if name == 'SharedSupport.dmg':
                extracted_digest = archived.hexdigest()
            else:
                require(encoding in ['application/octet-stream', 'application/x-gzip'],
                        'Unsupported XAR encoding')
                decoded = inflate(saved, size) if encoding == 'application/x-gzip' else bytes(saved)
                require(len(decoded) == size, 'XAR extracted size mismatch')
                extracted_digest = hashlib.sha1(decoded).hexdigest()
                small[name] = decoded
            require(extracted_digest == data.findtext('extracted-checksum'),
                    'Signed extracted checksum mismatch: ' + name)
            checked.append(name)

    info = ET.fromstring(small['PackageInfo'])
    require(info.get('identifier') == 'com.apple.pkg.InstallAssistant.macOSTahoe' and
            info.get('version') == '25.6.83', 'Unexpected installer package identity')
    counts = compare_app(pbzx(small['Payload']), APP)
    for rel in ['Contents/MacOS/InstallAssistant', 'Contents/Resources/startosinstall',
                'Contents/Resources/createinstallmedia']:
        checked_tool(['/usr/bin/codesign', '--verify', '--strict', '--all-architectures',
                      '-R=anchor apple', str(APP / rel)])
    return {'status': 'PASS', 'product': PRODUCT, 'package_version': info.get('version'),
            'package_signature': 'signed Apple Software', 'gatekeeper_package': 'Apple Installer',
            'catalog_toc_sha1': digest.hex(), 'signed_entries_verified': checked,
            'app_matches_package': counts, 'strict_apple_executables': 3,
            'outer_app_resource_error_suppressed': False, 'installer_launched': False,
            'volumes_created': False, 'boot_settings_changed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.catalog), indent=2))
    except (ValueError, OSError, KeyError, ET.ParseError, subprocess.SubprocessError,
            lzma.LZMAError, zlib.error, struct.error) as error:
        raise SystemExit('FAIL: ' + str(error))
