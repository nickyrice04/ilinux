/* SPDX-License-Identifier: GPL-2.0-only */
/* Linux GPIO numbering is preserved. Reserved pads are never accessed. */
static bool apple_gpio_pin_available(const struct apple_gpio_pinctrl *pctl,
				     unsigned int pin)
{
	return pin < pctl->npins && (!pctl->filter_reserved ||
		(pctl->valid_pins[pin / 32] & BIT(pin % 32)));
}

static u32 apple_gpio_valid_word(const struct apple_gpio_pinctrl *pctl,
				unsigned int first)
{
	u32 mask = 0;
	unsigned int bit;

	for (bit = 0; bit < 32; bit++)
		if (apple_gpio_pin_available(pctl, first + bit))
			mask |= BIT(bit);
	return mask;
}

static int apple_gpio_reserve_range(struct apple_gpio_pinctrl *pctl,
				    unsigned int first, unsigned int count)
{
	unsigned int pin;

	if (!count || first >= pctl->npins || count > pctl->npins - first)
		return -EINVAL;
	/* Reject overlaps before changing the bitmap. */
	for (pin = first; pin < first + count; pin++)
		if (!apple_gpio_pin_available(pctl, pin))
			return -EINVAL;
	for (pin = first; pin < first + count; pin++)
		pctl->valid_pins[pin / 32] &= ~BIT(pin % 32);
	return 0;
}

static bool apple_gpio_reg_accessible(struct device *dev, unsigned int reg)
{
	struct apple_gpio_pinctrl *pctl = dev_get_drvdata(dev);

	return !(reg % 4) && apple_gpio_pin_available(pctl, reg / 4);
}
