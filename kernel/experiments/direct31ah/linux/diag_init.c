/* SPDX-License-Identifier: MIT */
/* Original RAM-only PID 1. No block-device opens, MMIO, hotplug or frequency writes. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

enum { MAX_WORKERS=64, BATCH=1024, MEM_BYTES=64*1024*1024 };
static atomic_int ready, go, stop;
static int log_fd=-1;
static int diagnostic_printf(const char *format,...) {
    char line[4096];va_list args;va_start(args,format);
    int n=vsnprintf(line,sizeof(line),format,args);va_end(args);
    if(n<0 || (size_t)n>=sizeof(line))return -1;
    size_t wrote=fwrite(line,1,(size_t)n,stdout);fflush(stdout);
    if(log_fd>=0) {
        char record[4160];int len=snprintf(record,sizeof(record),"<6>iLinux31ah %s",line);
        if(len>0 && (size_t)len<sizeof(record))(void)write(log_fd,record,(size_t)len);
    }
    return wrote==(size_t)n?n:-1;
}
static int diagnostic_puts(const char *line) {return diagnostic_printf("%s\n",line);}
#define printf diagnostic_printf
#define puts diagnostic_puts
static const uint64_t mult=6364136223846793005ULL;
struct worker { int cpu, actual, pin_error, migrated, timer_error; uint64_t begin,work_end,end,steps,value,sleep_ns; };
struct observation {
    int created,passed,expected,timers_checked,timer_failures,timed_out,worker_result,memory_result;
    uint64_t overlap_ns;
};
static struct observation observed={.worker_result=-1,.memory_result=-1};
static int simulate_stall;
static uint64_t now_ns(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) _exit(121);
    return (uint64_t)t.tv_sec*1000000000ULL+(uint64_t)t.tv_nsec;
}
static uint64_t advance(uint64_t seed,uint64_t count) {
    uint64_t a=1,c=0,m=mult,i=1;
    while (count) {
        if (count&1) { a*=m;c=c*m+i; }
        i*=m+1;m*=m;count>>=1;
    }
    return a*seed+c;
}
static void *run_worker(void *arg) {
    struct worker *w=arg;
    cpu_set_t set;CPU_ZERO(&set);CPU_SET(w->cpu,&set);
    w->pin_error=pthread_setaffinity_np(pthread_self(),sizeof(set),&set);
    atomic_fetch_add(&ready,1);
    while (!atomic_load(&go) && !atomic_load(&stop)) sched_yield();
    if (w->pin_error || atomic_load(&stop)) return NULL;
    /* Only --selftest-timeout sets this; no native switch enables it. */
    while(simulate_stall && !atomic_load(&stop))usleep(5000);
    if(atomic_load(&stop))return NULL;
    w->actual=sched_getcpu();w->begin=now_ns();w->value=0x31a60000ULL+(unsigned)w->cpu;
    do {
        for (int j=0;j<BATCH;j++) w->value=w->value*mult+1;
        w->steps+=BATCH;
        if (sched_getcpu()!=w->cpu) w->migrated=1;
    } while (!atomic_load(&stop) && now_ns()-w->begin<250000000ULL);
    w->work_end=now_ns();
    struct timespec delay={.tv_sec=0,.tv_nsec=1000000};
    uint64_t before=now_ns();
    while (clock_nanosleep(CLOCK_MONOTONIC,0,&delay,&delay)==EINTR) {}
    w->sleep_ns=now_ns()-before;
    if (w->sleep_ns<1000000ULL) w->timer_error=1;
    w->end=now_ns();
    return NULL;
}
static int per_cpu(int limit,int expected) {
    cpu_set_t allowed;
    if (sched_getaffinity(0,sizeof(allowed),&allowed)) return 1;
    /* A timed-out thread can still refer to its record. Never return a pointer
     * into the per_cpu stack to that thread or inspect its unjoined record. */
    static struct worker workers[MAX_WORKERS];
    static pthread_t tids[MAX_WORKERS];int n=0,created=0,bad=0;
    observed.expected=expected;observed.worker_result=1;
    memset(workers,0,sizeof(workers));
    for (int c=0;c<CPU_SETSIZE;c++) if (CPU_ISSET(c,&allowed)) {
        if (n==MAX_WORKERS) { puts("{\"phase\":\"cpu_workers\",\"result\":\"REFUSED_CPU_BOUND\"}");return 1; }
        workers[n++].cpu=c;
        if (limit && n==limit) break;
    }
    if (!n) return 1;
    int wrong_count=expected && n!=expected;
    atomic_store(&ready,0);atomic_store(&go,0);atomic_store(&stop,0);
    for (int i=0;i<n;i++) {
        if (pthread_create(&tids[i],NULL,run_worker,&workers[i])) { bad=1;break; }
        created++;
    }
    uint64_t deadline=now_ns()+2000000000ULL;
    while (atomic_load(&ready)<created && now_ns()<deadline) sched_yield();
    if (created!=n || atomic_load(&ready)!=created) bad=1;
    if (bad) atomic_store(&stop,1);
    atomic_store(&go,1);
    uint64_t join_end=now_ns()+(simulate_stall?50000000ULL:3000000000ULL);
    struct timespec join_deadline={.tv_sec=(time_t)(join_end/1000000000ULL),.tv_nsec=(long)(join_end%1000000000ULL)};
    observed.created=created;
    uint64_t latest=0,earliest=UINT64_MAX;int intervals=0;
    for (int i=0;i<created;i++) {
        int joined=pthread_clockjoin_np(tids[i],NULL,CLOCK_MONOTONIC,&join_deadline);
        if(joined) {
            bad=1;atomic_store(&stop,1);
            if(joined==ETIMEDOUT)observed.timed_out++;
            printf("{\"phase\":\"cpu_worker_join\",\"worker_index\":%d,\"join_error\":%d,\"result\":\"%s\",\"unjoined_record_read\":false}\n",i,joined,joined==ETIMEDOUT?"TIMEOUT":"FAIL");
            continue;
        }
        struct worker *w=&workers[i];
        int ok=!w->pin_error && !w->migrated && !w->timer_error && w->actual==w->cpu && w->steps
            && w->value==advance(0x31a60000ULL+(unsigned)w->cpu,w->steps);
        if (!ok) bad=1;
        if(ok)observed.passed++;
        if(w->steps && !w->pin_error)observed.timers_checked++;
        if(w->timer_error)observed.timer_failures++;
        if(w->steps && w->work_end>w->begin) {
            intervals++;
            if (w->begin>latest)latest=w->begin;
            if (w->work_end<earliest)earliest=w->work_end;
        }
        printf("{\"phase\":\"cpu_worker\",\"cpu\":%d,\"actual_cpu\":%d,\"iterations\":%llu,\"elapsed_ns\":%llu,\"requested_sleep_ns\":1000000,\"observed_sleep_ns\":%llu,\"result\":\"%s\"}\n",
            w->cpu,w->actual,(unsigned long long)w->steps,(unsigned long long)(w->work_end-w->begin),(unsigned long long)w->sleep_ns,ok?"PASS":"FAIL");
    }
    uint64_t overlap=created>0 && intervals==created && earliest>latest?earliest-latest:0;
    bad|=wrong_count;
    if (n>1 && !overlap)bad=1;
    observed.overlap_ns=overlap;
    observed.worker_result=observed.timed_out?2:bad;
    printf("{\"phase\":\"cpu_workers\",\"workers\":%d,\"expected_native_workers\":%d,\"common_interval_ns\":%llu,\"result\":\"%s\",\"performance_parity_measured\":false}\n",
        created,expected,(unsigned long long)overlap,bad?"FAIL":"PASS");
    return bad;
}
static ssize_t read_file(const char *path,char *buf,size_t cap) {
    int fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if (fd<0)return -1;
    ssize_t n=read(fd,buf,cap-1);close(fd);
    if (n<0)return n;
    buf[n]=0;
    return n;
}
static int cmdline_has(const char *wanted) {
    char buf[4096],*save;ssize_t n=read_file("/proc/cmdline",buf,sizeof(buf));
    if(n<0 || n==(ssize_t)sizeof(buf)-1)return 0;
    for(char *p=strtok_r(buf," \t\r\n",&save);p;p=strtok_r(NULL," \t\r\n",&save))
        if(!strcmp(p,wanted))return 1;
    return 0;
}
static int compatible_has(const char *wanted) {
    char buf[4096];ssize_t n=read_file("/proc/device-tree/compatible",buf,sizeof(buf));
    if(n<0)return 0;
    size_t at=0,len=strlen(wanted);
    while(at<(size_t)n) {
        char *end=memchr(buf+at,0,(size_t)n-at);if(!end)return 0;
        size_t item=(size_t)(end-(buf+at));
        if(item==len && !memcmp(buf+at,wanted,len))return 1;
        at+=item+1;
    }
    return 0;
}
static void memory_smoke(void) {
    volatile uint64_t *p=malloc(MEM_BYTES);
    if (!p) { observed.memory_result=1;puts("{\"phase\":\"memory_smoke\",\"result\":\"ALLOCATION_FAILED\"}");return; }
    size_t words=MEM_BYTES/sizeof(*p);
    for (size_t i=0;i<words;i++)p[i]=(uint64_t)i;
    uint64_t start=now_ns(),sum=0;
    for (size_t i=0;i<words;i++)sum+=p[i];
    uint64_t elapsed=now_ns()-start,expected=(uint64_t)words*(words-1)/2;
    free((void *)p);
    observed.memory_result=sum==expected?0:1;
    printf("{\"phase\":\"memory_smoke\",\"bytes\":%d,\"read_ns\":%llu,\"checksum_ok\":%s,\"result\":\"%s\",\"full_bandwidth_benchmark\":false}\n",
        MEM_BYTES,(unsigned long long)elapsed,sum==expected?"true":"false",sum==expected?"PASS":"FAIL");
}
static int clean_name(const char *s) {
    if (!*s || strlen(s)>100 || !strcmp(s,".") || !strcmp(s,".."))return 0;
    for (;*s;s++)if (!( (*s>='a'&&*s<='z') || (*s>='A'&&*s<='Z') || (*s>='0'&&*s<='9') || *s=='_' || *s=='-' || *s=='.' || *s==':' ))return 0;
    return 1;
}
static int put(const char *path,const char *value) {
    int fd=open(path,O_WRONLY|O_CLOEXEC|O_NOFOLLOW);
    if (fd<0)return -1;
    size_t n=strlen(value);ssize_t result=write(fd,value,n);close(fd);
    return result==(ssize_t)n?0:-1;
}
static void gadget_log(void) {
    /* Native-only RAM configfs. This cannot run from --selftest or VM mode. */
    if (mount("configfs","/sys/kernel/config","configfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL) && errno!=EBUSY) {
        puts("{\"phase\":\"usb_log\",\"result\":\"CONFIGFS_FAILED\"}");return;
    }
    DIR *dir=opendir("/sys/class/udc");
    if (!dir) { puts("{\"phase\":\"usb_log\",\"result\":\"NO_UDC\"}");return; }
    struct dirent *ent;char udc[128]={0};
    while ((ent=readdir(dir)))if(ent->d_name[0]!='.' && clean_name(ent->d_name)) {
        snprintf(udc,sizeof(udc),"%.100s",ent->d_name);break;
    }
    closedir(dir);if(!*udc) {puts("{\"phase\":\"usb_log\",\"result\":\"NO_UDC\"}");return;}
    const char *base="/sys/kernel/config/usb_gadget/ilinux31ah";
    char path[256];
    if(mkdir(base,0700) && errno!=EEXIST)return;
    snprintf(path,sizeof(path),"%s/idVendor",base);if(put(path,"0x1d6b"))return;
    snprintf(path,sizeof(path),"%s/idProduct",base);if(put(path,"0x0104"))return;
    snprintf(path,sizeof(path),"%s/bcdDevice",base);if(put(path,"0x0131"))return;
    const char *dirs[]={"strings/0x409","configs/c.1","configs/c.1/strings/0x409","functions/gser.log"};
    for(unsigned i=0;i<sizeof(dirs)/sizeof(dirs[0]);i++) {snprintf(path,sizeof(path),"%s/%s",base,dirs[i]);if(mkdir(path,0700)&&errno!=EEXIST)return;}
    snprintf(path,sizeof(path),"%s/strings/0x409/manufacturer",base);if(put(path,"iLinux"))return;
    snprintf(path,sizeof(path),"%s/strings/0x409/product",base);if(put(path,"RAM diagnostic log"))return;
    snprintf(path,sizeof(path),"%s/configs/c.1/log",base);
    if(symlink("../../functions/gser.log",path)&&errno!=EEXIST)return;
    snprintf(path,sizeof(path),"%s/UDC",base);if(put(path,udc))return;
    puts("{\"phase\":\"usb_log\",\"result\":\"GADGET_BOUND\",\"input_commands_enabled\":false}");
    pid_t pid=fork();
    if(pid==0) {
        int dest=-1;
        for(int tries=0;tries<50;tries++) {dest=open("/dev/ttyGS0",O_WRONLY|O_NOCTTY|O_NONBLOCK|O_CLOEXEC);if(dest>=0)break;usleep(100000);}
        int src=open("/dev/kmsg",O_RDONLY|O_NONBLOCK|O_CLOEXEC);if(dest<0||src<0)_exit(1);
        char buf[8192];uint64_t until=now_ns()+120000000000ULL;
        while(now_ns()<until) {
            ssize_t n=read(src,buf,sizeof(buf));
            if(n>0) {
                /* Forward only this collector's bounded JSON, never raw driver
                 * logs that may contain unit identifiers or network addresses. */
                char *message=memchr(buf,';',(size_t)n);
                const char tag[]="iLinux31ah ";
                if(message && (size_t)(buf+n-message)>sizeof(tag)) {
                    message++;
                    if(!memcmp(message,tag,sizeof(tag)-1)) {
                        message+=sizeof(tag)-1;
                        (void)write(dest,message,(size_t)(buf+n-message));
                    }
                }
            } else usleep(20000);
        }
        _exit(0);
    }
}
static void phase_marker(const char *message) {
    printf("{\"phase\":\"%s\",\"monotonic_ns\":%llu}\n",message,(unsigned long long)now_ns());fflush(stdout);
}
static void inventory(void) {
    char b[4096];
    if(read_file("/sys/devices/system/cpu/online",b,sizeof(b))>0) {
        b[strcspn(b,"\r\n")]=0;
        if(strspn(b,"0123456789,-")==strlen(b))printf("{\"phase\":\"cpu_online\",\"value\":\"%s\"}\n",b);
    }
    DIR *dir=opendir("/sys/class/net");struct dirent *ent;
    if(dir) {while((ent=readdir(dir)))if(ent->d_name[0]!='.'&&clean_name(ent->d_name))printf("{\"phase\":\"network_inventory\",\"interface\":\"%s\",\"addresses_collected\":false}\n",ent->d_name);closedir(dir);}
    dir=opendir("/sys/block");
    if(dir) {while((ent=readdir(dir)))if(!strncmp(ent->d_name,"nvme",4)&&clean_name(ent->d_name))printf("{\"phase\":\"storage_inventory\",\"device\":\"%s\",\"opened\":false,\"mounted\":false}\n",ent->d_name);closedir(dir);}
    if(read_file("/proc/device-tree/chosen/aurora,ctxr-exec-window",b,sizeof(b))==16) {
        uint64_t size=0;for(int i=8;i<16;i++)size=(size<<8)|(unsigned char)b[i];
        printf("{\"phase\":\"exec_window\",\"bytes\":%llu,\"base_collected\":false}\n",(unsigned long long)size);
    }
}
static void frequency_inventory(void) {
    DIR *dir=opendir("/sys/devices/system/cpu/cpufreq");struct dirent *ent;
    if(!dir) {puts("{\"phase\":\"cpufreq_inventory\",\"result\":\"NO_POLICIES\"}");return;}
    while((ent=readdir(dir))) {
        if(strncmp(ent->d_name,"policy",6) || !ent->d_name[6] || strspn(ent->d_name+6,"0123456789")!=strlen(ent->d_name+6))continue;
        if(!clean_name(ent->d_name))continue;
        const char *fields[]={"related_cpus","scaling_cur_freq","cpuinfo_cur_freq","scaling_min_freq","scaling_max_freq","scaling_governor"};
        for(unsigned i=0;i<sizeof(fields)/sizeof(fields[0]);i++) {
            char path[256],value[256];
            snprintf(path,sizeof(path),"/sys/devices/system/cpu/cpufreq/%.100s/%s",ent->d_name,fields[i]);
            if(read_file(path,value,sizeof(value))<=0)continue;
            value[strcspn(value,"\r\n")]=0;
            if(!*value || strspn(value,"0123456789abcdefghijklmnopqrstuvwxyz_- ")!=strlen(value))continue;
            printf("{\"phase\":\"cpufreq_inventory\",\"policy\":\"%s\",\"field\":\"%s\",\"value\":\"%s\",\"hardware_clock_verified\":false}\n",ent->d_name,fields[i],value);
        }
    }
    closedir(dir);
}
static void core_inventory(void) {
    cpu_set_t allowed;if(sched_getaffinity(0,sizeof(allowed),&allowed))return;
    int count=0;
    for(int cpu=0;cpu<CPU_SETSIZE && count<MAX_WORKERS;cpu++)if(CPU_ISSET(cpu,&allowed)) {
        count++;char path[256],value[128];
        snprintf(path,sizeof(path),"/sys/devices/system/cpu/cpu%d/of_node/reg",cpu);
        if(read_file(path,value,sizeof(value))==8) {
            uint64_t affinity=0;for(int i=0;i<8;i++)affinity=(affinity<<8)|(unsigned char)value[i];
            printf("{\"phase\":\"core_inventory\",\"cpu\":%d,\"dt_mpidr\":\"0x%llx\"}\n",cpu,(unsigned long long)affinity);
        }
        const char *fields[]={"cpu_capacity","regs/identification/midr_el1"};
        for(unsigned i=0;i<sizeof(fields)/sizeof(fields[0]);i++) {
            snprintf(path,sizeof(path),"/sys/devices/system/cpu/cpu%d/%s",cpu,fields[i]);
            if(read_file(path,value,sizeof(value))<=0)continue;
            value[strcspn(value,"\r\n")]=0;
            if(!*value || strspn(value,"0123456789abcdefABCDEFx")!=strlen(value))continue;
            printf("{\"phase\":\"core_inventory\",\"cpu\":%d,\"field\":\"%s\",\"value\":\"%s\"}\n",cpu,fields[i],value);
        }
    }
}
static int selftest(void) {
    uint64_t x=17;
    for(uint64_t i=0;i<10000;i++) {if(advance(17,i)!=x)return 1;x=x*mult+1;}
    if(clean_name("../escape") || clean_name("bad name") || !clean_name("2a2280000.usb"))return 1;
    int rc=per_cpu(2,0);
    printf("{\"scope\":\"GENERIC_LINUX_CONTROL\",\"selftest\":\"%s\",\"physical_m5_claim\":false}\n",rc?"FAIL":"PASS");
    return rc;
}
static int timeout_selftest(void) {
    simulate_stall=1;
    int rc=per_cpu(2,0);
    int expected=rc && observed.timed_out>0 && observed.passed==0;
    printf("{\"scope\":\"GENERIC_LINUX_TIMEOUT_CONTROL\",\"expected_timeout_observed\":%s,\"selftest\":\"%s\",\"physical_m5_claim\":false}\n",expected?"true":"false",expected?"PASS":"FAIL");
    return expected?0:1;
}
static void camera_summary(int seconds) {
    const char *worker=observed.worker_result<0?"NOT_RUN":observed.worker_result==0?"PASS":observed.worker_result==2?"TIMEOUT":"FAIL";
    const char *timer=observed.timer_failures?"FAIL":observed.created && observed.timers_checked==observed.created?"PASS":"INCOMPLETE";
    const char *memory=observed.memory_result<0?"NOT_RUN":observed.memory_result?"FAIL":"PASS";
    printf("{\"phase\":\"camera_summary\",\"seconds\":%d,\"cpu\":\"%s\",\"passed\":%d,\"workers\":%d,\"expected\":%d,\"timers\":\"%s\",\"ram\":\"%s\",\"overlap_ns\":%llu,\"parity\":false}\n",seconds,worker,observed.passed,observed.created,observed.expected,timer,memory,(unsigned long long)observed.overlap_ns);
}
int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IOLBF,0);
    if(argc==2 && !strcmp(argv[1],"--selftest"))return selftest();
    if(argc==2 && !strcmp(argv[1],"--selftest-timeout"))return timeout_selftest();
    if(getpid()!=1) {fputs("Run only as init or with --selftest\n",stderr);return 2;}
    mkdir("/proc",0555);mkdir("/sys",0555);mkdir("/dev",0755);mkdir("/run",0700);
    if(mount("proc","/proc","proc",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))return 3;
    if(mount("sysfs","/sys","sysfs",MS_NOSUID|MS_NODEV|MS_NOEXEC,NULL))return 3;
    if(mount("devtmpfs","/dev","devtmpfs",MS_NOSUID,NULL))return 3;
    if(mount("tmpfs","/run","tmpfs",MS_NOSUID|MS_NODEV,"mode=0700,size=16m"))return 3;
    int con=open("/dev/console",O_WRONLY|O_NOCTTY);if(con>=0){dup2(con,1);dup2(con,2);if(con>2)close(con);}
    int native=compatible_has("apple,j716c") && compatible_has("apple,t6050");
    int vm=cmdline_has("ilinux31ah.vmcontrol=1");
    if(!native && !vm) {puts("{\"result\":\"REFUSED_WRONG_BOARD\"}");for(;;)pause();}
    log_fd=open("/dev/kmsg",O_WRONLY|O_NONBLOCK|O_CLOEXEC);
    puts(native?"{\"scope\":\"J716C_RAM_DIAGNOSTIC\",\"storage_mounts\":false}":"{\"scope\":\"GENERIC_VM_CONTROL\",\"physical_m5_claim\":false}");
    phase_marker("PID1_ENTERED");
    if(native)gadget_log();
    inventory();core_inventory();frequency_inventory();phase_marker("WORKERS_START");
    int rc=per_cpu(0,native?18:0);phase_marker(rc?"WORKERS_FAILED":"WORKERS_DONE");
    memory_smoke();
    frequency_inventory();
    for(int tick=0;tick<60;tick++) {
        if(tick%5==0)camera_summary(tick);
        printf("{\"phase\":\"heartbeat\",\"seconds\":%d,\"monotonic_ns\":%llu}\n",tick,(unsigned long long)now_ns());
        while(waitpid(-1,NULL,WNOHANG)>0){}
        sleep(1);
    }
    camera_summary(60);
    phase_marker("COLLECTION_COMPLETE_NO_REBOOT");
    for(;;)pause();
}
