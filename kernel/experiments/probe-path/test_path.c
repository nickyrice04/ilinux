/* Actual attribution/ref-lifetime helper with controlled public-node fixtures. */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
struct task_struct { int id; } task1,task2;
static struct task_struct *current=&task1;
struct device_node { unsigned int refs; } nodes[286],unknown;
struct device { struct device_node *of_node; };
static bool ilinux_probe_active,target=true;
static unsigned int calls,put_count,marks,values[7];
static bool of_machine_is_compatible(const char *s) { (void)s;return target; }
static struct device_node *of_find_node_by_path(const char *s) { assert(s[0]=='/' && calls<286);nodes[calls].refs++;return &nodes[calls++]; }
static void of_node_put(struct device_node *n) { if(n) { assert(n->refs==1);n->refs--;put_count++; } }
static bool ilinux_probe_fb_mark(unsigned int lane,unsigned int value) { assert(lane<7 && value<65536);values[lane]=value;marks++;return true; }
#include "path-state.h"
int main(void)
{
 assert(ARRAY_SIZE(ilinux_probe_nodes)==286);
 target=false;ilinux_probe_identity_init();assert(!calls);
 target=true;ilinux_probe_identity_init();assert(calls==286);
 struct device first={&nodes[0]},last={&nodes[285]},missing={&unknown},no_of={NULL};
 assert(ilinux_probe_id(&first)==1 && ilinux_probe_id(&last)==286);
 assert(!ilinux_probe_id(&missing) && !ilinux_probe_id(&no_of) && !ilinux_probe_id(NULL));
 ilinux_probe_path_start(&first);assert(values[4]==1 && values[5]==0 && values[6]==1);
 unsigned int before=marks;
 ilinux_probe_path_mark(&last,0x62);assert(before==marks); /* inactive */
 ilinux_probe_active=true;current=&task2;ilinux_probe_path_mark(&last,0x62);assert(before==marks); /* other task */
 current=&task1;ilinux_probe_path_mark(&last,0x62);assert(values[4]==1 && values[6]==286 && values[5]==0x62); /* nested device, root preserved */
 ilinux_probe_path_mark(&missing,0x63);assert(values[6]==0 && values[5]==0x63);
 ilinux_probe_identity_end();assert(put_count==286 && !ilinux_probe_owner);
 before=marks;ilinux_probe_path_mark(&last,0x64);assert(before==marks);
 ilinux_probe_identity_end();assert(put_count==286); /* safe cleared refs */
 for(unsigned int i=0;i<286;i++) assert(!nodes[i].refs && !ilinux_probe_nodes[i].node);
 puts("PASS: actual device-ID helper, 286 refs, unknown IDs, task gating, nested attribution and cleanup");
}
