/* usb-pipe.h: options and exit codes shared by the command line and the USB backend. */
#ifndef USB_PIPE_H
#define USB_PIPE_H
#include <stdio.h>

#define USB_PIPE_VERSION "1 (2026-10-16)"

/* The device, fixed in the code: the M5's RAM-root gadget as usb-gadget.sh creates it
 * (omarchy-arm64/ram-root/overlay/usr/local/lib/ilinux/usb-gadget.sh). Interface 0 is the
 * journal (the bulk-log reader's), interface 1 the SSH byte pipe. */
#define USB_PIPE_VENDOR_ID 0x1d6b
#define USB_PIPE_PRODUCT_ID 0x0104
#define USB_PIPE_BCD_DEVICE 0x0039
#define USB_PIPE_INTERFACE 1
#define USB_PIPE_CONFIGURATION 1
#define USB_PIPE_INTERFACE_CLASS 0xff
#define USB_PIPE_INTERFACES_IN_CONFIGURATION 2
#define USB_PIPE_PRODUCT_PREFIX "iLinux J716c control channel, port "

struct usb_pipe_options {
    int port;              /* 1..3, or 0 for any (one match required) */
    int wait_s;            /* wait for the device */
    int banner_wait_ms;    /* wait for sshd's banner before relaying; 0 = relay at once */
    int quiet_ms;          /* stale bytes before the banner are dropped after this silence */
    int write_timeout_s;   /* a write the M5 does not accept within this ends the session */
    int dry_run;           /* find and check the device, print it, open nothing */
};

enum usb_pipe_exit {
    USB_PIPE_EXIT_OK = 0,
    USB_PIPE_EXIT_SSH = 1,        /* writing to ssh failed */
    USB_PIPE_EXIT_NO_DEVICE = 2,  /* no matching interface within --wait */
    USB_PIPE_EXIT_OPEN = 3,       /* the interface could not be opened (held by someone else) */
    USB_PIPE_EXIT_IDENTITY = 4,   /* identity or descriptor mismatch, or several candidates */
    USB_PIPE_EXIT_DEVICE = 5,     /* the device failed, stalled or sent no banner */
    USB_PIPE_EXIT_USAGE = 6,      /* refused before touching anything */
};

/* iousbhost.m on macOS; usb-pipe.c's stub elsewhere. */
int usb_pipe_backend_main(const struct usb_pipe_options *o, FILE *log);

#endif
