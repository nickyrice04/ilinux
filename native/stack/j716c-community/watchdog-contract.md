# Physical watchdog and finite host lease: exact J716c source contract

This is source qualification and an offline protocol component for 31AY.
It does not deploy, arm, ping, stop or test any physical watchdog. The
publisher's host guardian is not supplied, and its private transport or
thresholds have not been inferred.

## Confirmed interfaces and limits

The exact integration kernel uses the ordinary **Apple SoC Watchdog**
driver and Linux watchdog UAPI. J716c's DT selects the primary watchdog
with the existing t8103 compatibility fallback and a 24 MHz reference clock.
The driver controls WD1, which performs a normal machine reset; WD0's
Recovery reset mechanism is a different channel and is not the userspace
interface being proposed. No special SMC/PMGR userspace protocol is required
to operate this kernel's WD1. The driver defaults to 30 seconds; its
32-bit counter at this clock permits a maximum hardware interval of
178 seconds. It supports timeout selection, keepalive, time-left reporting
and magic close. [Exact driver](https://github.com/cameroncooper/linux/blob/a59e709c737777495c84541c6afb6c862bb79227/drivers/watchdog/apple_wdt.c),
[exact DT](https://github.com/cameroncooper/linux/blob/a59e709c737777495c84541c6afb6c862bb79227/arch/arm64/boot/dts/apple/t6050-die0.dtsi#L40),
[clock](https://github.com/cameroncooper/linux/blob/a59e709c737777495c84541c6afb6c862bb79227/arch/arm64/boot/dts/apple/t6050-base.dtsi#L265).

Linux's standard API is enough **after a sole userspace owner has opened
the correct watchdog**. A future adapter should verify identity/options,
request and read back a capped timeout, maintain exclusive ownership,
and issue keepalives only for fresh accepted leases. It must never send the
magic close byte, disable the watchdog, fall back to a software watchdog,
or silently select another device. These are future implementation
requirements, not actions performed here.
[Kernel watchdog API](https://github.com/cameroncooper/linux/blob/a59e709c737777495c84541c6afb6c862bb79227/Documentation/watchdog/watchdog-api.rst).

There are two important standard-core behaviors:

- The matched config has built-in Apple watchdog support,
  `CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y`,
  `CONFIG_WATCHDOG_OPEN_TIMEOUT=0`, and NOWAYOUT and WATCHDOG_SYSFS unset.
  The zero open timeout permits indefinite kernel renewal of an inherited
  running watchdog before userspace opens it. An inherited WD1 alone does
  not establish a finite whole-boot deadline.
- Closing an active magic-close watchdog without its magic byte issues
  **one final keepalive** and leaves it running. A finite bound must account
  for that release ping. The watchdog core can also renew longer virtual
  timeouts; a small verified interval below the hardware maximum avoids
  that renewal path after userspace activation.

Keep the published config unchanged for exact reproduction. A separately
reviewed bounded runtime profile could supply a finite
`watchdog.open_timeout` parameter and start its sole owner early. The value
and actual boot-to-open timing must be qualified. Do not claim that the
published configuration already enforces this profile.
[Config](https://github.com/cameroncooper/linux/blob/5e11068a1c6d8fccb155bc6e0159cc16107e53ec/Documentation/arch/arm64/apple-j716c-bringup/kernel.config),
[worker and open deadline](https://github.com/cameroncooper/linux/blob/a59e709c737777495c84541c6afb6c862bb79227/drivers/watchdog/watchdog_dev.c#L63),
[unexpected-close behavior](https://github.com/cameroncooper/linux/blob/a59e709c737777495c84541c6afb6c862bb79227/drivers/watchdog/watchdog_dev.c#L937).

## Aura supplies retention, not automatic T6050 arming

Exact Aura9da has a board-scoped `wdt_stage2_keep_j716c()` path. With
`j716c.wdt=keep`, it requires the exact T6050/J716c/Mac17,6 target,
watchdog-v3 layout, expected register range, an already enabled WD1
and a countdown that has not expired. It reads and preserves that
countdown without touching the timer. Bad inherited state is refused.
Without this explicit path, Stage2 disables the watchdog during startup.
[Exact retention implementation](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/wdt.c#L23),
[Stage2 integration](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/main.c#L370).

Its generic arming helper expects watchdog-v2 and its exported timed-arm
interface admits T8140/T6040, not T6050. The Stage1 boot/trial watchdog
mechanisms therefore cannot simply be assumed to arm J716c. The comment
describes a host-prearmed RAM chainload, but it does not publish the
host's exact arming/renewal/transport procedure. No new MMIO writer is
justified merely by copying register offsets.
[Arming restrictions](https://github.com/cameroncooper/aura/blob/9da61857f9d9262bd64c023fbc1b18315b12d0af/src/wdt.c#L123).

The missing pre-Linux piece is now concrete: qualify who arms WD1,
when the armed interval starts, how exact Stage1/Stage2 preserve or replace
it, and what happens if no Linux watchdog owner appears. The userspace
lease component below does not fill that gap. It also does not cover an
early hang before the inherited countdown has been safely established.

## Original offline lease component

`lease.py` is an original pure decision adapter. It has no device, ioctl,
socket, SSH, subprocess or writer implementation. It treats a caller's
monotonic arm timestamp as an already-qualified reference point; it does
not itself establish that hardware was armed or transport authenticated.

Its fixed protocol accepts one bounded ASCII frame with a contiguous
sequence number per renewal. A duplicate, gap, malformed frame, clock
regression, burst, lease expiry or hard deadline is terminal. It never
extends a deadline from a host-provided timestamp and has no environment
override or restart path.

The proposed finite budget is deliberately conservative:

| Quantity | Proposed offline contract |
| --- | --- |
| Verified physical interval | At most 10 seconds |
| Fresh-host lease interval | 3 seconds |
| Minimum accepted renewal spacing | 500 milliseconds |
| Last eligible keepalive | Strictly before 70 seconds from arm |
| Additional release allowance | One final kernel release ping |
| Conditional physical reset bound | Before 90 seconds from arm |

The extra **two** physical intervals reserve both the final hardware
countdown and the watchdog core's possible close ping. This is a model
bound under a correctly operating, verified 10-second physical watchdog,
one owner/one close, no automatic reopen or other renewal source, and
qualified timing. It is not a hard real-time hardware measurement.
Transport failure must stop eligibility, not launch a second controller.
Actual hardware owner code, timer/timeout readback, service integration,
pre-Linux coverage and fault-injection validation remain unimplemented.

## Reuse and handoff sequence

The RAM root already supplies systemd, key-authenticated SSH and native
collection tools. The publisher exercised N1/key SSH; its USB topic still
has no proven serial/SSH channel. A reviewed SSH renewal transport is a
reasonable implementation option, not a claim about the publisher's
private guardian. Do not depend on the old USB path.

The existing M1 `attempt31n-supervisor.py` is useful for one-shot reservation,
a local child deadline, evidence preservation and no automatic retry.
Its own header explicitly requires a human return timer. Killing the M1
child does **not** reset a frozen M5, so it cannot substitute for physical
WD1. The existing RAM-root initialization/desktop units likewise do not
establish a standard watchdog owner.

Before native deployment:

1. Complete the exact-board firmware, Stage1 and rescue review.
2. Qualify pre-Linux WD1 arming/retention and a finite Linux pre-open
   period without changing the published reproduction config.
3. Add and test a sole Linux standard-watchdog owner with fixed identity,
   capped/read-back timeout, the reviewed lease protocol and no disarm,
   restart, alternate-device or concurrent PID1 watchdog ownership.
4. Bind M1's authenticated renewal stream to that one session and stop
   renewal on failed health observations, disconnect, lease expiry or
   the independent hard deadline. Keep the human/camera record.
5. Verify actual expiry on host loss and Linux-owner loss before treating
   the mechanism as recovery protection for a graphics/CPU workload.

A WD1 reset selects the configured boot target. It does **not** select
Macintosh HD for us. The approved return/default sequence must prevent
automatic re-entry into the experimental Lab, independently of byte
restoration and the physical watchdog. Preserve the manual power/Options/
Original route. Nothing in this record authorizes a new boot or default
selection.
