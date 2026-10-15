/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
/*
 * dchid_ring.h - M4/M5 MTP HID transport: shared-memory byte FIFO, message
 * framing and the three management commands the host sends to set it up.
 *
 * Original implementation written from our own static analysis of the macOS
 * 26.6.2 drivers on this Mac (see kernel/experiments/mtp-input/README.md).
 * It is portable on purpose: the kernel driver includes it as is, and
 * test_ring.c builds it in userspace against a synthetic firmware model.
 *
 * Evidence labels are in the README. In short:
 *   ring layout          Confirmed (decompiler + independent disassembly)
 *   framing, checksum    Confirmed (same)
 *   0xC1 / 0x91 / 0x95   Confirmed byte layouts
 *   doorbell contents    Unknown (only "any DockChannel RX, then drain" is known)
 */
#ifndef DCHID_RING_H
#define DCHID_RING_H

#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/string.h>
#include <linux/compiler.h>
#include <asm/barrier.h>
#define DCHID_RMB()	dma_rmb()
#define DCHID_WMB()	dma_wmb()
#define DCHID_MB()	dma_mb()
#define DCHID_LOAD32(p)	READ_ONCE(*(volatile u32 *)(p))
#define DCHID_STORE32(p, v) WRITE_ONCE(*(volatile u32 *)(p), (v))
#else
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
#define DCHID_RMB()	__atomic_thread_fence(__ATOMIC_ACQUIRE)
#define DCHID_WMB()	__atomic_thread_fence(__ATOMIC_RELEASE)
#define DCHID_MB()	__atomic_thread_fence(__ATOMIC_SEQ_CST)
#define DCHID_LOAD32(p)	__atomic_load_n((volatile u32 *)(p), __ATOMIC_RELAXED)
#define DCHID_STORE32(p, v) __atomic_store_n((volatile u32 *)(p), (v), __ATOMIC_RELAXED)
#endif

/* ------------------------------------------------------------------ framing */

#define DCHID_HDR_LEN		8	/* hdr_len byte may be 6..8 on the wire */
#define DCHID_SUBHDR_LEN	8
#define DCHID_CSUM_LEN		4
#define DCHID_MIN_MSG		12	/* header + checksum, empty body */

#define DCHID_TYPE_NONE		0x00	/* parsed and ignored (doorbell candidate) */
#define DCHID_TYPE_CMD		0x11	/* host->device command / device ack */
#define DCHID_TYPE_REPORT	0x12	/* device->host input report or event */

/* Errors for the incremental assembler, same numbering macOS uses internally. */
enum dchid_asm_status {
	DCHID_ASM_INCOMPLETE = 0,	/* need more bytes */
	DCHID_ASM_COMPLETE = 1,
	DCHID_ASM_E_HDR_LEN = 0xfc,	/* hdr_len > 8 */
	DCHID_ASM_E_TOO_BIG = 0xfd,	/* declared size exceeds the buffer */
	DCHID_ASM_E_OVERRUN = 0xfe,	/* more bytes than declared */
	DCHID_ASM_E_CHECKSUM = 0xff,
};

static inline u32 dchid_le32(const void *p)
{
	const u8 *b = p;

	return (u32)b[0] | (u32)b[1] << 8 | (u32)b[2] << 16 | (u32)b[3] << 24;
}

static inline u16 dchid_le16(const void *p)
{
	const u8 *b = p;

	return (u16)(b[0] | b[1] << 8);
}

static inline void dchid_put_le32(void *p, u32 v)
{
	u8 *b = p;

	b[0] = v; b[1] = v >> 8; b[2] = v >> 16; b[3] = v >> 24;
}

static inline void dchid_put_le16(void *p, u16 v)
{
	u8 *b = p;

	b[0] = v; b[1] = v >> 8;
}

static inline void dchid_put_le64(void *p, u64 v)
{
	dchid_put_le32(p, (u32)v);
	dchid_put_le32((u8 *)p + 4, (u32)(v >> 32));
}

/* checksum = ~sum of the little-endian u32 words of header+body (len % 4 == 0) */
static inline u32 dchid_frame_csum(const void *p, size_t len)
{
	const u8 *b = p;
	u32 sum = 0;

	for (size_t i = 0; i + 4 <= len; i += 4)
		sum += dchid_le32(b + i);
	return ~sum;
}

