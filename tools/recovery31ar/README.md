# 31AR complete transaction package

31AP's real paired-Recovery admission and owned read-only cleanup passed.
31AR prepares the next controlled transaction around the same matched Aura/Linux
candidate and exact boot021 rollback. It does not rebuild the image, restart
either machine, run the controller, or modify macOS during preparation.

The new native controller owns the complete admission, persistent private
comparison state, Preboot mount lifecycle, single attempted Apple commands,
readback and cleanup. The rendered Bash blocks verify/copy pinned files into a
new canonical scratch directory, invoke that controller once, validate its
finite result and remove only known scratch files after successful cleanup.
Every failure preserves scratch and transaction state. There is no retry,
automatic boot, force unmount, deletion of old state or Original policy writer.

The new fixed lab Data paths are Users/Shared/iLinuxBoot/31ar-kit for the
four-file kit and private/var/db/ilinux31ar-state for the new transaction. The
state parent is already root-owned; no existing owner or mode is changed.
All older kits, consumed markers and historical source inventories stay intact.
The independently accessible restore block needs only the exact helper, public
profile and boot021; the candidate file is not a restore prerequisite.

    python3 -I tools/recovery31ar/package.py --prepare \
      --kit build/ilinux-31ar-kit --output build/31ar-page
    python3 -I tools/recovery31ar/package.py \
      --page build/31ar-page/recovery.html --check-only

Default and --help are inert. --prepare checks exact binary delivery as data;
--prepare-source-page --output build/31ar-source-page can render the exact same
public page before private helper transfer and explicitly reports delivery as
unverified. Both outputs carry the same profile and paste bytes. Neither makes
the physical transaction ready or authorized. --check-only opens no socket.

--stage --kit ... is a separate future explicitly authorized four-file copy
to lab Data. It reuses the complete pinned original stager and its fresh
hardware/volume guards, exact file checks, private modes, exclusive creation and
durable copy with only the destination/state/profile/inventory selections
changed. The new state path's real parent, root owner, restrictive mode, absent
extended ACL and state absence are checked on both metadata observations.
It never runs the controller or touches boot policy or
Preboot. It refuses an existing new kit or transaction rather than overwriting.

--page ... without --check-only is a separate bounded page service. Its
default bind is loopback; an explicit RFC1918 IPv4 and lifetime up to 1800s are
supported for the later M1 handoff. It serves only reviewed bytes at /31ar,
without logs, file downloads, listing, uploads or a control API. Private URLs
remain outside Git. Nothing is served by import, default, preparation or checks.

The combined page has two clearly named text boxes. Each operation also has its
own one-box install.html or restore.html. Click within the appropriate box,
Command-A/Command-C, quit the browser, open Utilities Terminal and paste once.
No simultaneous browser/Terminal windows or clipboard exercise is required.

Keep recording off for all Recovery authentication and Apple commands. Start
the camera only for the separately authorized native window after install
postcondition and cleanup have both passed. The unchanged candidate's maximum
external observation window is 90 seconds, allowing its 60-second liveness
record. It is a RAM diagnostic, not the Omarchy desktop. Entry, distinct workers,
checksums, timers, liveness and later performance are separate claims.

Focused offline checks:

    python3 -I tools/recovery31ar/test_render.py
    python3 -I tools/recovery31ar/test_package.py

The package tests cover the new source/build/profile binding and adapter.
Original copy/HTTP transport behavior reuses its retained evidence rather than
repeating old suites. Offline success cannot prove actual APFS RW transitions,
Apple mutation behavior, authenticated native entry, SMP or performance.
