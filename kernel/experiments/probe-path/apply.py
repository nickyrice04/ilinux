#!/usr/bin/env python3
"""Apply the pinned boot029 probe-path and readable-panel diagnostic change."""
import hashlib,json
from pathlib import Path
import sys
root=Path(sys.argv[1]); here=Path(__file__).resolve().parent
sources=json.loads((here/'source-sha256.json').read_text())
for n,h in sources.items():
 if hashlib.sha256((root/n).read_bytes()).hexdigest()!=h: raise SystemExit('STOP: source mismatch '+n)
def once(s,a,b):
 if s.count(a)!=1: raise SystemExit('STOP: ambiguous anchor '+repr(a))
 return s.replace(a,b,1)
changes={}
def part(path,signature,transform):
 s=changes.get(path,(root/path).read_text()); a=s.index(signature); b=s.index('\n}\n',a)+3
 changes[path]=s[:a]+transform(s[a:b])+s[b:]
def marks(s,dev,items):
 for code,anchor in items:
  indent=anchor[:len(anchor)-len(anchor.lstrip())]
  s=once(s,'\n'+anchor,'\n'+indent+f'ilinux_probe_path_mark({dev}, 0x{code:02x});\n'+anchor)
 return s
bus='drivers/base/bus.c';dd='drivers/base/dd.c';plat='drivers/base/platform.c'
def bus_patch(s):
 s=once(s,'struct subsys_private *sp = bus_to_subsys(dev->bus);','struct subsys_private *sp;')
 s=once(s,'\tif (!sp)', '\tilinux_probe_path_mark(dev, 0x01);\n\tsp = bus_to_subsys(dev->bus);\n\tif (!sp)')
 s=marks(s,'dev',[(2,'\tdevice_initial_probe(dev);'),(3,'\tmutex_lock(&sp->mutex);'),(4,'\tlist_for_each_entry(sif, &sp->interfaces, node)'),(7,'\tmutex_unlock(&sp->mutex);'),(8,'\tsubsys_put(sp);')])
 s=once(s,'\t\tif (sif->add_dev)\n\t\t\tsif->add_dev(dev, sif);','\t\tif (sif->add_dev) {\n\t\t\tilinux_probe_path_mark(dev, 0x05);\n\t\t\tsif->add_dev(dev, sif);\n\t\t\tilinux_probe_path_mark(dev, 0x06);\n\t\t}')
 return once(s,'\tsubsys_put(sp);','\tsubsys_put(sp);\n\tilinux_probe_path_mark(dev, 0x09);')
part(bus,'void bus_probe_device(struct device *dev)',bus_patch)
def attach(s):
 s=marks(s,'dev',[(0x10,'\tdevice_lock(dev);'),(0x11,'\tif (dev->p->dead) {'),(0x12,'\t\tif (dev->parent)\n\t\t\tpm_runtime_get_sync(dev->parent);'),(0x13,'\t\tret = bus_for_each_drv(dev->bus, NULL, &data,'),(0x14,'\t\tif (!ret && allow_async && data.have_async) {'),(0x15,'\t\t\tpm_request_idle(dev);'),(0x16,'\t\tif (dev->parent)\n\t\t\tpm_runtime_put(dev->parent);'),(0x17,'\tdevice_unlock(dev);'),(0x18,'\tif (async)'),(0x19,'\treturn ret;')])
 return s
