/* SPDX-License-Identifier: GPL-2.0-only */
	.macro adr_l reg, symbol
	adrp \reg, \symbol
	add \reg, \reg, :lo12:\symbol
	.endm
#include "entry-markers.inc"
	.data
	.balign 8
	.global ilinux_fb_descriptor
ilinux_fb_descriptor:
	.quad 0, 0
	.text
	.macro probe number
	.global probe\number
	.type probe\number, %function
probe\number:
	ilinux_entry_mark \number
	eor x0, x0, x1
	eor x0, x0, x2
	eor x0, x0, x3
	ret
	.size probe\number, .-probe\number
	.endm
	probe 0
	probe 1
	probe 2
	.section .note.GNU-stack,"",%progbits
