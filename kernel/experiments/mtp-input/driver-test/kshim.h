/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
/*
 * kshim.h - the few kernel APIs dockchannel-hid.c uses, as declarations.
 *
 * Force-included (-include) when the patched driver is syntax-checked or
 * built into the userspace behaviour harness. It is a stand-in written from
 * the public kernel API, nothing more: it cannot prove the driver builds in a
 * real kernel (the VM job does that), it catches typos, use-before-declaration,
 * wrong member names and wrong argument counts in our own code.
 */
#ifndef KSHIM_H
#define KSHIM_H
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#define __KERNEL__ 1
#define IS_ENABLED(x) 1
#define __packed __attribute__((packed))
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64;
typedef uint8_t __u8; typedef uint16_t __u16; typedef uint32_t __u32;
typedef long ssize_t;
typedef uint64_t dma_addr_t;
typedef struct { int counter; } atomic_t;
typedef unsigned gfp_t;
#define GFP_KERNEL 0
#define PAGE_SIZE 16384UL
#define SZ_16K 0x4000
#define SZ_16M 0x1000000
#define EINVAL 22
#define ENOMEM 12
#define EIO 5
#define ETIMEDOUT 110
#define EBUSY 16
#define EINPROGRESS 115
#define EPROBE_DEFER 517
#define BIT(n) (1UL << (n))
#define GENMASK(h, l) (((~0UL) << (l)) & (~0UL >> (63 - (h))))
#define FIELD_PREP(m, v) ((((unsigned long)(v)) << __builtin_ctzl(m)) & (m))
#define FIELD_GET(m, v) ((((unsigned long)(v)) & (m)) >> __builtin_ctzl(m))
#define round_up(x, y) ((((x) + (y) - 1) / (y)) * (y))
#define round_down(x, y) (((x) / (y)) * (y))
#define min(a, b) ({ __typeof__(a) _a = (a); __typeof__(b) _b = (b); (void)(&_a == &_b); _a < _b ? _a : _b; })
#define min_t(t, a, b) ({ t _a = (a); t _b = (b); _a < _b ? _a : _b; })
#define clamp_t(t, v, lo, hi) ({ t _v = (v), _lo = (lo), _hi = (hi); _v < _lo ? _lo : (_v > _hi ? _hi : _v); })
#define container_of(p, T, m) ((T *)((char *)(p) - offsetof(T, m)))
#define WARN_ON(x) ({ int __w = !!(x); __w; })
#define WARN_ON_ONCE(x) ({ int __w = !!(x); __w; })
#define BUG_ON(x) do { if (x) __builtin_trap(); } while (0)
#define IS_ERR(p) ((unsigned long)(p) >= (unsigned long)-4095)
#define IS_ERR_OR_NULL(p) (!(p) || IS_ERR(p))
static inline long PTR_ERR(const void *p) { return (long)p; }
static inline void *ERR_PTR(long e) { return (void *)e; }
#define READ_ONCE(x) (*(volatile __typeof__(x) *)&(x))
#define WRITE_ONCE(x, v) (*(volatile __typeof__(x) *)&(x) = (v))
#define dma_rmb() __atomic_thread_fence(__ATOMIC_ACQUIRE)
#define dma_wmb() __atomic_thread_fence(__ATOMIC_RELEASE)
#define dma_mb() __atomic_thread_fence(__ATOMIC_SEQ_CST)
#define wmb() __atomic_thread_fence(__ATOMIC_RELEASE)

static inline u16 get_unaligned_le16(const void *p) { u16 v; memcpy(&v, p, 2); return v; }
static inline u32 get_unaligned_le32(const void *p) { u32 v; memcpy(&v, p, 4); return v; }

