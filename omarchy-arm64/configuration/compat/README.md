# Omarchy compatibility fixes (not VM-specific)

## qt612-color-shadowing

**Symptom:** under Qt ≥ 6.12, the Omarchy 4.0.4 shell starts with a solid
black bar and no modules. Popups and notifications are unthemed, and the log
fills with `Cannot read property '…' of undefined` and
`Unable to assign [undefined] to QColor`.

**Cause (Confirmed, 2026-10-12):**

* QtQuick 6.12 exports a new QML type, `QtQuick/Color 6.12`.
* Inside any file that does an unversioned `import QtQuick`, that type
  shadows the shell's own `qs.Commons` singleton `Color`, even when
  `qs.Commons` is imported after QtQuick.
* So `Color.bar.text`, `Color.background` and the rest are undefined.

A minimal reproduction with Qt's `qml` tool:

* `import QtQuick` + `import Commons` gives `Color.background = undefined`.
* `import QtQuick 6.11` + `import Commons` gives `#101315`.

**Fix:**

* `ilinux-omarchy-qt612-fix` pins the shell's unversioned `import QtQuick`
  to `6.11`. That hides only the types Qt added in 6.12, which the shell
  doesn't use. It touched 102 files.
* The script is idempotent. It only acts when QtQuick exports `Color` *and*
  the shell defines a `Color` singleton, so it becomes a no-op once upstream
  renames or qualifies the singleton.
* `ilinux-omarchy-qt612-fix.hook` (→ `/etc/pacman.d/hooks/`) re-applies it
  after `omarchy` or `qt6-declarative` upgrades.
* Install the script to `/usr/local/bin/`, then run `omarchy-restart-shell`.

**Upstream:** this is an Omarchy bug, not specific to ARM or Apple. It is
worth reporting to basecamp/omarchy, with the two-line reproduction above.
