/* SPDX-License-Identifier: GPL-2.0-only */
extern bool ilinux_probe_diag;
bool ilinux_probe_fb_mark(unsigned int lane, unsigned int value);
unsigned int ilinux_probe_fb_state(void);
static u32 fb_text_height;
#define ILINUX_STRIP_SCALE 4U
#define ILINUX_PANEL_ROWS 4U
#define ILINUX_PANEL_COLS 12U
static unsigned int fb_diag_state;
static unsigned int panel_values[8];

unsigned int ilinux_probe_fb_state(void)
{
	return READ_ONCE(fb_diag_state);
}

bool ilinux_probe_fb_mark(unsigned int lane, unsigned int value)
{
	static const char hex[] = "0123456789ABCDEF";
	static const char labels[] = "PSWHDBCI";
	static const u8 rows[] = { 0, 0, 1, 1, 2, 3, 3, 2 };
	static const u8 cols[] = { 0, 5, 0, 5, 0, 0, 5, 7 };
	static const u8 digits[] = { 2, 2, 2, 2, 4, 2, 4, 3 };
	u32 x, y, c, bytes, left, top;
	char text[6];

	if (!READ_ONCE(ilinux_probe_diag) || !fb_mapping || mapping_failed ||
	    !fb_font || lane >= 8 || value > ((lane == 4 || lane == 6) ? 65535 : lane == 7 ? 4095 : 255) ||
	    fb_width < ILINUX_PANEL_COLS * fb_font->width * ILINUX_STRIP_SCALE ||
	    fb_height < (ILINUX_PANEL_ROWS * ILINUX_STRIP_SCALE + 6) * fb_font->height)
		return false;
	WRITE_ONCE(panel_values[lane], value);
	bytes = DIV_ROUND_UP(fb_font->width, 8);
	/* Repaint saved lanes too: later console text can overwrite diagnostic RAM.
	 * This is a fixed, bounded panel; no printk, locks or timer dependency.
	 */
	for (unsigned int n = 0; n < 8; n++) {
		unsigned int saved = READ_ONCE(panel_values[n]);
		text[0] = labels[n]; text[1] = ':';
		for (c = 0; c < digits[n]; c++)
			text[2 + c] = hex[(saved >> ((digits[n] - 1 - c) * 4)) & 15];
		left = cols[n] * fb_font->width * ILINUX_STRIP_SCALE;
		top = fb_height - (ILINUX_PANEL_ROWS - rows[n]) * fb_font->height * ILINUX_STRIP_SCALE;
		for (y = 0; y < fb_font->height * ILINUX_STRIP_SCALE; y++) {
			u32 *row = fb_mapping + (u64)(top + y) * fb_stride;
			for (c = 0; c < 2U + digits[n]; c++) {
				const u8 *glyph = fb_font->data + (u8)text[c] * fb_font->height * bytes;
				for (x = 0; x < fb_font->width * ILINUX_STRIP_SCALE; x++)
					WRITE_ONCE(row[left + c * fb_font->width * ILINUX_STRIP_SCALE + x],
						(glyph[(y / ILINUX_STRIP_SCALE) * bytes + x / ILINUX_STRIP_SCALE / 8] &
						 (0x80 >> (x / ILINUX_STRIP_SCALE % 8))) ? U32_MAX : 0);
			}
		}
	}
	return true;
}
