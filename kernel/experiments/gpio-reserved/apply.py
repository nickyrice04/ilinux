#!/usr/bin/env python3
"""Apply reserved GPIO support to the exact retained boot031 source."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
here = Path(__file__).resolve().parent
for name, digest in json.loads((here / 'source-sha256.json').read_text()).items():
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
        raise SystemExit('STOP: source differs: ' + name)
p = root / 'drivers/pinctrl/pinctrl-apple-gpio.c'
s = p.read_text()


def once(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit('STOP: ambiguous anchor ' + repr(a))
    s = s.replace(a, b, 1)


once('\tu8 irqgrps[];', '\tunsigned int npins;\n\tbool filter_reserved;\n\tu32 valid_pins[16];\n\tu8 irqgrps[];')
once('/* No locking needed', '''extern void ilinux_probe_path_mark(struct device *dev, unsigned int phase);
extern void ilinux_probe_pin_mark(struct device *dev, unsigned int pin);
#include "ilinux-gpio-reserved.h"
#include "ilinux-gpio-cache.h"

/* No locking needed''')
once('\tregmap_update_bits(pctl->map, REG_GPIO(pin), mask, value);', '''	if (!apple_gpio_pin_available(pctl, pin))
		return;
	regmap_update_bits(pctl->map, REG_GPIO(pin), mask, value);''')
once('\tret = regmap_read(pctl->map, REG_GPIO(pin), &val);', '''	if (!apple_gpio_pin_available(pctl, pin))
		return 0;
	ret = regmap_read(pctl->map, REG_GPIO(pin), &val);''')
once('\t\tif (func >= pinmux_generic_get_function_count(pctldev)) {', '\t\tif (!apple_gpio_pin_available(pctl, pin) ||\n\t\t    func >= pinmux_generic_get_function_count(pctldev)) {')
# Reject requests before raw input reads or any side effects. gpiolib also
# consumes gpio-reserved-ranges to remove these lines from its valid mask.
for function, pin, error in [
    ('apple_gpio_pinmux_set', 'group', '-EINVAL'),
    ('apple_gpio_get_direction', 'offset', '-EINVAL'),
    ('apple_gpio_get', 'offset', '-EINVAL'),
    ('apple_gpio_set', 'offset', '-EINVAL'),
    ('apple_gpio_direction_input', 'offset', '-EINVAL'),
    ('apple_gpio_direction_output', 'offset', '-EINVAL'),
    ('apple_gpio_irq_ack', 'data->hwirq', ''),
    ('apple_gpio_irq_mask', 'data->hwirq', ''),
    ('apple_gpio_irq_unmask', 'data->hwirq', ''),
    ('apple_gpio_irq_startup', 'data->hwirq', '0'),
    ('apple_gpio_irq_set_type', 'data->hwirq', '-EINVAL'),
]:
    start = s.index(function + '(')
    end = s.index('\n}', start)
    snippet = s[start:end]
    # First empty line after declarations. Cached get_reg calls already reject
    # unavailable pins; no MMIO takes place during these declarations.
    pos = snippet.index('\n\n', snippet.index('{'))
    replacement = snippet[:pos] + '\n\n\tif (!apple_gpio_pin_available(pctl, ' + pin + '))\n\t\treturn' + (' ' + error if error else '') + ';' + snippet[pos:]
    once(snippet, replacement)
once('\t\tfor_each_set_bit(pinl, &pending, 32)\n\t\t\tgeneric_handle_domain_irq(gc->irq.domain, pinh + pinl);', '''		pending &= apple_gpio_valid_word(pctl, pinh);
		for_each_set_bit(pinl, &pending, 32)
			generic_handle_domain_irq(gc->irq.domain, pinh + pinl);''')
once('\t\t/* Cache only DT-declared pins; do not read absent pin registers. */', '''		/* Validate exclusions before any controller MMIO. */
		pctl->npins = npins;
		pctl->filter_reserved = true;
		for (i = 0; i < npins; i++)
			pctl->valid_pins[i / 32] |= BIT(i % 32);
		ilinux_probe_path_mark(&pdev->dev, 0x90);
		if (of_property_present(pdev->dev.of_node, "gpio-reserved-ranges")) {
			int n = of_property_count_u32_elems(pdev->dev.of_node, "gpio-reserved-ranges");
			u32 first, count;

			if (n <= 0 || n > 1024 || n % 2)
				return -EINVAL;
			for (i = 0; i < n; i += 2) {
				if (of_property_read_u32_index(pdev->dev.of_node,
				    "gpio-reserved-ranges", i, &first) ||
				    of_property_read_u32_index(pdev->dev.of_node,
				    "gpio-reserved-ranges", i + 1, &count))
					return -EINVAL;
				res = apple_gpio_reserve_range(pctl, first, count);
				if (res)
					return res;
			}
		}
		/* Cache only DT-declared pins; do not read absent pin registers. */''')
once('\n\tpins = devm_kmalloc_array', '\n\tpctl->npins = npins;\n\tpins = devm_kmalloc_array')
once('\t\tconfig.max_register = REG_GPIO(npins - 1);', '\t\tconfig.max_register = REG_GPIO(npins - 1);\n\t\tconfig.max_register_is_0 = npins == 1;')
once('\tilinux_probe_path_mark(&pdev->dev, 0x73);', '''	if (t6050) {
		struct reg_default *defaults;

		defaults = devm_kcalloc(&pdev->dev, npins, sizeof(*defaults), GFP_KERNEL);
		if (!defaults)
			return -ENOMEM;
		res = apple_gpio_cache_defaults(pctl, defaults, &config);
		if (res)
			return res;
	}
	ilinux_probe_path_mark(&pdev->dev, 0x73);''')
p.write_text(s)
for source, target in [('reserved-pins.h', 'ilinux-gpio-reserved.h'),
                       ('cache-init.h', 'ilinux-gpio-cache.h'),
                       ('irq-init.h', 'ilinux-gpio-irq-init.h')]:
    (p.parent / target).write_bytes((here / source).read_bytes())
for source, target in [('path-state.h', 'drivers/base/ilinux-path-state.h'),
                       ('status-panel.h', 'drivers/firmware/efi/ilinux-status-strip.h')]:
    (root / target).write_bytes((here / source).read_bytes())
mapping = root / 'drivers/firmware/efi/ilinux-fb-map.h'
m = mapping.read_text()
assert m.count('lane < 7') == 1
mapping.write_text(m.replace('lane < 7', 'lane < 8'))
binding = root / 'Documentation/devicetree/bindings/pinctrl/apple,pinctrl.yaml'
b = binding.read_text()
assert b.count('  gpio-controller: true') == 1
binding.write_text(b.replace('  gpio-controller: true', '  gpio-controller: true\n\n  gpio-reserved-ranges: true'))
print('PASS: reserved pin access/cache/IRQ exclusions and indexed diagnostic panel applied')