/* devices and device tree */
struct fwnode_handle { int x; };
struct property { const char *name; struct property *next; };
struct device_node {
	const char *name;		/* shim extension: lets the harness answer of_get_child_by_name() */
	const char *firmware_name;	/* shim extension: answers "firmware-name" */
	struct device_node *child, *sibling;
	struct property *properties;
	struct fwnode_handle fwnode;
};
struct of_device_id { char compatible[128]; const void *data; };
struct device_driver { const char *name; const struct of_device_id *of_match_table; };
struct device;
struct device_link { struct device *supplier; struct device *consumer; };
struct device {
	struct device *parent;
	struct device_node *of_node;
	struct { int status; } links;
	struct fwnode_handle fwnode;
};
struct device_attribute { int x; };
struct platform_device { struct device dev; };
struct platform_driver {
	int (*probe)(struct platform_device *);
	void (*remove)(struct platform_device *);
	struct device_driver driver;
};
#define DL_FLAG_AUTOREMOVE_CONSUMER 2
#define DL_DEV_DRIVER_BOUND 3
extern struct device_link *device_link_add(struct device *c, struct device *s, u32 flags);
extern void put_device(struct device *d);
extern struct platform_device *of_find_device_by_node(struct device_node *np);
extern struct device_node *of_parse_phandle(const struct device_node *np, const char *name, int idx);
extern void of_node_put(struct device_node *np);
extern struct device_node *of_get_child_by_name(const struct device_node *np, const char *name);
extern int of_property_read_u32(const struct device_node *np, const char *name, u32 *out);
extern int of_property_read_string(const struct device_node *np, const char *name, const char **out);
extern const void *device_get_match_data(const struct device *dev);
extern int dma_set_mask_and_coherent(struct device *dev, u64 mask);
#define DMA_BIT_MASK(n) (((n) == 64) ? ~0ULL : ((1ULL << ((n) & 63)) - 1))
extern void *dmam_alloc_coherent(struct device *dev, size_t size, dma_addr_t *h, gfp_t gfp);
extern void *devm_kzalloc(struct device *dev, size_t size, gfp_t gfp);
extern void *devm_kmalloc(struct device *dev, size_t size, gfp_t gfp);
extern char *devm_kstrdup(struct device *dev, const char *s, gfp_t gfp);
extern void *devm_kmemdup(struct device *dev, const void *src, size_t len, gfp_t gfp);
extern void *kzalloc(size_t size, gfp_t gfp);
extern void kfree(const void *p);
extern const char *dev_name(const struct device *dev);
extern int device_create_file(struct device *dev, const struct device_attribute *attr);
extern void device_remove_file(struct device *dev, const struct device_attribute *attr);
#define DEVICE_ATTR_RO(n) struct device_attribute dev_attr_##n = { 0 }
#define for_each_child_of_node(parent, ch) for (ch = (parent)->child; ch; ch = ch->sibling)
#define for_each_property_of_node(dn, pp) for (pp = (dn)->properties; pp; pp = pp->next)

/* printk family: no format attribute on purpose (kernel-only %pad / %*ph) */
#define KSHIM_ERR 3
#define KSHIM_WARN 4
#define KSHIM_INFO 6
#define KSHIM_DBG 7
extern void __kshim_log(int level, const struct device *d, const char *fmt, ...);
#define dev_err(d, ...) __kshim_log(KSHIM_ERR, d, __VA_ARGS__)
#define dev_warn(d, ...) __kshim_log(KSHIM_WARN, d, __VA_ARGS__)
#define dev_info(d, ...) __kshim_log(KSHIM_INFO, d, __VA_ARGS__)
#define dev_dbg(d, ...) __kshim_log(KSHIM_DBG, d, __VA_ARGS__)
#define dev_err_ratelimited(d, ...) __kshim_log(KSHIM_ERR, d, __VA_ARGS__)
#define dev_warn_ratelimited(d, ...) __kshim_log(KSHIM_WARN, d, __VA_ARGS__)
#define dev_info_ratelimited(d, ...) __kshim_log(KSHIM_INFO, d, __VA_ARGS__)
#define dev_dbg_ratelimited(d, ...) __kshim_log(KSHIM_DBG, d, __VA_ARGS__)
extern int scnprintf(char *buf, size_t size, const char *fmt, ...);
extern ssize_t strscpy(char *dst, const char *src, size_t n);

