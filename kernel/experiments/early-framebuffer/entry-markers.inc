/* SPDX-License-Identifier: GPL-2.0-only */
/* Temporary RAM-boot diagnostic. Only x9-x14 and condition flags are clobbered. The controller
 * fills the zero descriptor from the validated prepared DT; zero is a no-op.
 * Use ONLY before MMU enable. x0-x3 (boot ABI), x19-x21 and LR are untouched.
 */
	.macro ilinux_entry_mark number
	adr_l	x9, ilinux_fb_descriptor
	ldr	x10, [x9]
	cbz	x10, .Lilinux_done\@
	ldr	x11, [x9, #8]
	// 64x32 white blocks at (16 + 80*number, 16).
	add	x10, x10, x11, lsl #4
	add	x10, x10, #(64 + 320 * \number)
	mov	x12, #32
	mov	w14, #-1
.Lilinux_row\@:
	mov	x9, x10
	mov	x13, #64
.Lilinux_pixel\@:
	str	w14, [x9], #4
	subs	x13, x13, #1
	b.ne	.Lilinux_pixel\@
	add	x10, x10, x11
	subs	x12, x12, #1
	b.ne	.Lilinux_row\@
	dsb	sy
.Lilinux_done\@:
	.endm
