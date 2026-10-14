// SPDX-License-Identifier: GPL-2.0-only
/* Diagnostic-only flat-DT framebuffer console, before driver/IRQ probing.
 * No GPU/DCP commands: use only the bootloader's existing scanout allocation.
 */
#include <linux/console.h>
#include <linux/font.h>
#include <linux/init.h>
#include <linux/io.h>
#include <linux/libfdt.h>
#include <linux/of_fdt.h>
#include <linux/serial_core.h>
#include <asm/early_ioremap.h>

static u64 fb_base, fb_size;
static u32 fb_width, fb_height, fb_stride, cx, cy;
static const struct font_desc *fb_font;
static struct console *fb_console;
static void *fb_mapping;
static bool mapping_failed;

static const void * __init prop(const void *fdt, int node, const char *key, int size)
{
	int len;
	const void *p = fdt_getprop(fdt, node, key, &len);
	return p && len == size ? p : NULL;
}

static bool __init text_prop(const void *fdt, int node, const char *key, const char *text)
{
	const char *p = prop(fdt, node, key, strlen(text) + 1);
	return p && !strcmp(p, text);
}

static int __init read_framebuffer(const void *fdt)
{
	int chosen, node, found = -1, len;
	const fdt32_t *cells, *w, *h, *s;
	const char *status;
	u64 base, size;
	u32 width, height, stride;

	if (!fdt || fdt_node_check_compatible(fdt, 0, "apple,j716c"))
		return -ENODEV;
	chosen = fdt_path_offset(fdt, "/chosen");
	if (chosen < 0)
		return -ENODEV;
	cells = prop(fdt, chosen, "#address-cells", 4);
	if (!cells || fdt32_to_cpu(*cells) != 2)
		return -EINVAL;
	cells = prop(fdt, chosen, "#size-cells", 4);
	if (!cells || fdt32_to_cpu(*cells) != 2 || !prop(fdt, chosen, "ranges", 0))
		return -EINVAL;
	fdt_for_each_subnode(node, fdt, chosen) {
		if (fdt_node_check_compatible(fdt, node, "simple-framebuffer"))
			continue;
		status = fdt_getprop(fdt, node, "status", &len);
		if (status && !text_prop(fdt, node, "status", "okay") &&
		    !text_prop(fdt, node, "status", "ok"))
			continue;
		if (found >= 0)
			return -EINVAL;
		found = node;
	}
	if (found < 0)
		return -ENODEV;
	if (!text_prop(fdt, found, "format", "x8r8g8b8") &&
	    !text_prop(fdt, found, "format", "x2r10g10b10"))
		return -EINVAL;
	cells = prop(fdt, found, "reg", 16);
	w = prop(fdt, found, "width", 4);
	h = prop(fdt, found, "height", 4);
	s = prop(fdt, found, "stride", 4);
	if (!cells || !w || !h || !s)
		return -EINVAL;
	base = ((u64)fdt32_to_cpu(cells[0]) << 32) | fdt32_to_cpu(cells[1]);
	size = ((u64)fdt32_to_cpu(cells[2]) << 32) | fdt32_to_cpu(cells[3]);
	width = fdt32_to_cpu(*w); height = fdt32_to_cpu(*h); stride = fdt32_to_cpu(*s);
	/* Bound early mapping sizes and all renderer arithmetic; fail closed. */
	if (!base || (base & 3) || width < 320 || width > 8192 ||
	    height < 200 || height > 8192 || (stride & 3) ||
	    stride < width * 4 || stride > 32768 ||
	    size < (u64)stride * height || size > 256ULL * 1024 * 1024 ||
	    base > U64_MAX - size)
		return -EINVAL;
	fb_base = base; fb_size = (u64)stride * height;
	fb_width = width; fb_height = height; fb_stride = stride;
	return 0;
}

static __ref void *map_row(u32 y)
{
	if (mapping_failed)
		return NULL;
	if (fb_mapping)
		return fb_mapping + (u64)y * fb_stride;
	return early_memremap_prot(fb_base + (u64)y * fb_stride, fb_stride,
				  pgprot_val(pgprot_writecombine(PAGE_KERNEL)));
}

static __ref void unmap_row(void *p)
{
	if (!fb_mapping)
		early_memunmap(p, fb_stride);
}

static void clear_line(void)
{
	u32 y;
	for (y = 0; y < fb_font->height * 2; y++) {
		void *p = map_row(cy + y);
		if (!p)
			return;
		memset(p, 0, fb_stride);
		unmap_row(p);
	}
}

static void fb_write(struct console *con, const char *text, unsigned int count)
{
	u32 y, x, bytes = DIV_ROUND_UP(fb_font->width, 8);
	while (count--) {
		unsigned char c = *text++;
		if (c == '\r') { cx = 0; continue; }
		if (c != '\n') {
			const u8 *glyph = fb_font->data + c * fb_font->height * bytes;
			for (y = 0; y < fb_font->height * 2; y++) {
				u32 *row = map_row(cy + y);
				if (!row)
					return;
				for (x = 0; x < fb_font->width * 2; x++) {
					u32 bit = x / 2;
					/* All RGB bits white works for both 8- and 10-bit formats. */
					row[cx + x] = (glyph[(y / 2) * bytes + bit / 8] &
						(0x80 >> (bit % 8))) ? U32_MAX : 0;
				}
				unmap_row(row);
			}
			cx += fb_font->width * 2;
		}
		if (c == '\n' || cx + fb_font->width * 2 > fb_width) {
			cx = 0;
			cy += fb_font->height * 2;
			/* Circular rows avoid costly full-frame scrolling on every printk.
			 * The newest row is followed by a cleared row; film the transition.
			 */
			if (cy + fb_font->height * 2 > fb_height)
				cy = 0;
			clear_line();
		}
	}
}

static int __init fb_remap(void)
{
	if (!fb_console || !console_is_registered(fb_console))
		return 0;
	fb_mapping = memremap(fb_base, fb_size, MEMREMAP_WC);
	/* early_ioremap is no longer safe after initcalls begin. */
	mapping_failed = !fb_mapping;
	return fb_mapping ? 0 : -ENOMEM;
}
early_initcall(fb_remap);

static int __init fb_unmap(void)
{
	if (fb_mapping && !console_is_registered(fb_console)) {
		memunmap(fb_mapping);
		fb_mapping = NULL;
		mapping_failed = true;
	}
	return 0;
}
late_initcall(fb_unmap);

static int __init fb_setup(struct earlycon_device *dev, const char *opt)
{
	int err;
	if (opt && *opt)
		return -EINVAL;
	err = read_framebuffer(initial_boot_params);
	if (err)
		return err;
	fb_font = get_default_font(fb_width, fb_height, NULL, NULL);
	if (!fb_font || !fb_font->width || !fb_font->height ||
	    fb_font->width > 32 || fb_font->height > 64 ||
	    fb_font->height * 6 > fb_height)
		return -ENODEV;
	/* Keep top-left entry blocks intact until the first full text wrap. */
	cx = 0; cy = fb_font->height * 4;
	clear_line();
	fb_console = dev->con;
	dev->con->write = fb_write;
	return 0;
}
EARLYCON_DECLARE(ilinuxfb, fb_setup);
