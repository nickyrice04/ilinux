// SPDX-License-Identifier: MIT
/*
 * Userspace tests for dchid_ring.h against a synthetic MTP firmware model.
 * No Apple code or data is used: every layout below is the one the header
 * documents, and the expected bytes are written out by hand.
 *
 *   cc -std=c11 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
 *      test_ring.c -o test_ring && ./test_ring
 */
#include <stdio.h>
#include <stdlib.h>

#include "dchid_ring.h"

static int failures, checks;

#define CHECK(cond)                                                              \
	do {                                                                     \
		checks++;                                                        \
		if (!(cond)) {                                                   \
			failures++;                                              \
			fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
		}                                                                \
	} while (0)

static u64 rng_state = 0x9e3779b97f4a7c15ull;

static u32 rnd(void)
{
	rng_state ^= rng_state << 13;
	rng_state ^= rng_state >> 7;
	rng_state ^= rng_state << 17;
	return (u32)(rng_state >> 16);
}

/* ---------------------------------------------------------------- known answers */

static void test_encoders(void)
{
	u8 b[DCHID_CMD_SHMEM_LEN];
	static const u8 awake[] = {0xc1, 0x02};
	static const u8 asleep[] = {0xc1, 0x01};
	/* iova 0x1_0002_8000, size 0x200000 */
	static const u8 fifo[] = {0x91, 0x00, 0x00, 0x00, 0x80, 0x02, 0x00, 0x01,
				  0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00};
	/* type 2, iface 1, iova 0x100_0004_0000, size 0x00012345 */
	static const u8 shmem[] = {0x95, 0x02, 0x00, 0x01, 0x00, 0x00, 0x04, 0x00,
				   0x00, 0x01, 0x00, 0x00, 0x45, 0x23, 0x01, 0x00};

	CHECK(dchid_enc_awake(b, 1) == 2 && !memcmp(b, awake, 2));
	CHECK(dchid_enc_awake(b, 0) == 2 && !memcmp(b, asleep, 2));
	CHECK(dchid_enc_register_fifo(b, 0x100028000ull, 0x200000) == 15 && !memcmp(b, fifo, 15));
	CHECK(dchid_enc_register_shmem(b, DCHID_SHMEM_FIRMWARE, 1, 0x10000040000ull, 0x12345) == 16 &&
	      !memcmp(b, shmem, 16));
}

static void test_build_and_parse(void)
{
	/* SET_REPORT feature (group 2 -> flags 0x80) of {0xc1, 0x02} on iface 0, seq 7 */
	static const u8 payload[] = {0xc1, 0x02};
	u8 m[64];
	size_t n = dchid_build_cmd(m, sizeof(m), 7, 0, 0x80, payload, 2);
	/* header 8 + subheader 8 + payload padded to 4 (2 -> 4) + checksum 4 */
	CHECK(n == 8 + 12 + 4);
	CHECK(m[0] == 8 && m[1] == 0x11 && dchid_le16(m + 2) == 12 && m[4] == 7 && m[5] == 0);
	CHECK(m[8] == 0x80 && dchid_le16(m + 10) == 2 && m[16] == 0xc1 && m[17] == 0x02);
	CHECK(dchid_le32(m + 20) == dchid_frame_csum(m, 20));
	/* the checksum is the complement: sum of all words incl. checksum == 0xffffffff */
	u32 sum = 0;
	for (size_t i = 0; i < n; i += 4)
		sum += dchid_le32(m + i);
	CHECK(sum == 0xffffffffu);

	struct dchid_asm a = {.buf = m, .cap = sizeof(m), .have = 0};
	size_t fed = 0;
	while (dchid_asm_check(&a) == DCHID_ASM_INCOMPLETE) {
		size_t need = dchid_asm_need(&a);
		CHECK(need > 0 && fed + need <= n);
		a.have += need;
		fed += need;
	}
	CHECK(dchid_asm_check(&a) == DCHID_ASM_COMPLETE && fed == n);
	CHECK(dchid_msg_payload_len(m) == 2 && dchid_msg_payload(m)[0] == 0xc1);

	CHECK(dchid_build_cmd(m, 16, 0, 0, 0, payload, 2) == 0);	/* too small */
}