/*
 * Incremental message assembler. The caller owns @buf (capacity @cap) and feeds
 * it exactly dchid_asm_need() bytes at a time; that is how the device side is
 * read from both the DockChannel FIFO and the ring, so a message is never split
 * across, or merged with, its neighbour.
 */
struct dchid_asm {
	u8 *buf;
	size_t cap;
	size_t have;
};

static inline void dchid_asm_reset(struct dchid_asm *a)
{
	a->have = 0;
}

/* Total message size once the length field is known (0 if it is not yet). */
static inline size_t dchid_asm_total(const struct dchid_asm *a)
{
	if (a->have < 6)
		return 0;
	return (size_t)a->buf[0] + dchid_le16(a->buf + 2) + DCHID_CSUM_LEN;
}

/* Bytes to read next: 12 first (smallest possible message), then the rest. */
static inline size_t dchid_asm_need(const struct dchid_asm *a)
{
	size_t total;

	if (a->have < DCHID_MIN_MSG)
		return DCHID_MIN_MSG - a->have;
	total = dchid_asm_total(a);
	return total > a->have ? total - a->have : 0;
}

/* Call after appending @n bytes at buf + have (caller already advanced have). */
static inline enum dchid_asm_status dchid_asm_check(const struct dchid_asm *a)
{
	size_t total;

	if (a->have < 6)
		return DCHID_ASM_INCOMPLETE;
	if (a->buf[0] > DCHID_HDR_LEN || a->buf[0] < 6)
		return DCHID_ASM_E_HDR_LEN;
	total = dchid_asm_total(a);
	if (total > a->cap)
		return DCHID_ASM_E_TOO_BIG;
	if (a->have < DCHID_MIN_MSG || a->have < total)
		return DCHID_ASM_INCOMPLETE;
	if (a->have > total)
		return DCHID_ASM_E_OVERRUN;
	if (dchid_le32(a->buf + total - DCHID_CSUM_LEN) !=
	    dchid_frame_csum(a->buf, total - DCHID_CSUM_LEN))
		return DCHID_ASM_E_CHECKSUM;
	return DCHID_ASM_COMPLETE;
}

/* Accessors, valid only after DCHID_ASM_COMPLETE. */
static inline u8 dchid_msg_type(const u8 *m)    { return m[1]; }
static inline u8 dchid_msg_seq(const u8 *m)     { return m[4]; }
static inline u8 dchid_msg_iface(const u8 *m)   { return m[5]; }
static inline u8 dchid_msg_status(const u8 *m)  { return m[7]; }
static inline const u8 *dchid_msg_app(const u8 *m) { return m + m[0]; }
static inline u16 dchid_msg_payload_len(const u8 *m) { return dchid_le16(dchid_msg_app(m) + 2); }
static inline const u8 *dchid_msg_payload(const u8 *m) { return dchid_msg_app(m) + DCHID_SUBHDR_LEN; }

/*
 * Build a host->device message (type 0x11, hdr_len 8). Returns the total size
 * or 0 if @cap is too small. flags = (report group << 6) | request.
 */
static inline size_t dchid_build_cmd(u8 *out, size_t cap, u8 seq, u8 iface, u8 flags,
				     const void *payload, u16 len)
{
	size_t body = ((size_t)len + DCHID_SUBHDR_LEN + 3) & ~(size_t)3;
	size_t total = DCHID_HDR_LEN + body + DCHID_CSUM_LEN;

	if (total > cap)
		return 0;
	memset(out, 0, total);
	out[0] = DCHID_HDR_LEN;
	out[1] = DCHID_TYPE_CMD;
	dchid_put_le16(out + 2, (u16)body);
	out[4] = seq;
	out[5] = iface;
	out[DCHID_HDR_LEN] = flags;
	dchid_put_le16(out + DCHID_HDR_LEN + 2, len);
	if (len)
		memcpy(out + DCHID_HDR_LEN + DCHID_SUBHDR_LEN, payload, len);
	dchid_put_le32(out + DCHID_HDR_LEN + body, dchid_frame_csum(out, DCHID_HDR_LEN + body));
	return total;
}

