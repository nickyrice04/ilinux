/* Execute the actual patched platform wrapper across success/error paths. */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <errno.h>
#define EPROBE_DEFER 517
#define unlikely(x) (x)
#define PD_FLAG_ATTACH_POWER_ON 1
#define PD_FLAG_DETACH_POWER_OFF 2
struct platform_device { int unused; } pdev;
struct platform_driver { int (*probe)(struct platform_device *); bool prevent_deferred_probe; } driver;
struct device { void *driver,*of_node; } device;
#define to_platform_driver(x) (&driver)
#define to_platform_device(x) (&pdev)
static int clk_result,domain_result,probe_result;
static unsigned int clocks,domains,probes,warnings,phase;
static void ilinux_probe_path_mark(struct device *d,unsigned int p) {assert(d==&device);phase=p;}
static int platform_probe_fail(struct platform_device *d) {(void)d;assert(0);return 0;}
static int of_clk_set_defaults(void *n,bool critical) {(void)n;assert(!critical && phase==0x61);clocks++;return clk_result;}
static int dev_pm_domain_attach(struct device *d,unsigned int f) {assert(d==&device && f==3 && phase==0x62);domains++;return domain_result;}
static int real_probe(struct platform_device *d) {assert(d==&pdev && phase==0x63);probes++;return probe_result;}
static void dev_warn(struct device *d,const char *m) {(void)m;assert(d==&device);warnings++;}
#include "tested-platform.h"
static void reset(void){clk_result=domain_result=probe_result=0;clocks=domains=probes=warnings=phase=0;driver.probe=real_probe;driver.prevent_deferred_probe=false;}
int main(void){
 reset();assert(!platform_probe(&device) && clocks==1 && domains==1 && probes==1 && phase==0x65);
 reset();driver.probe=platform_probe_fail;assert(platform_probe(&device)==-ENXIO && !clocks && !domains && !probes);
 reset();clk_result=-EINVAL;assert(platform_probe(&device)==-EINVAL && clocks==1 && !domains && !probes && phase==0x61);
 reset();domain_result=-EPROBE_DEFER;assert(platform_probe(&device)==-EPROBE_DEFER && clocks==1 && domains==1 && !probes);
 reset();probe_result=-EIO;assert(platform_probe(&device)==-EIO && probes==1 && !warnings);
 reset();probe_result=-EPROBE_DEFER;assert(platform_probe(&device)==-EPROBE_DEFER && probes==1 && !warnings);
 reset();probe_result=-EPROBE_DEFER;driver.prevent_deferred_probe=true;assert(platform_probe(&device)==-ENXIO && probes==1 && warnings==1);
 reset();driver.probe=NULL;assert(!platform_probe(&device) && domains==1 && !probes);
 puts("PASS: eight actual platform-probe flows preserve callbacks, returns and deferral semantics");
}