static void test_smallest_message(void)
{
	/* an empty message: 8-byte header + checksum = 12 bytes, type 0 */
	u8 m[12] = {8, 0, 0, 0, 3, 0, 0, 0};
	dchid_put_le32(m + 8, dchid_frame_csum(m, 8));
	struct dchid_asm a = {.buf = m, .cap = sizeof(m), .have = 0};

	CHECK(dchid_asm_need(&a) == 12);
	a.have = 12;
	CHECK(dchid_asm_check(&a) == DCHID_ASM_COMPLETE);
	CHECK(dchid_msg_type(m) == DCHID_TYPE_NONE && dchid_msg_seq(m) == 3);
}

static void test_assembler_errors(void)
{
	u8 m[64];
	struct dchid_asm a = {.buf = m, .cap = 32, .have = 0};
	static const u8 p[] = {1, 2, 3, 4, 5, 6, 7, 8};
	size_t n = dchid_build_cmd(m, sizeof(m), 1, 2, 0x40, p, 8);

	a.have = n;
	a.cap = sizeof(m);
	CHECK(dchid_asm_check(&a) == DCHID_ASM_COMPLETE);

	m[n - 1] ^= 0x10;					/* corrupt checksum */
	CHECK(dchid_asm_check(&a) == DCHID_ASM_E_CHECKSUM);
	m[n - 1] ^= 0x10;

	a.cap = n - 4;						/* buffer smaller than declared size */
	CHECK(dchid_asm_check(&a) == DCHID_ASM_E_TOO_BIG);
	a.cap = sizeof(m);

	m[0] = 9;						/* hdr_len beyond 8 */
	CHECK(dchid_asm_check(&a) == DCHID_ASM_E_HDR_LEN);
	m[0] = 5;
	CHECK(dchid_asm_check(&a) == DCHID_ASM_E_HDR_LEN);
	m[0] = 8;

	a.have = n + 4;						/* more bytes than declared */
	CHECK(dchid_asm_check(&a) == DCHID_ASM_E_OVERRUN);
	a.have = 5;
	CHECK(dchid_asm_check(&a) == DCHID_ASM_INCOMPLETE);
}

/* ---------------------------------------------------------------------- ring */

static void test_ring_basics(void)
{
	u8 mem[8 + 16] = {0};
	struct dchid_ring r;
	u8 out[32];

	CHECK(dchid_ring_init(&r, mem, 8) < 0);			/* no data area */
	CHECK(dchid_ring_init(&r, mem, sizeof(mem)) == 0 && r.cap == 16);
	CHECK(dchid_ring_read(&r, out, 4) == 0);		/* empty */

	CHECK(dchid_ring_write(&r, "abcdefgh", 8) == 8);
	CHECK(dchid_ring_read(&r, out, 3) == 3 && !memcmp(out, "abc", 3));
	CHECK(dchid_ring_write(&r, "ijklmnopq", 9) == 9);	/* wraps: 5 + 9 = 14 <= 15 */
	CHECK(dchid_ring_write(&r, "XX", 2) < 0);		/* only 1 free (cap-1 rule) */
	CHECK(dchid_ring_read(&r, out, 32) == 14 && !memcmp(out, "defghijklmnopq", 14));
	CHECK(dchid_ring_read(&r, out, 1) == 0);

	/* exactly cap-1 bytes fit, one more does not */
	u8 big[16];
	memset(big, 0x5a, sizeof(big));
	CHECK(dchid_ring_write(&r, big, 15) == 15);
	CHECK(dchid_ring_write(&r, big, 1) < 0);
	CHECK(dchid_ring_read(&r, out, 15) == 15);

	/* corrupted indices are refused and counted, never dereferenced */
	dchid_put_le32(mem, 0x1000);
	CHECK(dchid_ring_read(&r, out, 1) < 0 && r.errors == 1);
	dchid_put_le32(mem, 0);
	dchid_put_le32(mem + 4, 16);
	CHECK(dchid_ring_read(&r, out, 1) < 0 && r.errors == 2);
	dchid_ring_reset(&r);
	CHECK(dchid_le32(mem) == 0 && dchid_le32(mem + 4) == 0);
}

