// SPDX-License-Identifier: GPL-2.0-only OR MIT
/*
 * test_driver.c - behaviour harness for the patched dockchannel-hid.c.
 *
 * The driver is #included unchanged and compiled against kshim.h; every kernel
 * service it calls is a small mock below, and the MTP firmware is a model that
 * speaks the framing the README documents (written independently of the
 * driver's helpers: its own checksum, its own message builder).
 *
 * What this proves: the new ring path, handshake order, descriptor/ready/ack
 * handling and the FIFO-era behaviour that must not change. What it does not
 * prove: that the real firmware behaves like the model (that is the hardware
 * experiment), or that the file builds in a real kernel (VM job).
 *
 * Concurrency: single-threaded. A waiting command lets the "world" advance
 * (firmware model, DockChannel IRQ thread, and packet work items of queues
 * that are not already executing, as separate kernel threads would).
 */
#include <stdarg.h>
#include <stdlib.h>

#include "dockchannel-hid.c"

/* ------------------------------------------------------------ accounting */
static int checks, failures, verbose;
#define CHECK(c) do { checks++; if (!(c)) { failures++; \
	fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)
#define CHECK_EQ(a, b) do { long long _a = (long long)(a), _b = (long long)(b); checks++; \
	if (_a != _b) { failures++; fprintf(stderr, "FAIL %s:%d: %s == %s (%lld != %lld)\n", \
	__FILE__, __LINE__, #a, #b, _a, _b); } } while (0)

static int nlog[8];
static char last_err[256];

void __kshim_log(int level, const struct device *d, const char *fmt, ...)
{
	char buf[512];
	va_list ap;

	va_start(ap, fmt);
	vsnprintf(buf, sizeof(buf), fmt, ap);
	va_end(ap);
	nlog[level & 7]++;
	if (level == KSHIM_ERR) {
		strncpy(last_err, buf, sizeof(last_err) - 1);
		last_err[sizeof(last_err) - 1] = 0;
	}
	if (verbose)
		fprintf(stderr, "  [%d] %s", level, buf);
}

int scnprintf(char *buf, size_t size, const char *fmt, ...)
{
	va_list ap;
	int n;

	va_start(ap, fmt);
	n = vsnprintf(buf, size, fmt, ap);
	va_end(ap);
	if (n < 0)
		return 0;
	return (size_t)n >= size ? (int)(size - 1) : n;
}

ssize_t strscpy(char *dst, const char *src, size_t n)
{
	size_t len = strnlen(src, n ? n - 1 : 0);

	if (!n)
		return -7;
	memcpy(dst, src, len);
	dst[len] = 0;
	return (ssize_t)len;
}

/* ------------------------------------------------------- memory tracking */
static void *tracked[8192];
static int ntracked;
static int kalloc_live;			/* kzalloc/kfree balance: catches leaked work items */

static void *track(void *p)
{
	CHECK(ntracked < 8192);
	tracked[ntracked++] = p;
	return p;
}

static void free_tracked(void)
{
	while (ntracked)
		free(tracked[--ntracked]);
}

void *devm_kzalloc(struct device *dev, size_t n, gfp_t g) { return track(calloc(1, n ? n : 1)); }
void *devm_kmalloc(struct device *dev, size_t n, gfp_t g) { return track(malloc(n ? n : 1)); }
char *devm_kstrdup(struct device *dev, const char *s, gfp_t g) { return track(strdup(s)); }
void *devm_kmemdup(struct device *dev, const void *src, size_t n, gfp_t g)
{
	void *p = malloc(n ? n : 1);

	memcpy(p, src, n);
	return track(p);
}
void *kzalloc(size_t n, gfp_t g) { kalloc_live++; return calloc(1, n ? n : 1); }
void kfree(const void *p) { if (p) { kalloc_live--; free((void *)p); } }

static dma_addr_t next_iova;
static unsigned dma_allocs;
void *dmam_alloc_coherent(struct device *dev, size_t size, dma_addr_t *h, gfp_t g)
{
	size_t sz = (size + 0x3fff) & ~(size_t)0x3fff;
	void *p = aligned_alloc(0x4000, sz);

	memset(p, 0, sz);
	*h = next_iova;
	next_iova += sz;
	dma_allocs++;
	return track(p);
}

/* ------------------------------------------------- device tree and platform */
static struct device_node n_dchid, n_mt, n_kbd, n_stm, n_helper;
static struct platform_device pdev, helper_pdev;
static struct device_link the_link;
static const void *match_data;

static void dt_reset(void)
{
	memset(&n_dchid, 0, sizeof(n_dchid)); memset(&n_mt, 0, sizeof(n_mt));
	memset(&n_kbd, 0, sizeof(n_kbd)); memset(&n_stm, 0, sizeof(n_stm));
	memset(&n_helper, 0, sizeof(n_helper)); memset(&pdev, 0, sizeof(pdev));
	memset(&helper_pdev, 0, sizeof(helper_pdev));
	n_dchid.name = "input"; n_mt.name = "multi-touch"; n_kbd.name = "keyboard"; n_stm.name = "stm";
	n_dchid.child = &n_mt; n_mt.sibling = &n_kbd; n_kbd.sibling = &n_stm;
	pdev.dev.of_node = &n_dchid;
	helper_pdev.dev.links.status = DL_DEV_DRIVER_BOUND;
}

struct device_link *device_link_add(struct device *c, struct device *s, u32 f)
{ the_link.consumer = c; the_link.supplier = s; return &the_link; }
void put_device(struct device *d) { }
struct platform_device *of_find_device_by_node(struct device_node *np) { return &helper_pdev; }
struct device_node *of_parse_phandle(const struct device_node *np, const char *n, int i) { return &n_helper; }
void of_node_put(struct device_node *np) { }
struct device_node *of_get_child_by_name(const struct device_node *np, const char *name)
{
	for (struct device_node *c = np->child; c; c = c->sibling)
		if (!strcmp(c->name, name))
			return c;
	return NULL;
}
int of_property_read_u32(const struct device_node *np, const char *n, u32 *o) { return -EINVAL; }
int of_property_read_string(const struct device_node *np, const char *n, const char **o)
{
	if (!strcmp(n, "firmware-name") && np->firmware_name) {
		*o = np->firmware_name;
		return 0;
	}
	return -EINVAL;
}
const void *device_get_match_data(const struct device *dev) { return match_data; }
int dma_set_mask_and_coherent(struct device *dev, u64 m) { return 0; }
const char *dev_name(const struct device *dev) { return "mtp-test"; }
int device_create_file(struct device *d, const struct device_attribute *a) { return 0; }
void device_remove_file(struct device *d, const struct device_attribute *a) { }
struct gpio_desc *fwnode_gpiod_get_index(struct fwnode_handle *f, const char *c, int i,
					 enum gpiod_flags fl, const char *l) { return NULL; }
struct gpio_desc *devm_gpiod_get_index(struct device *d, const char *c, unsigned i,
				       enum gpiod_flags f) { return NULL; }
void gpiod_put(struct gpio_desc *d) { }
void gpiod_set_value_cansleep(struct gpio_desc *d, int v) { }

/* firmware loader: the harness hands out a synthetic HIDF container, never Apple data */
static struct firmware the_fw;
static int fw_requests;
int request_firmware(const struct firmware **fw, const char *name, struct device *dev)
{
	fw_requests++;
	if (!the_fw.data)
		return -2;
	*fw = &the_fw;
	return 0;
}
void release_firmware(const struct firmware *fw) { }

/* ------------------------------------------------- sync, work, completions */
void mutex_init(struct mutex *m) { m->locked = 0; }
void mutex_lock(struct mutex *m) { CHECK(!m->locked); m->locked = 1; }
void mutex_unlock(struct mutex *m) { CHECK(m->locked); m->locked = 0; }
void init_completion(struct completion *c) { c->done = 0; }
void reinit_completion(struct completion *c) { c->done = 0; }
void complete(struct completion *c) { c->done = 1; }
void complete_all(struct completion *c) { c->done = 1; }
bool completion_done(struct completion *c) { return c->done; }
unsigned long msecs_to_jiffies(unsigned int ms) { return ms; }
void msleep(unsigned int ms) { }
int atomic_xchg(atomic_t *a, int v) { int o = a->counter; a->counter = v; return o; }

static bool world_step(void);
static int wait_timeouts;
unsigned long wait_for_completion_timeout(struct completion *c, unsigned long t)
{
	for (int i = 0; i < 256 && !c->done; i++)
		if (!world_step())
			break;
	if (!c->done)
		wait_timeouts++;
	return c->done ? 1 : 0;
}

static int wq_ids[64];
static int nwq;
struct workqueue_struct *alloc_ordered_workqueue(const char *f, unsigned fl, ...)
{ return (struct workqueue_struct *)&wq_ids[nwq++ & 63]; }
struct workqueue_struct *alloc_workqueue(const char *f, unsigned fl, int m, ...)
{ return (struct workqueue_struct *)&wq_ids[nwq++ & 63]; }

static struct work_struct *pending[16384];
static int npending;
bool queue_work(struct workqueue_struct *wq, struct work_struct *w)
{
	if (w->pending)
		return false;
	w->pending = 1;
	w->wq = wq;
	CHECK(npending < 16384);
	pending[npending++] = w;
	return true;
}

static struct delayed_work *delayed[16];
static unsigned long delayed_ms[16];
static int ndelayed;
bool schedule_delayed_work(struct delayed_work *w, unsigned long d)
{
	if (w->work.pending)
		return false;
	w->work.pending = 1;
	CHECK(ndelayed < 16);
	delayed_ms[ndelayed] = d;
	delayed[ndelayed++] = w;
	return true;
}
bool cancel_delayed_work(struct delayed_work *w)
{
	if (!w->work.pending)
		return false;
	for (int i = 0; i < ndelayed; i++) {
		if (delayed[i] != w)
			continue;
		memmove(&delayed[i], &delayed[i + 1], (ndelayed - i - 1) * sizeof(delayed[0]));
		memmove(&delayed_ms[i], &delayed_ms[i + 1], (ndelayed - i - 1) * sizeof(delayed_ms[0]));
		ndelayed--;
		break;
	}
	w->work.pending = 0;
	return true;
}

/* An ordered queue runs one item at a time: never start a second while one executes. */
static void *busy_wq[16];
static int nbusy;
static bool wq_busy(void *wq)
{
	for (int i = 0; i < nbusy; i++)
		if (busy_wq[i] == wq)
			return true;
	return false;
}

static bool run_one_work(bool packet_only)
{
	for (int i = 0; i < npending; i++) {
		struct work_struct *w = pending[i];

		if (wq_busy(w->wq))
			continue;
		if (packet_only && w->func != dchid_packet_work)
			continue;
		memmove(&pending[i], &pending[i + 1], (npending - i - 1) * sizeof(pending[0]));
		npending--;
		w->pending = 0;
		CHECK(nbusy < 16);
		busy_wq[nbusy++] = w->wq;
		w->func(w);
		nbusy--;
		return true;
	}
	return false;
}

static bool run_works(void)
{
	bool any = false;

	while (run_one_work(false))
		any = true;
	return any;
}

/* fires every delayed work currently scheduled (the test controls "time") */
static void run_delayed(void)
{
	struct delayed_work *list[16];
	int n = ndelayed;

	memcpy(list, delayed, n * sizeof(list[0]));
	ndelayed = 0;
	for (int i = 0; i < n; i++) {
		list[i]->work.pending = 0;
		list[i]->work.func(&list[i]->work);
	}
}

/* ------------------------------------------------------------------ HID */
static struct hid_device *hids[32];
static int nhids;
struct report_rec { struct hid_device *h; u32 size; u8 data[2048]; };
static struct report_rec reports[2048];
static int nreports;
static int parse_fail;

struct hid_device *hid_allocate_device(void) { return track(calloc(1, sizeof(struct hid_device))); }
int hid_parse_report(struct hid_device *h, __u8 *start, unsigned size)
{
	if (!start || !size || size > 4096) { parse_fail++; return -EINVAL; }
	return 0;
}
int hid_add_device(struct hid_device *h)
{
	int ret = h->ll_driver->parse(h);

	if (ret)
		return ret;
	ret = h->ll_driver->start(h);
	if (ret)
		return ret;
	hids[nhids++] = h;
	return 0;
}
void hid_destroy_device(struct hid_device *h) { }
int hid_input_report(struct hid_device *h, int type, u8 *data, u32 size, int intr)
{
	CHECK(nreports < 2048 && size <= sizeof(reports[0].data));
	reports[nreports].h = h;
	reports[nreports].size = size;
	memcpy(reports[nreports].data, data, size);
	nreports++;
	return 0;
}
static struct hid_device *find_hid(const char *name)
{
	for (int i = 0; i < nhids; i++)
		if (!strcmp(hids[i]->name, name))
			return hids[i];
	return NULL;
}

/* ---------------------------------------------------------- DockChannel */
struct dockchannel { int x; };
static struct dockchannel dc_obj;
static u8 tx[1 << 20];
static size_t tx_len;
static u8 rx[1 << 21];
static size_t rx_len, rx_pos;
static void (*await_cb)(void *, size_t);
static void *await_cookie;
static size_t await_count;
static bool awaiting;

struct dockchannel *dockchannel_init(struct platform_device *p) { return &dc_obj; }
int dockchannel_send(struct dockchannel *dc, const void *buf, size_t n)
{
	CHECK(tx_len + n <= sizeof(tx));
	memcpy(tx + tx_len, buf, n);
	tx_len += n;
	return (int)n;
}
int dockchannel_recv(struct dockchannel *dc, void *buf, size_t n)
{
	if (rx_len - rx_pos < n)
		return -ETIMEDOUT;
	memcpy(buf, rx + rx_pos, n);
	rx_pos += n;
	return (int)n;
}
int dockchannel_await(struct dockchannel *dc, void (*cb)(void *, size_t), void *cookie, size_t n)
{
	await_cb = cb; await_cookie = cookie; await_count = n; awaiting = true;
	return (int)n;
}
static bool dock_irq(void)
{
	if (awaiting && rx_len - rx_pos >= await_count) {
		awaiting = false;
		await_cb(await_cookie, rx_len - rx_pos);
		return true;
	}
	return false;
}

/* ------------------------------------------------- firmware model (device) */
static u32 le32(const u8 *p) { return p[0] | p[1] << 8 | p[2] << 16 | (u32)p[3] << 24; }
static void put32(u8 *p, u32 v) { p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24; }
static u64 le64(const u8 *p) { return (u64)le32(p) | (u64)le32(p + 4) << 32; }

static size_t mk_msg(u8 *out, u8 type, u8 seq, u8 iface, u8 flags, const void *pl, u16 plen, u8 status)
{
	size_t body = (8 + (size_t)plen + 3) & ~(size_t)3;
	size_t total = 8 + body + 4;
	u32 sum = 0;

	memset(out, 0, total);
	out[0] = 8; out[1] = type; out[2] = body; out[3] = body >> 8;
	out[4] = seq; out[5] = iface; out[7] = status;
	out[8] = flags; out[10] = plen; out[11] = plen >> 8;
	if (plen)
		memcpy(out + 16, pl, plen);
	for (size_t i = 0; i < 8 + body; i += 4)
		sum += le32(out + i);
	put32(out + 8 + body, ~sum);
	return total;
}

static struct fw_model {
	bool echo_payload;	/* FIFO-era acks echo report id/data; false = bare ack */
	bool ack_via_ring;
	bool flags_echo;	/* ack carries the host's flags (false: zero) */
	bool auto_ack;
	bool mute;		/* never answer commands */
	u8 ack_status;		/* byte 7 of ack headers */
	size_t parsed;
	int nhost;
	struct { u8 seq, iface, flags; u16 len; u8 data[24]; } host[128];
} fw;

static struct dockchannel_hid *drv;
static struct dchid_ring fwring;	/* the device-side producer view of the same memory */
static unsigned doorbells;

static void dev_to_dock(const u8 *msg, size_t n)
{
	CHECK(rx_len + n <= sizeof(rx));
	memcpy(rx + rx_len, msg, n);
	rx_len += n;
}

/* a type-0 frame with no body at all: the smallest legal message (12 bytes) */
static void ring_doorbell(void)
{
	u8 m[12];

	memset(m, 0, sizeof(m));
	m[0] = 8;
	put32(m + 8, ~(le32(m) + le32(m + 4)));
	dev_to_dock(m, 12);
	doorbells++;
}

static void dev_send(const u8 *msg, size_t n, bool via_ring)
{
	if (via_ring) {
		CHECK(dchid_ring_write(&fwring, msg, n) == (long)n);
		ring_doorbell();
	} else {
		dev_to_dock(msg, n);
	}
}

static void dev_event(const void *payload, u16 len, bool via_ring)
{
	u8 m[512];
	size_t n = mk_msg(m, 0x12, 0, 0, 0, payload, len, 0);

	dev_send(m, n, via_ring);
}

static void dev_report(u8 iface, const void *payload, u16 len, bool via_ring)
{
	u8 m[2048];
	size_t n = mk_msg(m, 0x12, 0, iface, 0, payload, len, 0);

	dev_send(m, n, via_ring);
}

static u16 get_report_data(u8 id, u8 *out)
{
	switch (id) {
	case STM_REPORT_ID:
		out[0] = id;
		memset(out + 1, 0, 11);
		out[2] = 0xac; out[3] = 0x05;	/* vendor 0x05ac */
		out[4] = 0x40; out[5] = 0x03;	/* synthetic product 0x0340 */
		out[10] = 0x01;			/* keyboard type */
		out[11] = 13;			/* serial length */
		return 12;
	case STM_REPORT_SERIAL:
		out[0] = id;
		memcpy(out + 1, "SYNTHETIC0001", 13);
		return 14;
	}
	out[0] = id;
	return 1;
}

static void model_ack(const u8 *m)
{
	u8 flags = m[8], seq = m[4], iface = m[5];
	u16 plen = m[10] | m[11] << 8;
	const u8 *pl = m + 16;
	u8 resp[64];
	u16 rl = 0;
	u8 out[256];
	size_t n;

	/* a GET_REPORT answer always carries the report; only SET acks may be bare */
	if ((flags & 0x3f) == REQ_GET_REPORT && plen >= 1) {
		rl = get_report_data(pl[0], resp);
	} else if (fw.echo_payload) {
		rl = plen < sizeof(resp) ? plen : sizeof(resp);
		memcpy(resp, pl, rl);
	}
	n = mk_msg(out, 0x11, seq, iface, fw.flags_echo ? flags : 0, resp, rl, fw.ack_status);
	dev_send(out, n, fw.ack_via_ring);

	/* a reset-to-state-2 makes the interface report ready, as the FIFO-era firmware did */
	if (plen == 4 && pl[0] == CMD_RESET_INTERFACE && pl[3] == 2) {
		u8 ev[4] = { 0xf1, pl[2], 0, 0 };

		dev_event(ev, sizeof(ev), fw.ack_via_ring);
	}
}

static void model_process_tx(void)
{
	while (tx_len - fw.parsed >= 12) {
		const u8 *m = tx + fw.parsed;
		u16 length = m[2] | m[3] << 8;
		size_t total = 8 + (size_t)length + 4;
		u32 sum = 0;

		if (tx_len - fw.parsed < total)
			break;
		CHECK(m[0] == 8);
		CHECK(m[1] == 0x11);
		CHECK((length & 3) == 0 && length >= 8);
		for (size_t i = 0; i + 4 <= total - 4; i += 4)
			sum += le32(m + i);
		CHECK(le32(m + total - 4) == ~sum);
		if (fw.nhost < 128) {
			u16 plen = m[10] | m[11] << 8;

			fw.host[fw.nhost].seq = m[4];
			fw.host[fw.nhost].iface = m[5];
			fw.host[fw.nhost].flags = m[8];
			fw.host[fw.nhost].len = plen;
			memcpy(fw.host[fw.nhost].data, m + 16, plen < 24 ? plen : 24);
			fw.nhost++;
		}
		if (fw.auto_ack && !fw.mute)
			model_ack(m);
		fw.parsed += total;
	}
}

static bool world_step(void)
{
	size_t before = fw.parsed;
	bool progress;

	model_process_tx();
	progress = fw.parsed != before;
	if (dock_irq())
		progress = true;
	if (run_one_work(true))
		progress = true;
	return progress;
}

static void settle(void)
{
	for (int i = 0; i < 4000; i++) {
		bool p = world_step();

		p |= run_works();
		if (!p)
			return;
	}
	CHECK(!"settle did not converge");
}

/* ---------------------------------------------------------- scenario glue */
static const u8 kbd_desc[] = {
	0x05, 0x01, 0x09, 0x06, 0xa1, 0x01, 0x05, 0x07, 0x19, 0xe0, 0x29, 0xe7, 0x15, 0x00, 0x25,
	0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02, 0x95, 0x01, 0x75, 0x08, 0x81, 0x01, 0x95, 0x06,
	0x75, 0x08, 0x15, 0x00, 0x25, 0x65, 0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00, 0xc0,
};

static void blk(u8 *out, size_t *n, u16 type, const void *data, u16 len)
{
	out[(*n)++] = type; out[(*n)++] = type >> 8;
	out[(*n)++] = len; out[(*n)++] = len >> 8;
	memcpy(out + *n, data, len);
	*n += len;
}

/* m5: append the extra blocks newer firmware sends after the transport block */
static size_t mk_init(u8 *out, u8 iface, const char *name, const u8 *desc, u16 dlen, bool m5,
		      u16 ready_status, unsigned trailing_zero)
{
	size_t n = 0;
	u8 transport[6] = { 0, 0, 0, 0, 0, 0 };

	memset(out, 0, 22);
	out[n++] = 0xf0; out[n++] = 0; out[n++] = 0; out[n++] = iface;
	strncpy((char *)out + n, name, 15);
	n += 16;
	out[n++] = 0; out[n++] = 0;
	if (desc)
		blk(out, &n, 0, desc, dlen);
	blk(out, &n, 2, transport, 6);
	if (m5) {
		u8 rs[2] = { ready_status, ready_status >> 8 };
		u8 ifs[4] = { 1, 2, 3, 4 };
		u32 loc = 0x1000;

		blk(out, &n, 3, "SYNTH0001", 10);
		blk(out, &n, 4, rs, 2);
		blk(out, &n, 5, ifs, 4);
		blk(out, &n, 6, &loc, 4);
		blk(out, &n, 7, "Synthetic Device", 17);
	}
	while (trailing_zero--)
		out[n++] = 0;
	return n;
}

static int world_reset(void)
{
	free_tracked();
	memset(nlog, 0, sizeof(nlog));
	last_err[0] = 0;
	ntracked = 0; kalloc_live = 0;
	nwq = 0; npending = 0; ndelayed = 0; nbusy = 0;
	nhids = 0; nreports = 0; parse_fail = 0;
	tx_len = 0; rx_len = rx_pos = 0; awaiting = false;
	wait_timeouts = 0; doorbells = 0; dma_allocs = 0; fw_requests = 0;
	memset(&fw, 0, sizeof(fw));
	fw.auto_ack = true;
	fw.flags_echo = true;
	memset(&the_fw, 0, sizeof(the_fw));
	next_iova = 0x100000028000ULL;	/* inside the DART window, like macOS' live IOVA */
	dt_reset();
	drv = NULL;
	mtp_ring = -1;
	mtp_enable_cmd = true;
	mtp_poll_ms = 0;
	mtp_ring_size = RING_DEFAULT_SIZE;
	return 0;
}

static int do_probe(const struct dchid_cfg *cfg)
{
	int ret;

	match_data = cfg;
	ret = dockchannel_hid_driver.probe(&pdev);
	if (ret)
		return ret;
	drv = await_cookie;
	if (drv->ring_mode)
		dchid_ring_init(&fwring, drv->ring.mem, drv->ring.size);
	return 0;
}

static int probe_fresh(const struct dchid_cfg *cfg)
{
	world_reset();
	return do_probe(cfg);
}

static int count_host(u8 iface, u8 byte0)
{
	int n = 0;

	for (int i = 0; i < fw.nhost; i++)
		if (fw.host[i].iface == iface && fw.host[i].len && fw.host[i].data[0] == byte0)
			n++;
	return n;
}

static int find_host(u8 iface, u8 byte0)
{
	for (int i = 0; i < fw.nhost; i++)
		if (fw.host[i].iface == iface && fw.host[i].len && fw.host[i].data[0] == byte0)
			return i;
	return -1;
}

/* the first thing the (modelled) firmware does, then the 100 ms handshake */
static void first_traffic_and_handshake(void)
{
	ring_doorbell();
	settle();
	CHECK_EQ(ndelayed, 1);
	run_delayed();
	settle();
}

static void announce(bool via_ring, bool m5, u16 stm_status, unsigned pad)
{
	u8 buf[512];
	size_t n;

	n = mk_init(buf, 3, "stm", kbd_desc, sizeof(kbd_desc), m5, stm_status, pad);
	dev_event(buf, n, via_ring);
	n = mk_init(buf, 2, "keyboard", kbd_desc, sizeof(kbd_desc), m5, 0, pad);
	dev_event(buf, n, via_ring);
}

static void ready_event(u8 iface, u16 status, bool via_ring)
{
	u8 ev[4] = { 0xf1, iface, status, status >> 8 };

	dev_event(ev, sizeof(ev), via_ring);
}

/* ================================================================ tests */
static void test_probe(void)
{
	printf("probe: ring compatible selects ring mode\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	CHECK(drv->ring_mode);
	CHECK_EQ(drv->ring.size, 0x200000);
	CHECK_EQ(drv->ring.cap, 0x200000 - 8);
	CHECK_EQ(dma_allocs, 1);
	CHECK(awaiting);
	CHECK_EQ(await_count, 8);
	CHECK(drv->comm != NULL);
	CHECK(drv->ring_asm.buf != NULL);
	CHECK_EQ(le32(drv->ring.mem), 0);
	CHECK_EQ(le32(drv->ring.mem + 4), 0);

	printf("probe: generic compatible stays FIFO-only\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_fifo), 0);
	CHECK(!drv->ring_mode);
	CHECK_EQ(dma_allocs, 0);

	printf("probe: module parameters override the compatible\n");
	world_reset();
	mtp_ring = 1;
	CHECK_EQ(do_probe(&dchid_cfg_fifo), 0);
	CHECK(drv->ring_mode);
	world_reset();
	mtp_ring = 0;
	CHECK_EQ(do_probe(&dchid_cfg_ring), 0);
	CHECK(!drv->ring_mode);
	CHECK_EQ(dma_allocs, 0);

	printf("probe: ring size is clamped and page-rounded\n");
	world_reset();
	mtp_ring_size = 100;
	CHECK_EQ(do_probe(&dchid_cfg_ring), 0);
	CHECK_EQ(drv->ring.size, 0x4000);
	world_reset();
	mtp_ring_size = 0x7fffffff;
	CHECK_EQ(do_probe(&dchid_cfg_ring), 0);
	CHECK_EQ(drv->ring.size, 0x1000000);
	world_reset();
	mtp_ring_size = 0x5001;
	CHECK_EQ(do_probe(&dchid_cfg_ring), 0);
	CHECK_EQ(drv->ring.size, 0x8000);

	printf("probe: defers while the helper has not bound\n");
	world_reset();
	helper_pdev.dev.links.status = 0;
	match_data = &dchid_cfg_ring;
	CHECK_EQ(dockchannel_hid_driver.probe(&pdev), -EPROBE_DEFER);
}

static void check_handshake(void)
{
	int a, f;

	CHECK_EQ(ndelayed, 0);
	CHECK(drv->ring_registered);
	a = find_host(0, 0xc1);
	f = find_host(0, 0x91);
	CHECK(a >= 0 && f >= 0);
	if (a < 0 || f < 0)
		return;
	CHECK(a < f);				/* awake first, then the ring */
	CHECK_EQ(fw.host[a].flags, 0x80);	/* feature report, SET */
	CHECK_EQ(fw.host[a].iface, 0);
	CHECK_EQ(fw.host[a].len, 2);
	CHECK_EQ(fw.host[a].data[1], 2);	/* awake */
	CHECK_EQ(fw.host[f].flags, 0x80);
	CHECK_EQ(fw.host[f].iface, 0);
	CHECK_EQ(fw.host[f].len, 15);
	CHECK_EQ(fw.host[f].data[1], 0);
	CHECK_EQ(fw.host[f].data[2], 0);
	CHECK_EQ(le64(fw.host[f].data + 3), 0x100000028000ULL);	/* the IOVA the DMA API returned */
	CHECK_EQ(le32(fw.host[f].data + 11), 0x200000);	/* total size, index header included */
}

static void test_handshake(void)
{
	printf("handshake: first DockChannel traffic arms it once, 100 ms later\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	ring_doorbell();
	CHECK(dock_irq());
	CHECK_EQ(ndelayed, 1);
	CHECK_EQ(delayed_ms[0], RING_HANDSHAKE_DELAY_MS);
	CHECK(!drv->ring_registered);
	CHECK_EQ(fw.nhost, 0);
	ring_doorbell();
	CHECK(dock_irq());
	CHECK_EQ(ndelayed, 1);

	run_delayed();
	settle();
	check_handshake();
	CHECK_EQ(wait_timeouts, 0);
	CHECK_EQ(nlog[KSHIM_ERR], 0);
	CHECK_EQ(kalloc_live, 0);

	printf("handshake: failed registration is reported but draining continues\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	ring_doorbell();
	CHECK(dock_irq());
	fw.mute = true;
	run_delayed();
	CHECK(!drv->ring_registered);
	CHECK(nlog[KSHIM_ERR] >= 1);
	CHECK(wait_timeouts >= 2);
}

static void enumerate(bool via_ring, bool m5)
{
	struct hid_device *kbd;

	announce(via_ring, m5, 0, m5 ? 5 : 0);
	settle();
	/* the STM is created at once; the keyboard waits for the STM identity */
	CHECK(find_hid("Apple MTP stm") != NULL);
	CHECK(find_hid("Apple MTP keyboard") == NULL);
	CHECK(drv->ifaces[2] && drv->ifaces[2]->deferred);
	CHECK_EQ(count_host(0, CMD_ENABLE_INTERFACE), 1);

	ready_event(3, 0, via_ring);
	settle();
	CHECK(drv->id_ready);
	CHECK_EQ(count_host(3, STM_REPORT_ID), 1);
	CHECK_EQ(count_host(3, STM_REPORT_SERIAL), 1);
	kbd = find_hid("Apple MTP keyboard");
	CHECK(kbd != NULL);
	if (kbd) {
		CHECK_EQ(kbd->type, HID_TYPE_SPI_KEYBOARD);
		CHECK_EQ(kbd->vendor, 0x05ac);
		CHECK_EQ(kbd->product, 0x0340);
		CHECK(!strcmp(kbd->uniq, "SYNTHETIC0001"));
	}
	CHECK_EQ(count_host(0, CMD_ENABLE_INTERFACE), 2);	/* STM, keyboard */
	CHECK_EQ(parse_fail, 0);
	if (drv->ring_mode) {
		CHECK_EQ(ndelayed, mtp_poll_ms ? 1 : 0);	/* no second handshake, no stray timers */
		CHECK_EQ(count_host(0, 0x91), 1);
	}
}

static void send_reports(bool via_ring, int first, int count, size_t size)
{
	u8 rep[1800];

	for (int i = first; i < first + count; i++) {
		memset(rep, 0, sizeof(rep));
		rep[0] = i & 0xff;
		rep[1] = (i >> 8) & 0xff;
		for (size_t j = 2; j < size; j++)
			rep[j] = (u8)(i * 31 + j);
		dev_report(2, rep, size, via_ring);
		settle();
	}
}

static void test_enumeration_and_input(bool echo, bool acks_via_ring)
{
	struct hid_device *kbd;

	printf("ring: enumeration, input, wrap-around (%s acks%s)\n", echo ? "echo" : "bare",
	       acks_via_ring ? ", acks through the ring" : "");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	fw.echo_payload = echo;
	fw.ack_via_ring = acks_via_ring;
	first_traffic_and_handshake();
	check_handshake();

	enumerate(true, true);
	kbd = find_hid("Apple MTP keyboard");
	CHECK(kbd != NULL);
	if (!kbd)
		return;

	/* hid-core opens the device: it needs the interface's ready event */
	ready_event(2, 0, true);
	settle();
	CHECK_EQ(kbd->ll_driver->open(kbd), 0);

	send_reports(true, 0, 5, 8);
	CHECK_EQ(nreports, 5);
	for (int i = 0; i < nreports && i < 5; i++) {
		CHECK(reports[i].h == kbd);
		CHECK_EQ(reports[i].size, 8);
		CHECK_EQ(reports[i].data[0], i);
	}

	/* several trips around the 2 MiB ring with trackpad-sized reports, one at a time */
	{
		int total = 1600, seen = 0;
		bool ordered = true;
		u32 prev_wr = 0, wraps = 0;

		for (int i = 0; i < total; i++) {
			u32 wr;

			nreports = 0;
			send_reports(true, i, 1, 1752);
			if (nreports == 1) {
				struct report_rec *r = &reports[0];

				if (r->size != 1752 || r->data[0] != (i & 0xff) ||
				    r->data[1] != ((i >> 8) & 0xff) || r->data[1751] != (u8)(i * 31 + 1751))
					ordered = false;
				seen++;
			}
			wr = le32(drv->ring.mem);
			if (wr < prev_wr)
				wraps++;
			prev_wr = wr;
		}
		CHECK_EQ(seen, total);
		CHECK(ordered);
		CHECK(wraps >= 1);	/* 1600 x ~1.77 KB is more than one 2 MiB trip */
		CHECK_EQ(le32(drv->ring.mem), le32(drv->ring.mem + 4));	/* drained */
	}
	CHECK_EQ(nlog[KSHIM_ERR], 0);
	CHECK_EQ(wait_timeouts, 0);
	CHECK_EQ(kalloc_live, 0);
}

static void test_batched(void)
{
	struct hid_device *kbd;
	u8 rep[1752];
	int written = 0;

	printf("ring: bursts queued before one doorbell, ring filled to capacity\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	first_traffic_and_handshake();
	enumerate(true, true);
	ready_event(2, 0, true);
	settle();
	kbd = find_hid("Apple MTP keyboard");
	CHECK(kbd && kbd->ll_driver->open(kbd) == 0);
	nreports = 0;

	for (;;) {
		u8 m[2048];
		size_t n;

		memset(rep, 0, sizeof(rep));
		rep[0] = written & 0xff;
		rep[1] = (written >> 8) & 0xff;
		n = mk_msg(m, 0x12, 0, 2, 0, rep, sizeof(rep), 0);
		if (dchid_ring_write(&fwring, m, n) != (long)n)
			break;
		written++;
		if (written > 5000)
			break;
	}
	CHECK(written > 1000 && written < 5000);
	ring_doorbell();
	/* the whole burst is in the ring; the driver drains it with one RX callback */
	{
		int guard = 0;

		while (nreports < written && guard++ < 10) {
			settle();
			if (nreports < written)
				break;
		}
	}
	/* one drain call is bounded (1 << 14 steps); anything left needs another trigger */
	while (nreports < written) {
		int before = nreports;

		ring_doorbell();
		settle();
		if (nreports == before)
			break;
	}
	CHECK_EQ(nreports, written);
	for (int i = 0; i < nreports && i < written; i++) {
		if (reports[i].data[0] != (i & 0xff) || reports[i].data[1] != ((i >> 8) & 0xff)) {
			CHECK(!"burst order");
			break;
		}
	}
	CHECK_EQ(kalloc_live, 0);
}

static void test_errors(void)
{
	u8 m[128], rep[16];
	size_t n;
	struct hid_device *kbd;

	printf("ring: bad checksum, bad indices, unknown interface, type-0 with a body\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	first_traffic_and_handshake();
	enumerate(true, true);
	ready_event(2, 0, true);
	settle();
	kbd = find_hid("Apple MTP keyboard");
	CHECK(kbd && kbd->ll_driver->open(kbd) == 0);
	nreports = 0;
	nlog[KSHIM_ERR] = 0;
	memset(rep, 0x55, sizeof(rep));

	/* bad checksum: dropped and counted; the next good message still arrives */
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	m[n - 1] ^= 0x40;
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	ring_doorbell();
	settle();
	CHECK_EQ(nreports, 0);
	CHECK(nlog[KSHIM_ERR] >= 1);
	CHECK(drv->ring_drops >= 1);
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	ring_doorbell();
	settle();
	CHECK_EQ(nreports, 1);

	/* a bad checksum does not cost the messages queued behind it */
	nreports = 0;
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	m[n - 4] ^= 0x01;
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	ring_doorbell();
	settle();
	CHECK_EQ(nreports, 2);

	/* write index beyond the data area: ring reset, no crash, recovery */
	nreports = 0;
	nlog[KSHIM_ERR] = 0;
	put32(drv->ring.mem, drv->ring.cap + 100);
	ring_doorbell();
	settle();
	CHECK(nlog[KSHIM_ERR] >= 1);
	CHECK_EQ(le32(drv->ring.mem), 0);
	CHECK_EQ(le32(drv->ring.mem + 4), 0);
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	ring_doorbell();
	settle();
	CHECK_EQ(nreports, 1);

	/*
	 * A header that declares a 64 KiB body is legal framing: the driver waits for it (as
	 * macOS does), then rejects the checksum and resynchronises. Feed it that much data.
	 */
	nreports = 0;
	nlog[KSHIM_ERR] = 0;
	{
		static u8 junk[0x10008];
		unsigned long drops = drv->ring_drops;

		memset(junk, 0, sizeof(junk));
		junk[0] = 8; junk[1] = 0x12; junk[2] = 0xfc; junk[3] = 0xff; junk[5] = 2;
		for (size_t off = 0; off < sizeof(junk); off += 4096) {
			size_t chunk = sizeof(junk) - off < 4096 ? sizeof(junk) - off : 4096;

			CHECK(dchid_ring_write(&fwring, junk + off, chunk) == (long)chunk);
			ring_doorbell();
			settle();
		}
		CHECK(drv->ring_drops > drops);	/* checksum mismatch after the whole body */
		CHECK(nlog[KSHIM_ERR] >= 1);
	}
	/* header length above 8 is a framing error: buffered data is discarded, ring recovers */
	{
		u8 bad[12] = { 9, 0x12, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0 };
		unsigned long drops = drv->ring_drops;

		nreports = 0;
		CHECK(dchid_ring_write(&fwring, bad, 12) == 12);
		n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
		CHECK(dchid_ring_write(&fwring, m, n) == (long)n);	/* queued behind: lost with it */
		ring_doorbell();
		settle();
		CHECK(drv->ring_drops > drops);
		CHECK_EQ(nreports, 0);
	}
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	ring_doorbell();
	settle();
	CHECK_EQ(nreports, 1);

	/* unknown interfaces are dropped without desynchronising the stream */
	nreports = 0;
	n = mk_msg(m, 0x12, 0, 9, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	n = mk_msg(m, 0x12, 0, 200, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	ring_doorbell();
	settle();
	CHECK_EQ(nreports, 1);

	/* a type-0 frame that carries a body is not a doorbell: ignored cleanly */
	nreports = 0;
	n = mk_msg(m, 0, 0, 2, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);
	ring_doorbell();
	settle();
	CHECK_EQ(nreports, 1);
	CHECK_EQ(kalloc_live, 0);
}

static void test_poll(void)
{
	struct hid_device *kbd;
	u8 m[64], rep[8] = { 1, 2, 3, 4, 5, 6, 7, 8 };
	size_t n;

	printf("ring: debug polling drains data that came without a doorbell\n");
	world_reset();
	mtp_poll_ms = 10;
	CHECK_EQ(do_probe(&dchid_cfg_ring), 0);
	first_traffic_and_handshake();
	CHECK_EQ(ndelayed, 1);		/* the poll timer re-armed itself */
	enumerate(true, true);
	ready_event(2, 0, true);
	settle();
	kbd = find_hid("Apple MTP keyboard");
	CHECK(kbd && kbd->ll_driver->open(kbd) == 0);
	nreports = 0;
	n = mk_msg(m, 0x12, 0, 2, 0, rep, 8, 0);
	CHECK(dchid_ring_write(&fwring, m, n) == (long)n);	/* no doorbell */
	settle();
	CHECK_EQ(nreports, 0);
	run_delayed();			/* poll tick */
	settle();
	CHECK_EQ(nreports, 1);
	CHECK_EQ(ndelayed, 1);
}

static void test_fifo_mode(void)
{
	struct hid_device *kbd;
	u8 buf[512];
	size_t n;

	printf("fifo: the FIFO-era path is unchanged (no ring, no handshake, strict acks)\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_fifo), 0);
	fw.echo_payload = true;
	/*
	 * FIFO-era firmware ended an init packet with the transport block; whatever follows
	 * (padding, or blocks only newer firmware sends) is not parsed in this mode.
	 */
	n = mk_init(buf, 3, "stm", kbd_desc, sizeof(kbd_desc), false, 0, 9);
	dev_event(buf, n, false);
	n = mk_init(buf, 2, "keyboard", kbd_desc, sizeof(kbd_desc), true, 1, 9);
	dev_event(buf, n, false);
	settle();
	CHECK(drv->ifaces[2] != NULL && !drv->ifaces[2]->inactive);
	CHECK_EQ(ndelayed, 0);
	CHECK(!drv->ring_registered);
	CHECK_EQ(count_host(0, 0xc1), 0);
	CHECK_EQ(count_host(0, 0x91), 0);
	CHECK(find_hid("Apple MTP stm") != NULL);
	CHECK(find_hid("Apple MTP keyboard") == NULL);
	dev_event(NULL, 0, false);	/* zero-length event: ignored */
	/* an empty type-0 frame is only special in ring mode: here it is still a bad body */
	nlog[KSHIM_ERR] = 0;
	ring_doorbell();
	settle();
	CHECK_EQ(nlog[KSHIM_ERR], 1);
	nlog[KSHIM_ERR] = 0;
	ready_event(3, 0, false);
	settle();
	kbd = find_hid("Apple MTP keyboard");
	CHECK(kbd != NULL);
	CHECK_EQ(drv->ifaces[2]->hid_desc_len, sizeof(kbd_desc));
	ready_event(2, 0, false);
	settle();
	CHECK(kbd && kbd->ll_driver->open(kbd) == 0);
	send_reports(false, 0, 3, 8);
	CHECK_EQ(nreports, 3);

	/* FIFO mode keeps rejecting a bare ack and a status-less mismatch: the command times out */
	fw.echo_payload = false;
	{
		u8 setrep[2] = { 0x77, 0x01 };
		int before = wait_timeouts;
		int r = dchid_set_report(drv->ifaces[2], setrep, 2);

		CHECK(r < 0);
		CHECK_EQ(wait_timeouts, before + 1);
	}
	CHECK_EQ(kalloc_live, 0);
}

static void test_acks(void)
{
	int r;
	u8 setrep[2] = { 0x77, 0x01 };

	printf("ack: matched by transfer id, bare ack and zeroed flags accepted in ring mode\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	fw.echo_payload = false;
	fw.flags_echo = false;
	first_traffic_and_handshake();
	CHECK(drv->ring_registered);
	CHECK_EQ(wait_timeouts, 0);
	r = dchid_comm_cmd(drv, setrep, 2);
	CHECK(r >= 0);

	printf("ack: a non-zero status byte in the header becomes an error\n");
	fw.ack_status = 0x5;
	r = dchid_comm_cmd(drv, setrep, 2);
	CHECK(r < 0);
	fw.ack_status = 0;

	printf("ack: a wrong transfer id is ignored\n");
	{
		u8 bad[64];
		size_t n;
		int before = wait_timeouts;

		fw.mute = true;
		r = dchid_comm_cmd(drv, setrep, 2);
		CHECK(r < 0);
		CHECK_EQ(wait_timeouts, before + 1);
		nlog[KSHIM_ERR] = 0;
		n = mk_msg(bad, 0x11, 77, 0, 0x80, NULL, 0, 0);
		dev_to_dock(bad, n);
		settle();
		CHECK(nlog[KSHIM_ERR] >= 1);
	}
	CHECK_EQ(kalloc_live, 0);
}

static void test_enable_cmd_param(void)
{
	printf("param: mtp_enable_cmd=0 suppresses the 0xb4 enable command\n");
	world_reset();
	mtp_enable_cmd = false;
	CHECK_EQ(do_probe(&dchid_cfg_ring), 0);
	first_traffic_and_handshake();
	announce(true, true, 0, 0);
	settle();
	ready_event(3, 0, true);
	settle();
	CHECK_EQ(count_host(0, CMD_ENABLE_INTERFACE), 0);
	CHECK(find_hid("Apple MTP keyboard") != NULL);
}

static void test_stm_fallback(void)
{
	printf("stm: keyboard still appears when the STM never becomes ready\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	first_traffic_and_handshake();
	announce(true, true, 1, 0);	/* the STM announces itself as inactive */
	settle();
	CHECK(find_hid("Apple MTP keyboard") == NULL);
	CHECK(drv->ifaces[3]->inactive);
	CHECK_EQ(ndelayed, 1);		/* the fallback timer */
	CHECK_EQ(delayed_ms[0], STM_FALLBACK_MS);
	ready_event(3, 1, true);	/* ready event, status != 0: inactive, not ready */
	settle();
	CHECK(!drv->id_ready);
	CHECK_EQ(ndelayed, 1);
	run_delayed();
	settle();
	CHECK(drv->id_ready);
	CHECK(find_hid("Apple MTP keyboard") != NULL);
	CHECK(nlog[KSHIM_WARN] >= 1);
	CHECK_EQ(drv->device_id.vendor_id, 0x05ac);

	printf("stm: a ready STM cancels the fallback\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	first_traffic_and_handshake();
	announce(true, true, 0, 0);
	settle();
	CHECK_EQ(ndelayed, 1);
	ready_event(3, 0, true);
	settle();
	CHECK_EQ(ndelayed, 0);
	CHECK(drv->id_ready);
	CHECK(find_hid("Apple MTP keyboard") != NULL);
}

static void test_inactive_without_descriptor(void)
{
	u8 buf[512];
	size_t n;

	printf("init: an inactive interface without a descriptor is created only once it has one\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	first_traffic_and_handshake();
	n = mk_init(buf, 3, "stm", kbd_desc, sizeof(kbd_desc), true, 0, 0);
	dev_event(buf, n, true);
	settle();
	ready_event(3, 0, true);
	settle();
	CHECK(drv->id_ready);
	n = mk_init(buf, 1, "multi-touch", NULL, 0, true, 1, 0);
	dev_event(buf, n, true);
	settle();
	CHECK(find_hid("Apple MTP multi-touch") == NULL);
	CHECK(drv->ifaces[1] != NULL && drv->ifaces[1]->inactive);
	CHECK(!drv->ifaces[1]->creating);
	n = mk_init(buf, 1, "multi-touch", kbd_desc, sizeof(kbd_desc), true, 0, 0);
	dev_event(buf, n, true);
	settle();
	CHECK(find_hid("Apple MTP multi-touch") != NULL);
	CHECK(!drv->ifaces[1]->inactive);
}

static void test_firmware_upload(void)
{
	static u8 blob[4096 + 20];
	u8 buf[512];
	size_t n;
	int fi;
	struct hid_device *mt;

	printf("firmware: upload uses the 0x95 type-2 command and a DART-visible buffer\n");
	CHECK_EQ(probe_fresh(&dchid_cfg_ring), 0);
	n_mt.firmware_name = "apple/test-multitouch.bin";
	memset(blob, 0, sizeof(blob));
	put32(blob + 0, 0x46444948);	/* "HIDF" container, synthetic payload */
	put32(blob + 4, 1);
	put32(blob + 8, 20);
	put32(blob + 12, 4096);
	put32(blob + 16, 0);
	for (int i = 0; i < 4096; i++)
		blob[20 + i] = (u8)(i * 7);
	the_fw.data = blob;
	the_fw.size = sizeof(blob);

	first_traffic_and_handshake();
	n = mk_init(buf, 3, "stm", kbd_desc, sizeof(kbd_desc), true, 0, 0);
	dev_event(buf, n, true);
	settle();
	ready_event(3, 0, true);
	settle();
	n = mk_init(buf, 1, "multi-touch", kbd_desc, sizeof(kbd_desc), true, 0, 0);
	dev_event(buf, n, true);
	settle();
	mt = find_hid("Apple MTP multi-touch");
	CHECK(mt != NULL);
	if (!mt)
		return;
	CHECK_EQ(mt->type, HID_TYPE_SPI_MOUSE);
	CHECK_EQ(mt->ll_driver->open(mt), 0);
	fi = find_host(0, CMD_SEND_FIRMWARE);
	CHECK(fi >= 0);
	if (fi >= 0) {
		CHECK_EQ(fw.host[fi].len, 16);
		CHECK_EQ(fw.host[fi].data[1], 2);	/* type 2: firmware */
		CHECK_EQ(fw.host[fi].data[2], 0);
		CHECK_EQ(fw.host[fi].data[3], 1);	/* interface */
		CHECK_EQ(le32(fw.host[fi].data + 12), 4096);
	}
	CHECK_EQ(fw_requests, 1);
	/* the FIFO-era reset commands are still sent; macOS uses SMC functions (see README) */
	CHECK_EQ(count_host(0, CMD_RESET_INTERFACE), 2);
	CHECK_EQ(dma_allocs, 2);	/* ring + firmware */
}

int main(int argc, char **argv)
{
	if (argc > 1 && !strcmp(argv[1], "-v"))
		verbose = 1;
	setvbuf(stdout, NULL, _IONBF, 0);
	test_probe();
	test_handshake();
	test_enumeration_and_input(true, false);
	test_enumeration_and_input(false, false);
	test_enumeration_and_input(false, true);
	test_batched();
	test_errors();
	test_poll();
	test_fifo_mode();
	test_acks();
	test_enable_cmd_param();
	test_stm_fallback();
	test_inactive_without_descriptor();
	test_firmware_upload();
	free_tracked();
	printf("%d checks, %d failures\n", checks, failures);
	return failures ? 1 : 0;
}