/* ---------------------------------------------------------------- ring FIFO */

/*
 * One shared-memory byte FIFO: u32 write index, u32 read index, then data.
 * The device produces; the host consumes. Indices are byte offsets into data.
 */
#define DCHID_RING_HDR		8
#define DCHID_RING_MIN		(DCHID_RING_HDR + 1)

struct dchid_ring {
	u8 *mem;		/* start of the shared buffer (the u32 pair) */
	u32 size;		/* total size, header included */
	u32 cap;		/* size - 8 */
	u32 errors;		/* corrupted-index events seen */
};

static inline int dchid_ring_init(struct dchid_ring *r, void *mem, size_t size)
{
	if (!mem || size < DCHID_RING_MIN || size > 0xffffffffu)
		return -1;
	r->mem = mem;
	r->size = (u32)size;
	r->cap = (u32)size - DCHID_RING_HDR;
	r->errors = 0;
	return 0;
}

static inline void dchid_ring_reset(struct dchid_ring *r)
{
	DCHID_STORE32(r->mem, 0);
	DCHID_STORE32(r->mem + 4, 0);
	DCHID_WMB();
}

static inline u8 *dchid_ring_data(const struct dchid_ring *r)
{
	return r->mem + DCHID_RING_HDR;
}

/*
 * Bytes available to the host (consumer). Sets *wr and *rd. Returns -1 if
 * either index is outside the data area: the device wrote nonsense, and the
 * caller must stop trusting this ring until it is reset.
 */
static inline long dchid_ring_consumer_avail(struct dchid_ring *r, u32 *wr, u32 *rd)
{
	u32 w = DCHID_LOAD32(r->mem);
	u32 rr = DCHID_LOAD32(r->mem + 4);

	if (w >= r->cap || rr >= r->cap) {
		r->errors++;
		return -1;
	}
	*wr = w;
	*rd = rr;
	return w >= rr ? (long)(w - rr) : (long)r->cap - (long)rr + (long)w;
}

/* Copy up to @want bytes out and advance the read index. Returns bytes copied. */
static inline long dchid_ring_read(struct dchid_ring *r, void *dst, size_t want)
{
	u32 wr, rd, first, n;
	long avail = dchid_ring_consumer_avail(r, &wr, &rd);
	u8 *data = dchid_ring_data(r);

	if (avail < 0)
		return -1;
	n = (u32)((size_t)avail < want ? (size_t)avail : want);
	if (!n)
		return 0;
	DCHID_RMB();			/* index load before data loads */
	first = r->cap - rd;
	if (first > n)
		first = n;
	memcpy(dst, data + rd, first);
	if (n > first)
		memcpy((u8 *)dst + first, data, n - first);
	rd = (u32)(((u64)rd + n) % r->cap);
	DCHID_MB();			/* data loads before the index release (load->store) */
	DCHID_STORE32(r->mem + 4, rd);
	return n;
}

/* Producer side. Used by the test firmware model and by any future host ring. */
static inline long dchid_ring_producer_free(struct dchid_ring *r, u32 *wr, u32 *rd)
{
	u32 w = DCHID_LOAD32(r->mem);
	u32 rr = DCHID_LOAD32(r->mem + 4);

	if (w >= r->cap || rr >= r->cap)
		return -1;
	*wr = w;
	*rd = rr;
	/* one byte is always left unused so that wr == rd means empty */
	return rr > w ? (long)(rr - w - 1) : (long)r->cap - (long)w + (long)rr - 1;
}

static inline long dchid_ring_write(struct dchid_ring *r, const void *src, size_t len)
{
	u32 wr, rd, first;
	long room = dchid_ring_producer_free(r, &wr, &rd);
	u8 *data = dchid_ring_data(r);

	if (room < 0 || (size_t)room < len)
		return -1;
	first = r->cap - wr;
	if (first > len)
		first = (u32)len;
	memcpy(data + wr, src, first);
	if (len > first)
		memcpy(data, (const u8 *)src + first, len - first);
	wr = (u32)(((u64)wr + len) % r->cap);
	DCHID_WMB();
	DCHID_STORE32(r->mem, wr);
	return (long)len;
}

