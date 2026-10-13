"""Boundary checks: a malformed carrier must never broaden what gets copied."""
import unittest
from extract_kernel_payload import kernel_payload


def der(tag, value):
    return bytes((tag, len(value))) + value


def carrier(kind=b"krnl", payload=b"bvx2example"):
    im4p = der(0x30, der(0x16, b"IM4P") + der(0x16, kind) +
               der(0x16, b"test") + der(4, payload))
    return der(0x30, der(0x16, b"IMG4") + im4p + der(4, b"PRIVATE-DO-NOT-COPY"))


class Boundaries(unittest.TestCase):
    def test_only_payload(self):
        self.assertEqual(kernel_payload(carrier())[0], b"bvx2example")

    def test_reject_other_payload(self):
        with self.assertRaises(ValueError):
            kernel_payload(carrier(kind=b"sepi"))

    def test_reject_encrypted_or_unknown(self):
        with self.assertRaises(ValueError):
            kernel_payload(carrier(payload=b"opaque"))

    def test_all_truncations_fail(self):
        data = carrier()
        for i in range(len(data)):
            with self.subTest(i=i), self.assertRaises(ValueError):
                kernel_payload(data[:i])

    def test_indefinite_length_fails(self):
        with self.assertRaises(ValueError):
            kernel_payload(b"\x30\x80\x00\x00")


if __name__ == "__main__":
    unittest.main()
