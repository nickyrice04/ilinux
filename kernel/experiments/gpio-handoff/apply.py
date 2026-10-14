#!/usr/bin/env python3
"""Apply a digest-pinned, t6050-only GPIO handoff repair to boot030."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]); here=Path(__file__).resolve().parent
p=root/'drivers/pinctrl/pinctrl-apple-gpio.c'
expected=json.loads((here/'source-sha256.json').read_text())
for name,digest in expected.items():
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
  raise SystemExit('STOP: source differs '+name)
s=p.read_text()
def once(a,b):
 global s
 if s.count(a)!=1: raise SystemExit('STOP: ambiguous anchor '+repr(a))
 s=s.replace(a,b,1)
once('/* Probe & register */','''/* Probe & register */
extern void ilinux_probe_path_mark(struct device *dev, unsigned int phase);
#include "ilinux-gpio-irq-init.h"''')
once('\t\tgirq->parent_handler = apple_gpio_irq_handler;', '''\t\tgirq->parent_handler = apple_gpio_irq_handler;
		if (of_device_is_compatible(pctl->dev->of_node, "apple,t6050-pinctrl"))
			girq->init_hw = apple_gpio_t6050_irq_init_hw;''')
once('\tunsigned int npins;', '''\tunsigned int npins;
	struct regmap_config config = regmap_config;
	bool t6050 = of_device_is_compatible(pdev->dev.of_node, "apple,t6050-pinctrl");''')
once('\tpins = devm_kmalloc_array', '''\t/* Validate before allocations and before any controller MMIO. */
	if (t6050) {
		struct resource *r = platform_get_resource(pdev, IORESOURCE_MEM, 0);

		if (!npins || npins > 512 || nirqs > 7 || !r ||
		    resource_size(r) < REG_GPIO(npins) ||
		    (nirqs && resource_size(r) < REG_IRQ(nirqs - 1, npins - 1) + 4))
			return dev_err_probe(&pdev->dev, -EINVAL, "invalid t6050 GPIO geometry\\n");
		/* Cache only DT-declared pins; do not read absent pin registers. */
		config.max_register = REG_GPIO(npins - 1);
		config.num_reg_defaults_raw = npins;
	}

	pins = devm_kmalloc_array''')
once('&regmap_config);','&config);')
# Boundaries preserve existing operations/errors; no new blacklist.
items=[(0x70,'\tif (of_property_read_bool(pdev->dev.of_node, "interrupt-controller")) {','&pdev->dev'),(0x71,'\tpctl = devm_kzalloc','&pdev->dev'),(0x72,'\tpctl->base = devm_platform_ioremap_resource','&pdev->dev'),(0x73,'\tpctl->map = devm_regmap_init_mmio','&pdev->dev'),(0x75,'\tpctl->pctldev =','&pdev->dev'),(0x78,'\treturn apple_gpio_register(pctl);','&pdev->dev'),(0x79,'\t\tfor (i = 0; i < girq->num_parents; i++) {','pctl->dev'),(0x7a,'\tret = devm_gpiochip_add_data','pctl->dev'),(0x7b,'\nout_free_irq_data:','pctl->dev')]
for code,anchor,dev in items:
 # Match whole line prefix but preserve trailing call text.
 ind=anchor[:len(anchor)-len(anchor.lstrip('\t'))]
 if anchor.startswith('\n'):
  once(anchor, '\n\tilinux_probe_path_mark('+dev+', 0x'+format(code,'02x')+');\n'+anchor)
 else:
  once(anchor,ind+'ilinux_probe_path_mark('+dev+', 0x'+format(code,'02x')+');\n'+anchor)
# Two distinct loops, avoiding per-pin render overhead.
once('\tfor (i = 0; i < npins; i++) {\n\t\tpins[i].number', '\tilinux_probe_path_mark(&pdev->dev, 0x74);\n\tfor (i = 0; i < npins; i++) {\n\t\tpins[i].number')
once('\tfor (i = 0; i < npins; i++) {\n\t\tres = pinctrl_generic_add_group','\tilinux_probe_path_mark(&pdev->dev, 0x76);\n\tfor (i = 0; i < npins; i++) {\n\t\tres = pinctrl_generic_add_group')
once('\tfor (i = 0; i < ARRAY_SIZE(pinmux_functions); ++i)', '\tilinux_probe_path_mark(&pdev->dev, 0x77);\n\tfor (i = 0; i < ARRAY_SIZE(pinmux_functions); ++i)')
p.write_text(s)
(p.parent/'ilinux-gpio-irq-init.h').write_bytes((here/'irq-init.h').read_bytes())
print('PASS: t6050-only GPIO geometry/cache/IRQ handoff and probe boundaries applied')