/* --------------------------------------------------------- management cmds */

#define DCHID_CMD_AWAKE		0xc1	/* {0xc1, state}  state 2 = awake, 1 = not */
#define DCHID_CMD_FIFO		0x91	/* register a device->host ring */
#define DCHID_CMD_SHMEM		0x95	/* register a typed shared buffer */

#define DCHID_AWAKE_ASLEEP	1
#define DCHID_AWAKE_AWAKE	2
#define DCHID_SHMEM_FIRMWARE	2	/* firmware image (as in the FIFO-era driver) */
#define DCHID_SHMEM_REPORT	3	/* large-report staging buffer */

#define DCHID_CMD_AWAKE_LEN	2
#define DCHID_CMD_FIFO_LEN	15
#define DCHID_CMD_SHMEM_LEN	16

static inline size_t dchid_enc_awake(u8 out[DCHID_CMD_AWAKE_LEN], int awake)
{
	out[0] = DCHID_CMD_AWAKE;
	out[1] = awake ? DCHID_AWAKE_AWAKE : DCHID_AWAKE_ASLEEP;
	return DCHID_CMD_AWAKE_LEN;
}

/* {0x91, 0, 0, u64 iova @3 (unaligned), u32 total size @11}; size includes the 8-byte header */
static inline size_t dchid_enc_register_fifo(u8 out[DCHID_CMD_FIFO_LEN], u64 iova, u32 total_size)
{
	out[0] = DCHID_CMD_FIFO;
	out[1] = 0;
	out[2] = 0;
	dchid_put_le64(out + 3, iova);
	dchid_put_le32(out + 11, total_size);
	return DCHID_CMD_FIFO_LEN;
}

/* {0x95, type, 0, iface, u64 iova @4, u32 size @12} */
static inline size_t dchid_enc_register_shmem(u8 out[DCHID_CMD_SHMEM_LEN], u8 type, u8 iface,
					      u64 iova, u32 size)
{
	out[0] = DCHID_CMD_SHMEM;
	out[1] = type;
	out[2] = 0;
	out[3] = iface;
	dchid_put_le64(out + 4, iova);
	dchid_put_le32(out + 12, size);
	return DCHID_CMD_SHMEM_LEN;
}

/* ---------------------------------------------------------- init descriptor */

/* Management event ids (device -> host on interface 0) */
#define DCHID_EV_CONFIG_REQ	0xa0
#define DCHID_EV_RESET_REQ	0xa2
#define DCHID_EV_DUMP_REQ	0xa3
#define DCHID_EV_DUMP_RSP	0xa4
#define DCHID_EV_FUNC_REQ	0xb5
#define DCHID_EV_INIT		0xf0
#define DCHID_EV_READY		0xf1
#define DCHID_EV_WAKE		0xf2

/* TLV block types inside an INIT event */
#define DCHID_BLK_HID_DESC	0
#define DCHID_BLK_CONFIG	1
#define DCHID_BLK_TRANSPORT	2
#define DCHID_BLK_SERIAL	3
#define DCHID_BLK_READY		4
#define DCHID_BLK_IFACES	5
#define DCHID_BLK_LOCATION	6
#define DCHID_BLK_PRODUCT	7

#define DCHID_INIT_HDR_LEN	22

struct dchid_init_block {
	u16 type;
	u16 len;
	const u8 *data;
};

/*
 * Walk the TLV blocks of an INIT payload (after the 22-byte header). Returns
 * the number of bytes consumed or -1 on a truncated or oversized block.
 * *pos is advanced block by block; call until it returns 0.
 */
static inline int dchid_init_next(const u8 *payload, size_t len, size_t *pos,
				  struct dchid_init_block *blk)
{
	size_t p = *pos;

	if (p >= len)
		return 0;
	if (len - p < 4)
		return -1;
	blk->type = dchid_le16(payload + p);
	blk->len = dchid_le16(payload + p + 2);
	if (blk->len > 0x7ff || len - p - 4 < blk->len)
		return -1;
	blk->data = payload + p + 4;
	*pos = p + 4 + blk->len;
	return 1;
}

#endif /* DCHID_RING_H */