part(dd,'static int __device_attach(struct device *dev, bool allow_async)',attach)
part(dd,'static int __device_attach_driver(struct device_driver *drv, void *_data)',lambda s: marks(s,'dev',[(0x20,'\tret = driver_match_device(drv, dev);'),(0x21,'\tif (ret == 0) {'),(0x22,'\tret = driver_probe_device(drv, dev);')]).replace('\tret = driver_probe_device(drv, dev);','\tret = driver_probe_device(drv, dev);\n\tilinux_probe_path_mark(dev, 0x23);'))
part(dd,'static int __driver_probe_device(const struct device_driver *drv, struct device *dev)',lambda s: marks(s,'dev',[(0x30,'\tif (dev->p->dead || !device_is_registered(dev))'),(0x31,'\tpm_runtime_get_suppliers(dev);'),(0x32,'\tif (dev->parent)\n\t\tpm_runtime_get_sync(dev->parent);'),(0x33,'\tpm_runtime_barrier(dev);'),(0x34,'\tif (initcall_debug)'),(0x35,'\tpm_request_idle(dev);'),(0x36,'\tif (dev->parent)\n\t\tpm_runtime_put(dev->parent);'),(0x37,'\tpm_runtime_put_suppliers(dev);'),(0x38,'\treturn ret;')]))
part(dd,'static int really_probe(struct device *dev, const struct device_driver *drv)',lambda s: marks(s,'dev',[(0x40,'\tlink_ret = device_links_check_suppliers(dev);'),(0x41,'\tdevice_set_driver(dev, drv);'),(0x42,'\tret = pinctrl_bind_pins(dev);'),(0x43,'\t\tret = dev->bus->dma_configure(dev);'),(0x44,'\tret = driver_sysfs_add(dev);'),(0x45,'\t\tret = dev->pm_domain->activate(dev);'),(0x46,'\tret = call_driver_probe(dev, drv);'),(0x47,'\tret = device_add_groups(dev, drv->dev_groups);'),(0x48,'\tpinctrl_init_done(dev);'),(0x49,'\tif (dev->pm_domain && dev->pm_domain->sync)'),(0x4a,'\tdriver_bound(dev);'),(0x4b,'\treturn ret;'),(0x4c,'\tdevice_remove(dev);'),(0x4d,'\tdriver_sysfs_remove(dev);'),(0x4e,'\tbus_notify(dev, BUS_NOTIFY_DRIVER_NOT_BOUND);'),(0x4f,'\tif (dev->bus && dev->bus->dma_cleanup)'),(0x50,'\tdevice_links_no_driver(dev);'),(0x51,'\tdevice_unbind_cleanup(dev);')]))
part(plat,'static int platform_probe(struct device *_dev)',lambda s: marks(s,'_dev',[(0x60,'\tif (unlikely(drv->probe == platform_probe_fail))'),(0x61,'\tret = of_clk_set_defaults(_dev->of_node, false);'),(0x62,'\tret = dev_pm_domain_attach(_dev, PD_FLAG_ATTACH_POWER_ON |'),(0x63,'\tif (drv->probe)'),(0x64,'\tif (drv->prevent_deferred_probe && ret == -EPROBE_DEFER) {'),(0x65,'\treturn ret;')]))
for n in (bus,plat):
 s=changes[n];a=s.index('\n/**')
 changes[n]=s[:a]+'\nextern void ilinux_probe_path_mark(struct device *dev, unsigned int phase);\n'+s[a:]
# Update the same helper, preserving its tested clock/watchdog/scheduler code.
n='drivers/base/ilinux_probe_diag.h';s=(root/n).read_text()
s=once(s,'static int __init ilinux_probe_setup', '#include "ilinux-path-state.h"\n\nstatic int __init ilinux_probe_setup')
s=once(s,'\trate = arch_timer_get_rate();','\tilinux_probe_identity_init();\n\trate = arch_timer_get_rate();')
s=once(s,'\tif (entering)\n\t\tWRITE_ONCE(ilinux_probe_device, ilinux_probe_device + 1);','\tif (entering) {\n\t\tilinux_probe_path_start(dev);\n\t\tWRITE_ONCE(ilinux_probe_device, ilinux_probe_device + 1);\n\t} else {\n\t\tWRITE_ONCE(ilinux_probe_owner, NULL);\n\t}')
s=once(s,'\ttimer_shutdown_sync(&ilinux_probe_watch);','\ttimer_shutdown_sync(&ilinux_probe_watch);\n\tilinux_probe_identity_end();')
s=once(s,'\tpr_info("ilinux-probe: heartbeat=%u', '\tilinux_probe_fb_mark(3, ilinux_probe_heartbeats + 1);\n\tpr_info("ilinux-probe: heartbeat=%u')
changes[n]=s
n='drivers/firmware/efi/ilinux-fb-map.h';s=(root/n).read_text()
s=s.replace('fb_font->height * 6 > fb_height','(ILINUX_PANEL_ROWS * ILINUX_STRIP_SCALE + 6) * fb_font->height > fb_height')
s=s.replace('20 * fb_font->width * ILINUX_STRIP_SCALE','ILINUX_PANEL_COLS * fb_font->width * ILINUX_STRIP_SCALE')
s=s.replace('fb_height - fb_font->height * ILINUX_STRIP_SCALE','fb_height - ILINUX_PANEL_ROWS * fb_font->height * ILINUX_STRIP_SCALE')
s=s.replace('lane < 4','lane < 7');changes[n]=s
# All original digests and anchors have been checked before writes.
for n,s in changes.items(): (root/n).write_text(s)
for src,dst in [('path-state.h','drivers/base/ilinux-path-state.h'),('device-identities.h','drivers/base/ilinux-device-identities.h'),('status-panel.h','drivers/firmware/efi/ilinux-status-strip.h')]:
 (root/dst).write_bytes((here/src).read_bytes())
print('PASS: bounded task-attributed probe checkpoints and compact panel applied')