/* Model-based: random producer/consumer sizes against a plain FIFO model. */
static void test_ring_model(void)
{
	enum { CAP = 61, ITER = 20000 };
	u8 mem[8 + CAP];
	struct dchid_ring r;
	u8 model[1 << 16];
	size_t mhead = 0, mtail = 0;
	u8 tmp[128], got[128];

	memset(mem, 0, sizeof(mem));
	CHECK(dchid_ring_init(&r, mem, sizeof(mem)) == 0);
	for (int i = 0; i < ITER; i++) {
		if (rnd() & 1) {
			size_t len = rnd() % 40;
			for (size_t k = 0; k < len; k++)
				tmp[k] = (u8)rnd();
			size_t used = mtail - mhead;
			long rc = dchid_ring_write(&r, tmp, len);
			if (used + len <= CAP - 1) {
				CHECK(rc == (long)len);
				memcpy(model + mtail, tmp, len);
				mtail += len;
			} else {
				CHECK(rc < 0);
			}
		} else {
			size_t want = rnd() % 50;
			size_t used = mtail - mhead;
			size_t expect = want < used ? want : used;
			long rc = dchid_ring_read(&r, got, want);
			CHECK(rc == (long)expect);
			if (rc > 0)
				CHECK(!memcmp(got, model + mhead, (size_t)rc));
			mhead += expect;
		}
		if (mhead > (1 << 15)) {		/* compact the model */
			memmove(model, model + mhead, mtail - mhead);
			mtail -= mhead;
			mhead = 0;
		}
	}
}

/* --------------------------------------------------- firmware model end to end */

struct fw_msg {
	u8 type, seq, iface, flags;
	u16 len;
	u8 body[1800];
};

/* Build a device->host message (type 0x12) like the firmware would. */
static size_t fw_emit(u8 *out, size_t cap, const struct fw_msg *m)
{
	size_t n = dchid_build_cmd(out, cap, m->seq, m->iface, m->flags, m->body, m->len);

	if (n) {
		out[1] = m->type;
		/* checksum covers the header: recompute after changing the type byte */
		size_t body = n - DCHID_HDR_LEN - DCHID_CSUM_LEN;
		dchid_put_le32(out + DCHID_HDR_LEN + body, dchid_frame_csum(out, DCHID_HDR_LEN + body));
	}
	return n;
}

static void test_end_to_end(void)
{
	enum { RING = 8 + 4096, NMSG = 600 };
	static u8 mem[RING];
	static u8 wire[NMSG][2048];
	static size_t wire_len[NMSG];
	struct dchid_ring r;
	struct fw_msg *m = malloc(sizeof(*m));
	u8 asm_buf[4096];
	struct dchid_asm a = {.buf = asm_buf, .cap = sizeof(asm_buf), .have = 0};
	int produced = 0, consumed = 0, doorbells = 0, errors = 0;
	long spins = 0;

	CHECK(m != NULL);
	CHECK(dchid_ring_init(&r, mem, RING) == 0);
	for (int i = 0; i < NMSG; i++) {
		memset(m, 0, sizeof(*m));
		switch (rnd() % 4) {
		case 0:		/* keyboard: report id 1 + 8 bytes */
			m->type = DCHID_TYPE_REPORT; m->iface = 2; m->len = 9;
			m->body[0] = 1;
			break;
		case 1:		/* multi-touch frame: ~1.7 KiB, report id 0x44 */
			m->type = DCHID_TYPE_REPORT; m->iface = 1;
			m->len = (u16)(1 + 1751 - (int)(rnd() % 400));
			m->body[0] = 0x44;
			break;
		case 2:		/* command ack on the management interface */
			m->type = DCHID_TYPE_CMD; m->iface = 0; m->flags = 0x80; m->len = 2;
			m->body[0] = 0x91;
			break;
		default:	/* empty doorbell-style message */
			m->type = DCHID_TYPE_NONE; m->iface = 0; m->len = 0;
			break;
		}
		m->seq = (u8)i;
		for (u16 k = 1; k < m->len; k++)
			m->body[k] = (u8)(rnd() ^ i);
		wire_len[i] = fw_emit(wire[i], sizeof(wire[i]), m);
		CHECK(wire_len[i] != 0);
	}

	/* The firmware writes whenever there is room; the host drains per doorbell. */
	while (consumed < NMSG) {
		if (++spins > 200000) {		/* a stuck ring must fail, not hang */
			CHECK(!"end-to-end made no progress");
			break;
		}
		while (produced < NMSG && (rnd() % 3)) {
			if (dchid_ring_write(&r, wire[produced], wire_len[produced]) < 0)
				break;
			produced++;
			doorbells++;
		}
		/* drain: read exactly what the assembler asks for, never more */
		for (int drain = 0; drain < 10000; drain++) {
			size_t need = dchid_asm_need(&a);
			long got;

			if (!need)
				need = 1;
			got = dchid_ring_read(&r, a.buf + a.have, need);
			if (got <= 0)
				break;
			a.have += (size_t)got;
			enum dchid_asm_status st = dchid_asm_check(&a);
			if (st == DCHID_ASM_COMPLETE) {
				CHECK(a.have == wire_len[consumed]);
				CHECK(!memcmp(a.buf, wire[consumed], a.have));
				consumed++;
				dchid_asm_reset(&a);
				if (consumed == NMSG)
					break;
			} else if (st != DCHID_ASM_INCOMPLETE) {
				errors++;
				dchid_asm_reset(&a);
			}
		}
	}
	CHECK(errors == 0 && consumed == NMSG && produced == NMSG && doorbells == NMSG);
	CHECK(spins <= 200000);
	CHECK(r.errors == 0);
	free(m);
}

