// Original CPU-only, offscreen pixel-work reference; no graphics API/display.
// Fixed premultiplied-alpha overlay over an opaque deterministic background.
// This isolates pixel arithmetic/copy, NOT Mesa or WindowServer equivalence.
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/resource.h>
#include <unistd.h>

static uint64_t ns(clockid_t c) {
    struct timespec t; if(clock_gettime(c,&t)) exit(2);
    return (uint64_t)t.tv_sec*1000000000ULL+t.tv_nsec;
}
static uint32_t blend(uint32_t dst,uint32_t src) {
    unsigned inv=255-(src>>24), result=0xff000000;
    for(unsigned s=0;s<24;s+=8) {
        unsigned v=((src>>s)&255)+((((dst>>s)&255)*inv+127)/255);
        result|=v<<s;
    }
    return result;
}
static uint64_t checksum(const uint32_t *v,size_t n) {
    uint64_t sum=0;
    for(size_t i=0;i<n;i++)sum+=(uint64_t)v[i]*(i%251+1);
    return sum;
}
int main(int argc,char **argv) {
    unsigned w=3456,h=2160;
    if(argc==3) {
        char *a,*b; unsigned long x=strtoul(argv[1],&a,10),y=strtoul(argv[2],&b,10);
        if(*a||*b||!x||!y||x>3840||y>2160)return 2;
        w=x;h=y;
    } else if(argc!=1)return 2;
    size_t n=(size_t)w*h;
    uint32_t *base=malloc(n*4),*over=malloc(n*4),*out=malloc(n*4);
    if(!base||!over||!out)return 2;
    alarm(15);
    for(size_t i=0;i<n;i++) {
        base[i]=0xff000000u|((uint32_t)i&0xffffff);
        over[i]=0x40000000u|((i%65)<<16)|((i%33)<<8)|(i%17);
        out[i]=0;
    }
    for(int mode=0;mode<2;mode++) {
        uint64_t expected=0;
        for(size_t i=0;i<n;i++)expected+=(uint64_t)(mode?blend(base[i],over[i]):base[i])*(i%251+1);
        for(int rep=0;rep<9;rep++) {
            struct rusage before,after;getrusage(RUSAGE_SELF,&before);
            uint64_t c=ns(CLOCK_THREAD_CPUTIME_ID),t=ns(CLOCK_MONOTONIC);
            if(mode) for(size_t i=0;i<n;i++)out[i]=blend(base[i],over[i]);
            else for(size_t i=0;i<n;i++)out[i]=base[i];
            uint64_t end=ns(CLOCK_MONOTONIC),cpu=ns(CLOCK_THREAD_CPUTIME_ID)-c;
            getrusage(RUSAGE_SELF,&after);
            uint64_t sum=checksum(out,n);
            if(sum!=expected)return 3;
            printf("{\"test\":\"%s\",\"width\":%u,\"height\":%u,\"rep\":%d,\"warmup\":%s,\"wall_ns\":%llu,\"cpu_ns\":%llu,\"checksum\":%llu,\"minor_faults\":%ld,\"major_faults\":%ld,\"voluntary_switches\":%ld,\"involuntary_switches\":%ld}\n",
                mode?"alpha_over":"copy",w,h,rep,rep==0?"true":"false",(unsigned long long)(end-t),(unsigned long long)cpu,(unsigned long long)sum,
                after.ru_minflt-before.ru_minflt,after.ru_majflt-before.ru_majflt,after.ru_nvcsw-before.ru_nvcsw,after.ru_nivcsw-before.ru_nivcsw);
        }
    }
    free(base);free(over);free(out);return 0;
}
