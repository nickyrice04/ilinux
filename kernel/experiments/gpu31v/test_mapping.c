/* SPDX-License-Identifier: MIT */
#include "mapping.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

struct fixture {
    struct gpu31v_submission *submission;
    bool write_ok, publish_ok, reenter;
    unsigned writes, publications;
    uint64_t offset;
    uint32_t published;
    uint8_t bytes[GPU31V_MAPPING_BYTES];
};
static struct gpu31v_mapping sample(void)
{
    return (struct gpu31v_mapping){UINT64_C(0x123456789abc0000), 8192, 16, true};
}
static struct gpu31v_effect write_record(void *context, uint64_t offset,
    const uint8_t record[GPU31V_MAPPING_BYTES])
{
    struct fixture *f = context;
    assert(f->writes == 0 && f->publications == 0);
    if (f->reenter)
        assert(gpu31v_submit(f->submission) == GPU31V_STATE);
    ++f->writes;
    f->offset = offset;
    memcpy(f->bytes, record, sizeof(f->bytes)); /* Effects even on refusal. */
    return (struct gpu31v_effect){f->write_ok, UINT32_C(0xa1234567)};
}
static struct gpu31v_effect publish_record(void *context, uint32_t producer)
{
    struct fixture *f = context;
    assert(f->writes == 1 && f->publications == 0);
    assert(memcmp(f->bytes, f->submission->record, sizeof(f->bytes)) == 0);
    if (f->reenter)
        assert(gpu31v_submit(f->submission) == GPU31V_STATE);
    ++f->publications;
    f->published = producer; /* Store may succeed even when callback refuses. */
    return (struct gpu31v_effect){f->publish_ok, UINT32_MAX};
}
static struct gpu31v_ops ops(struct fixture *f)
{
    return (struct gpu31v_ops){write_record, publish_record, f};
}
static void golden(void)
{
    const uint8_t expected[24] = {
        0,0,0xbc,0x9a,0x78,0x56,0x34,0x12, 2,0,0,0, 0,0,0,0,
        4,0,5,0, 0,0,0,0
    };
    uint8_t bytes[24];
    struct gpu31v_mapping m = sample();
    assert(gpu31v_encode(&m, bytes) == GPU31V_OK);
    assert(memcmp(bytes, expected, sizeof(bytes)) == 0);
    for (unsigned shift = 14; shift <= 29; ++shift) {
        m.gart_page_shift = shift;
        m.flag_bit2 = false;
        assert(gpu31v_encode(&m, bytes) == GPU31V_OK);
        assert(((unsigned)bytes[16] | ((unsigned)bytes[17] << 8)) ==
            (1u << (shift - 14)));
        assert(bytes[18] == 1 && bytes[19] == 0);
    }
}
static void bounds(void)
{
    struct gpu31v_mapping m = sample();
    uint8_t bytes[24], before[24];
    memset(before, 0xa5, sizeof(before));
    assert(gpu31v_encode(NULL, bytes) == GPU31V_ARGUMENT);
    assert(gpu31v_encode(&m, NULL) == GPU31V_ARGUMENT);
    for (unsigned i = 0; i < 8; ++i) {
        m = sample();
        switch (i) {
        case 0: m.byte_length = 0; break;
        case 1: m.byte_length = 4095; break;
        case 2: m.byte_length = 4097; break;
        case 3: m.byte_length = (UINT64_C(1) << 32) * 4096; break;
        case 4: m.firmware_va = UINT64_MAX - 4095; m.byte_length = 4096; break;
        case 5: m.gart_page_shift = 13; break;
        case 6: m.gart_page_shift = 30; break;
        default: m.gart_page_shift = (unsigned)-1; break;
        }
        memcpy(bytes, before, sizeof(bytes));
        assert(gpu31v_encode(&m, bytes) == GPU31V_ARGUMENT);
        assert(memcmp(bytes, before, sizeof(bytes)) == 0);
    }
    m = sample(); m.firmware_va = 0; m.byte_length = (uint64_t)UINT32_MAX * 4096;
    assert(gpu31v_encode(&m, bytes) == GPU31V_OK);
    for (unsigned i = 8; i < 12; ++i) assert(bytes[i] == 255);
    m.byte_length = 4096; m.firmware_va = UINT64_MAX - 4096;
    assert(gpu31v_encode(&m, bytes) == GPU31V_OK);
}
static void configuration(void)
{
    struct gpu31v_submission s = {0};
    struct fixture f = {0}; struct gpu31v_ops o = ops(&f);
    struct gpu31v_mapping m = sample();
    assert(gpu31v_prepare(NULL,&m,0,0,6144,&o) == GPU31V_ARGUMENT);
    assert(gpu31v_prepare(&s,NULL,0,0,6144,&o) == GPU31V_ARGUMENT);
    assert(gpu31v_prepare(&s,&m,0,0,6144,NULL) == GPU31V_ARGUMENT);
    assert(gpu31v_prepare(&s,&m,256,0,6144,&o) == GPU31V_ARGUMENT);
    assert(gpu31v_prepare(&s,&m,0,256,6144,&o) == GPU31V_ARGUMENT);
    assert(gpu31v_prepare(&s,&m,0,0,6143,&o) == GPU31V_ARGUMENT);
    o.write = NULL;
    assert(gpu31v_prepare(&s,&m,0,0,6144,&o) == GPU31V_ARGUMENT);
    o = ops(&f); o.publish = NULL;
    assert(gpu31v_prepare(&s,&m,0,0,6144,&o) == GPU31V_ARGUMENT);
    assert(s.phase == GPU31V_FRESH && !f.writes && !f.publications);
    assert(gpu31v_submit(NULL) == GPU31V_ARGUMENT);
    assert(gpu31v_submit(&s) == GPU31V_STATE);
}
static void all_index_pairs(void)
{
    unsigned full = 0, submitted = 0;
    for (uint32_t c = 0; c < 256; ++c) for (uint32_t p = 0; p < 256; ++p) {
        struct gpu31v_submission s = {0};
        struct fixture f = {.submission=&s, .write_ok=true, .publish_ok=true};
        struct gpu31v_ops o = ops(&f);
        struct gpu31v_mapping m = sample();
        uint32_t next = p == 255 ? 0 : p + 1;
        enum gpu31v_result want = next == c ? GPU31V_QUEUE_FULL : GPU31V_OK;
        assert(gpu31v_prepare(&s,&m,c,p,6144,&o) == want);
        assert(!f.writes && !f.publications);
        assert(gpu31v_submit(&s) == want);
        if (want == GPU31V_QUEUE_FULL) {
            ++full;
            assert(!f.writes && !f.publications && s.phase == GPU31V_FULL);
        } else {
            ++submitted;
            assert(f.offset == (uint64_t)p * 24 && f.offset + 24 <= 6144);
            assert(f.writes == 1 && f.publications == 1 && f.published == next);
            assert(s.phase == GPU31V_SUBMITTED && s.write_status == UINT32_C(0xa1234567));
            assert(s.publish_status == UINT32_MAX);
        }
    }
    assert(full == 256 && submitted == 65280);
}
static void uncertain_write(void)
{
    struct gpu31v_submission s = {0};
    struct fixture f = {.submission=&s, .publish_ok=true};
    struct gpu31v_ops o = ops(&f); struct gpu31v_mapping m = sample();
    assert(gpu31v_prepare(&s,&m,0,0,6144,&o) == GPU31V_OK);
    assert(gpu31v_submit(&s) == GPU31V_WRITE_UNCERTAIN);
    assert(s.phase == GPU31V_WRITE_UNKNOWN && s.write_attempted && !s.publication_attempted);
    assert(f.writes == 1 && !f.publications && memcmp(f.bytes,s.record,24) == 0);
    assert(gpu31v_submit(&s) == GPU31V_STATE);
    assert(gpu31v_prepare(&s,&m,0,0,6144,&o) == GPU31V_STATE);
    assert(f.writes == 1 && !f.publications);
}
static void uncertain_publication(void)
{
    struct gpu31v_submission s = {0};
    struct fixture f = {.submission=&s, .write_ok=true};
    struct gpu31v_ops o = ops(&f); struct gpu31v_mapping m = sample();
    assert(gpu31v_prepare(&s,&m,1,255,6144,&o) == GPU31V_OK);
    assert(gpu31v_submit(&s) == GPU31V_PUBLISH_UNCERTAIN);
    assert(s.phase == GPU31V_PUBLICATION_UNKNOWN && s.publication_attempted);
    assert(f.published == 0 && s.proposed_producer == 0 && s.producer == 255);
    assert(s.publish_status == UINT32_MAX && f.writes == 1 && f.publications == 1);
    assert(gpu31v_submit(&s) == GPU31V_STATE);
    assert(gpu31v_prepare(&s,&m,1,255,6144,&o) == GPU31V_STATE);
}
static void reentrancy(void)
{
    struct gpu31v_submission s = {0};
    struct fixture f = {.submission=&s,.write_ok=true,.publish_ok=true,.reenter=true};
    struct gpu31v_ops o = ops(&f); struct gpu31v_mapping m = sample();
    assert(gpu31v_prepare(&s,&m,4,2,6144,&o) == GPU31V_OK);
    assert(gpu31v_submit(&s) == GPU31V_OK);
    assert(f.writes == 1 && f.publications == 1);
}
static void copied_inputs_and_one_attempt(void)
{
    struct gpu31v_submission s = {0};
    struct fixture f = {.submission=&s,.write_ok=true,.publish_ok=true};
    struct gpu31v_ops o = ops(&f); struct gpu31v_mapping m = sample();
    uint8_t expected[24]; assert(gpu31v_encode(&m,expected) == GPU31V_OK);
    assert(gpu31v_prepare(&s,&m,0,0,UINT64_MAX,&o) == GPU31V_OK);
    m.byte_length = 0; o.write = NULL; o.publish = NULL;
    assert(gpu31v_submit(&s) == GPU31V_OK);
    assert(memcmp(expected,f.bytes,24) == 0);
    assert(gpu31v_submit(&s) == GPU31V_STATE);
    assert(f.writes == 1 && f.publications == 1);
}
int main(void)
{
    golden(); bounds(); configuration(); all_index_pairs(); uncertain_write();
    uncertain_publication(); reentrancy(); copied_inputs_and_one_attempt();
    puts("GPU31V_MAPPING_PASS");
    return 0;
}
