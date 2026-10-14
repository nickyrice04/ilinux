/* SPDX-License-Identifier: GPL-2.0-only */
/* Independent diagnostic mapping; never infer geometry from raw addresses. */
static int __init fb_prepare(void)
{
	int err = read_framebuffer(initial_boot_params);

	if (err) {
		fb_diag_state = err == -ENODEV ? 1 : 2;
		return err;
	}
	fb_font = get_default_font(fb_width, fb_height, NULL, NULL);
	if (!fb_font || !fb_font->width || !fb_font->height ||
	    fb_font->width > 32 || fb_font->height > 64 ||
	    fb_font->height * 6 > fb_height) {
		fb_diag_state = 3;
		return -EINVAL;
	}
	if (ilinux_probe_diag && fb_width < 20 * fb_font->width * ILINUX_STRIP_SCALE) {
		fb_diag_state = 4;
		return -EINVAL;
	}
	return 0;
}

static int __init fb_remap(void)
{
	bool console_setup = !!fb_console;
	int err;

	/* Boot consoles can be absent or replaced before this initcall. The
	 * diagnostic strip has its own validated-DT initialization path.
	 */
	if (!ilinux_probe_diag && (!fb_console || !console_is_registered(fb_console)))
		return 0;
	err = fb_prepare();
	if (err) {
		if (ilinux_probe_diag)
			pr_info("ilinux-display: state=%u console_setup=%u\n", fb_diag_state, console_setup);
		return err == -ENODEV ? 0 : err;
	}
	fb_mapping = memremap(fb_base, fb_size, MEMREMAP_WC);
	mapping_failed = !fb_mapping;
	fb_diag_state = fb_mapping ? 6 : 5;
	if (fb_mapping && ilinux_probe_diag) {
		fb_text_height = fb_height - fb_font->height * ILINUX_STRIP_SCALE;
		cx = 0; cy = 0;
		for (unsigned int lane = 0; lane < 4; lane++)
			ilinux_probe_fb_mark(lane, 0);
	}
	if (ilinux_probe_diag)
		pr_info("ilinux-display: state=%u console_setup=%u\n", fb_diag_state, console_setup);
	return fb_mapping ? 0 : -ENOMEM;
}
