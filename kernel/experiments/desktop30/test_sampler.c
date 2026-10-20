// SPDX-License-Identifier: MIT
#define main sampler_entry
#include "samplecpu.c"
#undef main
#include <assert.h>
static void put(char *ring,size_t size,uint64_t pos,const void *src,size_t n) {
    const char *p=src;
    for(size_t i=0;i<n;i++)ring[(pos+i)&(size-1)]=p[i];
}
int main(void) {
    char ring[64]={0};struct perf_event_mmap_page meta={0};
    struct {struct perf_event_header h;uint64_t ip;} sample={{PERF_RECORD_SAMPLE,0,16},0x1010};
    areas[0]=(struct area){0x1000,0x2000,0};nareas=1;
    meta.data_tail=60;meta.data_head=76;put(ring,64,60,&sample,16);
    assert(!drain(&meta,ring,64));assert(counts[0]==1 && meta.data_tail==76);
    sample.ip=0x3000;put(ring,64,76,&sample,16);meta.data_head=92;
    assert(!drain(&meta,ring,64));assert(counts[5]==1);
    struct {struct perf_event_header h;uint64_t id,n;} loss={{PERF_RECORD_LOST,0,24},1,5};
    put(ring,64,92,&loss,24);meta.data_head=116;assert(!drain(&meta,ring,64));assert(lost==5);
    meta.data_head=meta.data_tail+65;assert(drain(&meta,ring,64)==-1);
    meta.data_head=meta.data_tail-1;assert(drain(&meta,ring,64)==-1);
    meta.data_head=meta.data_tail+4;assert(drain(&meta,ring,64)==-1);
    sample.h.size=0;put(ring,64,116,&sample,16);meta.data_head=132;assert(drain(&meta,ring,64)==-1);
    sample.h.size=17;put(ring,64,116,&sample,16);assert(drain(&meta,ring,64)==-1);
    sample.h.size=8;put(ring,64,116,&sample,16);assert(drain(&meta,ring,64)==-1);
    assert(!maps(getpid()));
    puts("PASS wrapped samples, unknown IP, lost records, six malformed-ring refusals, live maps");
    return 0;
}
