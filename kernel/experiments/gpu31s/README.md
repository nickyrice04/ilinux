# Typed GPU bootstrap message and injected transport

Original C11 implementation from the bounded behavior documented in
[`native31s-gpu-firmware.md`](../../../research/native31s-gpu-firmware.md),
with independent public m1n1 protocol corroboration. The exact retained-image
contract does not qualify every G17 firmware or a native G17C driver.

`gpu31s_encode_start` places an explicitly typed firmware address into the low
44 bits under the fixed bootstrap header. It rejects values that would truncate;
it does not translate CPU physical addresses or GPU virtual addresses. Zero and
unaligned values are format-valid, not evidence they are usable firmware memory.
`gpu31s_decode_start` requires the complete outgoing header and all non-address
bits, rather than recognizing only a partial discriminator.

`gpu31s_submit_start` validates the format and explicit service endpoint0x20,
then invokes the caller's word-by-value transport exactly once. It preserves the
opaque32-bit callback status, including errors, with no retry. `GPU31S_OK` means
the adapter called the transport, **not** that firmware accepted the word or booted.
A callback error does not prove the device never received the request. Format or
binding failure calls nothing and leaves output unchanged. No actual transport,
IO/MMIO implementation, device open, allocation or firmware image upload is
provided by this component. Offline tests use only a capture callback.

The caller must independently establish firmware identity/version, the endpoint
binding, lifetime/serialization and address conversion. Endpoint0x20 is a service
selector, not ADT GFX/GFX1 or a physical controller role. The neighboring0x21
endpoint is not an interchangeable target. No private boolean parameter or
borrowed-buffer lifetime assumption from the analyzed driver is copied into this
interface. Callbacks accept the message word by value.

`gpu31s_classify_received` preserves the complete incoming64-bit word and reports
only the observed six-bit discriminator and branch labels CASE_2, CASE_9 or OTHER.
This is **not a full message validation or acknowledgement decoder**. Public
m1n1 names a notification using full16-bit type0x42; its low-six-bit value is2.
Other words can also share discriminator2. No received case automatically changes
endpoint acceptance or native readiness. The earlier31R lifecycle remains a
separate evidence component; `initForOwner` itself binds software callbacks and
is not a hardware readiness handshake.

## Offline tests

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -O2 \
  kernel/experiments/gpu31s/bootstrap.c \
  kernel/experiments/gpu31s/test_bootstrap.c -o build/test-gpu31s
build/test-gpu31s
```

The14 groups cover literal boundary encodings, all20 non-address-bit mutations,
44-bit overflow refusal, null arguments,10,000 address round trips, all64 incoming
discriminators combined with1,024 high-bit patterns, full raw-word preservation,
explicit binding, exactly-one callback, opaque transport failures and unchanged
output on pre-submission refusal. No input pointers are serialized as firmware
addresses. Job079 runs Linux ASan/UBSan on the new component; actual results are
recorded in [`attempt31s/validation.json`](../../../native/boot/attempt31s/validation.json).

Further native work needs the G17C shared-data object layout, address ownership,
role mapping, queue initialization and qualified completion semantics. These
software tests cannot establish GPU rendering or performance improvement.
