/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after the existing framebuffer state. No raw addresses displayed. */
extern bool ilinux_probe_diag;
bool ilinux_probe_fb_mark(unsigned int lane, unsigned int value);
unsigned int ilinux_probe_fb_state(void);
static u32 fb_text_height;
#define ILINUX_STRIP_SCALE 4U
static unsigned int fb_diag_state;

unsigned int ilinux_probe_fb_state(void)
{
	return READ_ONCE(fb_diag_state);
}

bool ilinux_probe_fb_mark(unsigned int lane, unsigned int value)
{
	static const char hex[] = "0123456789ABCDEF";
	static const char labels[] = "PSWH";
	u32 x, y, c, bytes, left;
	char text[4];

	/* Permanent map only. Never call early_ioremap from scheduler/IRQ paths. */
	if (!READ_ONCE(ilinux_probe_diag) || !fb_mapping || mapping_failed ||
	    !fb_font || lane >= 4 || value > 255 ||
	    fb_width < 20 * fb_font->width * ILINUX_STRIP_SCALE ||
	    fb_height < (ILINUX_STRIP_SCALE + 2) * fb_font->height)
		return false;
	text[0] = labels[lane]; text[1] = ':';
	text[2] = hex[value >> 4]; text[3] = hex[value & 15];
	left = lane * 5 * fb_font->width * ILINUX_STRIP_SCALE;
	bytes = DIV_ROUND_UP(fb_font->width, 8);
	for (y = 0; y < fb_font->height * ILINUX_STRIP_SCALE; y++) {
		u32 *row = fb_mapping + (u64)(fb_height - fb_font->height * ILINUX_STRIP_SCALE + y) * fb_stride;
		for (c = 0; c < 4; c++) {
			const u8 *glyph = fb_font->data + (u8)text[c] * fb_font->height * bytes;
			for (x = 0; x < fb_font->width * ILINUX_STRIP_SCALE; x++)
				WRITE_ONCE(row[left + c * fb_font->width * ILINUX_STRIP_SCALE + x],
					(glyph[(y / ILINUX_STRIP_SCALE) * bytes + x / ILINUX_STRIP_SCALE / 8] &
					 (0x80 >> (x / ILINUX_STRIP_SCALE % 8))) ? U32_MAX : 0);
		}
	}
	return true;
}