/* synchronisation and deferred work */
struct mutex { int locked; };
extern void mutex_init(struct mutex *m);
extern void mutex_lock(struct mutex *m);
extern void mutex_unlock(struct mutex *m);
struct completion { int done; };
extern void init_completion(struct completion *c);
extern void reinit_completion(struct completion *c);
extern void complete(struct completion *c);
extern void complete_all(struct completion *c);
extern bool completion_done(struct completion *c);
extern unsigned long wait_for_completion_timeout(struct completion *c, unsigned long t);
extern unsigned long msecs_to_jiffies(unsigned int ms);
extern void msleep(unsigned int ms);
extern int atomic_xchg(atomic_t *a, int v);
struct work_struct { void (*func)(struct work_struct *); int pending; void *wq; /* shim extension */ };
struct delayed_work { struct work_struct work; };
struct workqueue_struct;
#define WQ_MEM_RECLAIM 8
extern struct workqueue_struct *alloc_ordered_workqueue(const char *fmt, unsigned flags, ...);
extern struct workqueue_struct *alloc_workqueue(const char *fmt, unsigned flags, int max, ...);
#define INIT_WORK(w, f) do { (w)->func = (f); (w)->pending = 0; } while (0)
#define INIT_DELAYED_WORK(w, f) INIT_WORK(&(w)->work, f)
#define to_delayed_work(w) container_of(w, struct delayed_work, work)
extern bool queue_work(struct workqueue_struct *wq, struct work_struct *w);
extern bool schedule_delayed_work(struct delayed_work *w, unsigned long delay);
extern bool cancel_delayed_work(struct delayed_work *w);

/* gpio */
struct gpio_desc;
enum gpiod_flags { GPIOD_ASIS = 0, GPIOD_OUT_LOW = 1 };
extern struct gpio_desc *fwnode_gpiod_get_index(struct fwnode_handle *fw, const char *con, int idx,
						enum gpiod_flags f, const char *label);
extern struct gpio_desc *devm_gpiod_get_index(struct device *dev, const char *con, unsigned idx,
					      enum gpiod_flags f);
extern void gpiod_put(struct gpio_desc *d);
extern void gpiod_set_value_cansleep(struct gpio_desc *d, int v);

/* firmware */
struct firmware { size_t size; const u8 *data; };
extern int request_firmware(const struct firmware **fw, const char *name, struct device *dev);
extern void release_firmware(const struct firmware *fw);

/* hid */
#define HID_INPUT_REPORT 0
#define HID_OUTPUT_REPORT 1
#define HID_FEATURE_REPORT 2
#define HID_REQ_GET_REPORT 0x01
#define HID_REQ_SET_REPORT 0x09
#define BUS_HOST 0x19
enum hid_type { HID_TYPE_OTHER = 0, HID_TYPE_SPI_KEYBOARD = 8, HID_TYPE_SPI_MOUSE = 9 };
struct hid_device;
struct hid_ll_driver {
	int (*start)(struct hid_device *);
	void (*stop)(struct hid_device *);
	int (*open)(struct hid_device *);
	void (*close)(struct hid_device *);
	int (*parse)(struct hid_device *);
	int (*raw_request)(struct hid_device *, unsigned char, __u8 *, size_t, unsigned char, int);
};
struct hid_device {
	struct device dev;
	char name[128], phys[64], uniq[64];
	const struct hid_ll_driver *ll_driver;
	u16 bus; u32 vendor, product, version, country;
	enum hid_type type;
	void *driver_data;
};
#define to_hid_device(d) container_of(d, struct hid_device, dev)
extern struct hid_device *hid_allocate_device(void);
extern int hid_add_device(struct hid_device *h);
extern void hid_destroy_device(struct hid_device *h);
extern int hid_parse_report(struct hid_device *h, __u8 *start, unsigned size);
extern int hid_input_report(struct hid_device *h, int type, u8 *data, u32 size, int interrupt);

/* DockChannel client API (include/linux/soc/apple/dockchannel.h in the pinned tree) */
struct dockchannel;
extern struct dockchannel *dockchannel_init(struct platform_device *pdev);
extern int dockchannel_send(struct dockchannel *dockchannel, const void *buf, size_t count);
extern int dockchannel_recv(struct dockchannel *dockchannel, void *buf, size_t count);
extern int dockchannel_await(struct dockchannel *dockchannel,
			     void (*callback)(void *cookie, size_t avail),
			     void *cookie, size_t count);

/* module glue */
#define module_param(a, b, c)
#define MODULE_PARM_DESC(a, b)
#define MODULE_DEVICE_TABLE(a, b)
#define MODULE_FIRMWARE(a)
#define MODULE_DESCRIPTION(a)
#define MODULE_AUTHOR(a)
#define MODULE_LICENSE(a)
#define module_platform_driver(d) static void *__keep_##d __attribute__((unused)) = &(d)
#endif