/* ------------------------------------------------------------- init blocks */

static void test_init_blocks(void)
{
	u8 p[64];
	size_t n = 0, pos = 0;
	struct dchid_init_block b;

	/* HID descriptor (3 bytes), transport (6 bytes), product string "kbd\0" */
	dchid_put_le16(p + n, 0); dchid_put_le16(p + n + 2, 3); n += 4;
	p[n++] = 5; p[n++] = 1; p[n++] = 9;
	dchid_put_le16(p + n, 2); dchid_put_le16(p + n + 2, 6); n += 4;
	memset(p + n, 0, 6); n += 6;
	dchid_put_le16(p + n, 7); dchid_put_le16(p + n + 2, 4); n += 4;
	memcpy(p + n, "kbd", 4); n += 4;

	CHECK(dchid_init_next(p, n, &pos, &b) == 1 && b.type == 0 && b.len == 3 && b.data[2] == 9);
	CHECK(dchid_init_next(p, n, &pos, &b) == 1 && b.type == DCHID_BLK_TRANSPORT && b.len == 6);
	CHECK(dchid_init_next(p, n, &pos, &b) == 1 && b.type == DCHID_BLK_PRODUCT && !strcmp((const char *)b.data, "kbd"));
	CHECK(dchid_init_next(p, n, &pos, &b) == 0);
	pos = 0;
	CHECK(dchid_init_next(p, n - 3, &pos, &b) == 1);	/* first block is intact */
	CHECK(dchid_init_next(p, n - 3, &pos, &b) == 1);
	CHECK(dchid_init_next(p, n - 3, &pos, &b) == -1);	/* product block truncated */
	pos = 0;
	dchid_put_le16(p + 2, 0x800);				/* oversized length */
	CHECK(dchid_init_next(p, n, &pos, &b) == -1);
}

/* ----------------------------------------------------------------- fuzzing */

static void test_assembler_fuzz(void)
{
	u8 buf[256];
	struct dchid_asm a = {.buf = buf, .cap = sizeof(buf), .have = 0};

	for (int round = 0; round < 20000; round++) {
		dchid_asm_reset(&a);
		for (int step = 0; step < 40; step++) {
			size_t need = dchid_asm_need(&a);
			if (need > a.cap - a.have)
				need = a.cap - a.have;
			if (!need)
				break;
			if (a.have == 0 && (rnd() & 3)) {
				/* bias towards plausible headers */
				buf[0] = 6 + rnd() % 4;
				buf[1] = (u8)rnd();
				dchid_put_le16(buf + 2, (u16)(rnd() % 300));
			}
			for (size_t k = 0; k < need; k++)
				if (a.have + k > 3 || !(rnd() & 3))
					buf[a.have + k] = (u8)rnd();
			a.have += need;
			enum dchid_asm_status st = dchid_asm_check(&a);
			CHECK(a.have <= a.cap);
			if (st != DCHID_ASM_INCOMPLETE)
				break;
		}
	}
}

int main(void)
{
	test_encoders();
	test_build_and_parse();
	test_smallest_message();
	test_assembler_errors();
	test_ring_basics();
	test_ring_model();
	test_end_to_end();
	test_init_blocks();
	test_assembler_fuzz();
	printf("%d checks, %d failures\n", checks, failures);
	return failures ? 1 : 0;
}
