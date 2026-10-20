// SPDX-License-Identifier: MIT
// Original bounded main-thread CPU-clock sampler. No hardware PMU events.
// Raw instruction addresses stay in this process; output is aggregate categories.
#define _GNU_SOURCE
#include <linux/perf_event.h>
#include <sys/syscall.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <time.h>

struct area {uint64_t lo,hi; unsigned category;};
static struct area areas[4096];
static size_t nareas;
static volatile sig_atomic_t stopped;
static const char *names[]={"compositor","mesa","llvm","anonymous_executable","other_executable_file","unmapped"};
static uint64_t counts[6],lost;
static void stop(int s) {(void)s;stopped=1;}
static double now(void) {struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static int maps(pid_t pid) {
    char path[64],line[4096]; snprintf(path,sizeof(path),"/proc/%d/maps",pid);
    FILE *f=fopen(path,"r");if(!f)return -1;
    nareas=0;
    while(fgets(line,sizeof(line),f)) {
        unsigned long lo,hi;char perms[5];int at=0;
        if(sscanf(line,"%lx-%lx %4s %*s %*s %*s %n",&lo,&hi,perms,&at)!=3 || !strchr(perms,'x'))continue;
        if(nareas==4096) {fclose(f);return -1;}
        const char *p=line+at;unsigned c=4;
        if(strstr(p,"/Hyprland"))c=0;
        else if(strstr(p,"/libgallium") || strstr(p,"/libEGL") || strstr(p,"/libGLES"))c=1;
        else if(strstr(p,"/libLLVM"))c=2;
        else if(!strchr(p,'/'))c=3;
        areas[nareas++]=(struct area){lo,hi,c};
    }
    fclose(f);return nareas?0:-1;
}
static void categorize(uint64_t ip) {
    unsigned c=5;
    for(size_t i=0;i<nareas;i++)if(ip>=areas[i].lo && ip<areas[i].hi){c=areas[i].category;break;}
    counts[c]++;
}
static void ringcopy(void *dst,const char *ring,size_t size,uint64_t pos,size_t n) {
    size_t off=pos&(size-1),first=n<size-off?n:size-off;
    memcpy(dst,ring+off,first);memcpy((char *)dst+first,ring,n-first);
}
static int drain(struct perf_event_mmap_page *meta,const char *ring,size_t size) {
    uint64_t head=__atomic_load_n(&meta->data_head,__ATOMIC_ACQUIRE),tail=meta->data_tail;
    if(head<tail || head-tail>size)return -1;
    while(tail<head){
        struct perf_event_header h;
        if(head-tail<sizeof(h))return -1;
        ringcopy(&h,ring,size,tail,sizeof(h));
        if(h.size<sizeof(h) || h.size>head-tail || h.size>size)return -1;
        if(h.type==PERF_RECORD_SAMPLE){
            if(h.size!=16)return -1;
            uint64_t ip;ringcopy(&ip,ring,size,tail+8,8);categorize(ip);
        }else if(h.type==PERF_RECORD_LOST){
            if(h.size!=24)return -1;
            uint64_t n;ringcopy(&n,ring,size,tail+16,8);lost+=n;
        }
        tail+=h.size;
    }
    __atomic_store_n(&meta->data_tail,tail,__ATOMIC_RELEASE);return 0;
}
int main(int argc,char **argv) {
    char *end;long pid,seconds;
    if(argc!=3)return 3;
    errno=0;pid=strtol(argv[1],&end,10);if(errno || *end || pid<=1 || pid>4194304)return 3;
    seconds=strtol(argv[2],&end,10);if(errno || *end || seconds<1 || seconds>90)return 3;
    if(maps((pid_t)pid))return 3;
    signal(SIGTERM,stop);signal(SIGINT,stop);signal(SIGALRM,stop);alarm((unsigned)seconds+2);
    struct perf_event_attr a={.type=PERF_TYPE_SOFTWARE,.size=sizeof(a),.config=PERF_COUNT_SW_CPU_CLOCK,
        .sample_period=10000000,.sample_type=PERF_SAMPLE_IP,.disabled=1,
        .exclude_kernel=1,.exclude_hv=1,.wakeup_events=1};
    int fd=(int)syscall(__NR_perf_event_open,&a,pid,-1,-1,PERF_FLAG_FD_CLOEXEC);
    if(fd<0){
        printf("{\"status\":\"unavailable\",\"errno\":%d,\"event\":\"software_cpu_clock\"}\n",errno);
        return 0;
    }
    size_t page=(size_t)sysconf(_SC_PAGESIZE),size=page*8;
    struct perf_event_mmap_page *meta=mmap(NULL,page+size,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
    if(meta==MAP_FAILED){close(fd);return 3;}
    if(meta->data_offset!=page || meta->data_size!=size){munmap(meta,page+size);close(fd);return 3;}
    if(ioctl(fd,PERF_EVENT_IOC_RESET,0) || ioctl(fd,PERF_EVENT_IOC_ENABLE,0))return 3;
    double start=now(),refresh=start;
    int bad=0;
    while(!stopped && now()-start<seconds){
        if(drain(meta,(char *)meta+page,size)){bad=1;break;}
        if(now()-refresh>=1){if(maps((pid_t)pid)){bad=1;break;}refresh=now();}
        struct timespec pause={0,20000000};nanosleep(&pause,NULL);
    }
    ioctl(fd,PERF_EVENT_IOC_DISABLE,0);
    if(drain(meta,(char *)meta+page,size))bad=1;
    printf("{\"status\":\"%s\",\"event\":\"software_cpu_clock\",\"period_ns\":10000000,\"wall_s\":%.6f,\"lost\":%llu,\"categories\":{",bad?"invalid":"sampled",now()-start,(unsigned long long)lost);
    for(unsigned i=0;i<6;i++)printf("%s\"%s\":%llu",i?",":"",names[i],(unsigned long long)counts[i]);
    puts("}}");munmap(meta,page+size);close(fd);return bad?3:0;
}
