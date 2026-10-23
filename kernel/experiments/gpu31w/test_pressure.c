/* SPDX-License-Identifier: MIT */
#include "pressure.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

struct fixture {
    struct gpu31w_submission *submission;
    bool note_ok, write_ok, publish_ok, reenter;
    uint32_t note_status, producer;
    unsigned events;
    char order[4];
    uint8_t record[24];
};
static void event(struct fixture *f, char value)
{
    assert(f->events < 3);
    f->order[f->events++] = value;
    if (f->reenter)
        assert(gpu31w_submit(f->submission) == GPU31W_STATE);
}
static struct gpu31v_effect note(void *context, uint32_t endpoint,
    uint64_t word, bool flag)
{
    struct fixture *f = context;
    assert(f->events == 0);
    assert(endpoint == 0x21 && word == UINT64_C(0x0085000000000000) && !flag);
    event(f,'N'); /* Sending may have effects even on refused/zero status. */
    return (struct gpu31v_effect){f->note_ok, f->note_status};
}
static struct gpu31v_effect write_record(void *context, uint64_t offset,
    const uint8_t record[24])
{
    struct fixture *f = context;
    assert(offset == (uint64_t)f->producer * 24);
    assert(f->events == (f->submission->note_required ? 1u : 0u));
    if (f->submission->note_required) assert(f->order[0]=='N');
    memcpy(f->record,record,24);
    event(f,'W');
    return (struct gpu31v_effect){f->write_ok, UINT32_C(0x12345678)};
}
static struct gpu31v_effect publish(void *context, uint32_t next)
{
    struct fixture *f = context;
    assert(next == (f->producer + 1) % 256);
    assert(f->order[f->events-1]=='W');
    assert(memcmp(f->record,f->submission->mapping.record,24)==0);
    event(f,'P');
    return (struct gpu31v_effect){f->publish_ok, UINT32_MAX};
}
static struct gpu31v_mapping mapping(void)
{
    return (struct gpu31v_mapping){UINT64_C(0x100000000000), 16384, 14, false};
}
static struct gpu31v_ops ops(struct fixture *f)
{
    return (struct gpu31v_ops){write_record,publish,f};
}
static struct gpu31w_transport transport(struct fixture *f)
{
    return (struct gpu31w_transport){0,0x21,note,f};
}
static enum gpu31w_result prepare(struct gpu31w_submission *s,
    struct fixture *f, uint32_t consumer)
{
    struct gpu31v_mapping m=mapping();
    struct gpu31v_ops o=ops(f);struct gpu31w_transport t=transport(f);
    return gpu31w_prepare(s,&m,consumer,f->producer,6144,&o,&t);
}
static void invalid(void)
{
    struct gpu31w_submission s={0};struct fixture f={.submission=&s};
    struct gpu31v_mapping m=mapping();struct gpu31v_ops o=ops(&f);
    struct gpu31w_transport t=transport(&f);
    assert(gpu31w_prepare(NULL,&m,0,0,6144,&o,&t)==GPU31W_ARGUMENT);
    assert(gpu31w_prepare(&s,&m,0,0,6144,&o,NULL)==GPU31W_ARGUMENT);
    t.provider_role=1;
    assert(gpu31w_prepare(&s,&m,0,0,6144,&o,&t)==GPU31W_ARGUMENT);
    t=transport(&f);t.endpoint=0x20;
    assert(gpu31w_prepare(&s,&m,0,0,6144,&o,&t)==GPU31W_ARGUMENT);
    t=transport(&f);t.note=NULL;
    assert(gpu31w_prepare(&s,&m,0,0,6144,&o,&t)==GPU31W_ARGUMENT);
    t=transport(&f);
    assert(gpu31w_prepare(&s,&m,256,0,6144,&o,&t)==GPU31W_ARGUMENT);
    assert(gpu31w_prepare(&s,&m,0,256,6144,&o,&t)==GPU31W_ARGUMENT);
    assert(gpu31w_prepare(&s,&m,0,0,6143,&o,&t)==GPU31W_ARGUMENT);
    m.byte_length=0;
    assert(gpu31w_prepare(&s,&m,0,0,6144,&o,&t)==GPU31W_ARGUMENT);
    assert(s.phase==GPU31W_FRESH && s.mapping.phase==GPU31V_FRESH && f.events==0);
    assert(gpu31w_submit(&s)==GPU31W_STATE);
    assert(gpu31w_submit(NULL)==GPU31W_ARGUMENT);
}
static void all_empty_positions(void)
{
    for(uint32_t p=0;p<256;++p) {
        struct gpu31w_submission s={0};
        struct fixture f={.submission=&s,.note_ok=true,.write_ok=true,.publish_ok=true,.producer=p};
        assert(prepare(&s,&f,p)==GPU31W_OK && !s.note_required && !f.events);
        assert(gpu31w_submit(&s)==GPU31W_OK && s.phase==GPU31W_DONE);
        assert(!s.note_attempted && !s.note_accepted);
        assert(strcmp(f.order,"WP")==0);
    }
}
static void all_pressure_positions(void)
{
    for(uint32_t p=0;p<256;++p) {
        struct gpu31w_submission s={0};
        struct fixture f={.submission=&s,.note_ok=true,.write_ok=true,.publish_ok=true,
            .note_status=UINT32_MAX,.producer=p};
        assert(prepare(&s,&f,(p+2)%256)==GPU31W_OK && s.note_required && !f.events);
        assert(gpu31w_submit(&s)==GPU31W_OK && s.phase==GPU31W_DONE);
        assert(s.note_attempted && s.note_accepted && s.note_status==UINT32_MAX);
        assert(s.mapping.publish_status==UINT32_MAX && strcmp(f.order,"NWP")==0);
    }
}
static void all_full_positions(void)
{
    for(uint32_t p=0;p<256;++p) {
        struct gpu31w_submission s={0};
        struct fixture f={.submission=&s,.note_ok=true,.write_ok=true,.publish_ok=true,.producer=p};
        assert(prepare(&s,&f,(p+1)%256)==GPU31W_QUEUE_FULL);
        assert(gpu31w_submit(&s)==GPU31W_QUEUE_FULL && !f.events);
        assert(!s.note_attempted && !s.mapping.write_attempted);
    }
}
static void uncertain_note(void)
{
    for(unsigned i=0;i<2;++i) {
        struct gpu31w_submission s={0};
        struct fixture f={.submission=&s,.write_ok=true,.publish_ok=true,.note_status=i*23};
        assert(prepare(&s,&f,2)==GPU31W_OK);
        assert(gpu31w_submit(&s)==GPU31W_NOTE_UNKNOWN && s.phase==GPU31W_STOPPED);
        assert(s.note_attempted && !s.note_accepted && s.note_status==i*23);
        assert(s.note_word==GPU31W_NOTE && !s.mapping.write_attempted);
        assert(strcmp(f.order,"N")==0);
        assert(gpu31w_submit(&s)==GPU31W_STATE && prepare(&s,&f,2)==GPU31W_STATE);
        assert(f.events==1);
    }
}
static void uncertain_mapping(void)
{
    for(unsigned stage=0;stage<2;++stage) {
        struct gpu31w_submission s={0};
        struct fixture f={.submission=&s,.note_ok=true,.write_ok=stage==1,.publish_ok=false};
        assert(prepare(&s,&f,2)==GPU31W_OK);
        assert(gpu31w_submit(&s)==(stage==0 ? GPU31W_WRITE_UNKNOWN : GPU31W_PUBLISH_UNKNOWN));
        assert(s.phase==GPU31W_STOPPED && s.note_accepted);
        assert(s.mapping.phase==(stage==0 ? GPU31V_WRITE_UNKNOWN : GPU31V_PUBLICATION_UNKNOWN));
        assert(strcmp(f.order,stage==0 ? "NW" : "NWP")==0);
        assert(gpu31w_submit(&s)==GPU31W_STATE);
        assert(prepare(&s,&f,2)==GPU31W_STATE);
    }
}
static void reentrancy(void)
{
    struct gpu31w_submission s={0};
    struct fixture f={.submission=&s,.note_ok=true,.write_ok=true,.publish_ok=true,.reenter=true};
    assert(prepare(&s,&f,2)==GPU31W_OK);
    assert(gpu31w_submit(&s)==GPU31W_OK && strcmp(f.order,"NWP")==0);
}
static void copied_inputs_once(void)
{
    struct gpu31w_submission s={0};
    struct fixture f={.submission=&s,.note_ok=true,.write_ok=true,.publish_ok=true};
    struct gpu31v_mapping m=mapping();struct gpu31v_ops o=ops(&f);
    struct gpu31w_transport t=transport(&f);uint8_t bytes[24];
    assert(gpu31v_encode(&m,bytes)==GPU31V_OK);
    assert(gpu31w_prepare(&s,&m,2,0,6144,&o,&t)==GPU31W_OK);
    m.byte_length=0;o.write=NULL;t.note=NULL;t.endpoint=0x20;
    assert(gpu31w_submit(&s)==GPU31W_OK && memcmp(bytes,f.record,24)==0);
    assert(gpu31w_submit(&s)==GPU31W_STATE && prepare(&s,&f,2)==GPU31W_STATE);
    assert(f.events==3);
}
int main(void)
{
    invalid();all_empty_positions();all_pressure_positions();all_full_positions();
    uncertain_note();uncertain_mapping();reentrancy();copied_inputs_once();
    puts("GPU31W_PRESSURE_PASS");return 0;
}
