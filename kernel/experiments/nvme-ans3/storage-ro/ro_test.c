// SPDX-License-Identifier: MIT
/*
 * ro_test: PID 1 of the storage set's VM test (kernel/experiments/nvme-ans3/storage-ro/README.md).
 *
 * Boots under Virtualization.framework (vzrun --nvme) on the boot042 Image with a writable virtual
 * NVMe disk, loads the storage set's nvme-core.ko (with the iLinux read-only patch) and nvme.ko (the
 * PCI transport the virtual controller needs), and then tries every way this kernel has to change the
 * disk: write(2), a shared writable mapping, discard, zero-out and secure discard, NVMe passthrough
 * writes, flush, write zeroes and deallocate, the admin commands that change a controller or its media
 * (Format NVM, Sanitize, firmware commit, namespace management, Set Features), and mounting the
 * disk's file systems. The host checks the disk image's SHA-256 before and after.
 *
 * ilinux.rotest=guarded (the default): the storage set's nvme-core, which must first refuse to load
 * with ilinux_read_only=0 (EPERM; its read-only mode cannot be turned off), then loads as built. Every
 * attempt must be refused and the image must not change.
 * ilinux.rotest=control: the VM control build of nvme-core (/lib/modules/nvme-core-control.ko, built
 * with ILINUX_RO_CONTROL, never in the storage set) with ilinux_read_only=0, on a scratch copy of the
 * disk, so the data-path attempts are shown to write when nothing refuses them (the media-changing
 * admin commands are never sent in this mode).
 * One "RO-TEST <check> PASS|FAIL|INFO ..." line per check on the console, then
 * "RO-TEST-RESULT PASS|FAIL <mode> ..."; then the VM powers off.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <linux/nvme_ioctl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/mount.h>
#include <sys/reboot.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <unistd.h>

#define DISK "/dev/nvme0n1"
#define CTRL_DEV "/dev/nvme0"
#define MIB (1024L * 1024L)

static int guarded = 1;
static int failures;

static void say(const char *fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	fflush(stdout);
}

/* one check: ok says whether this mode's expectation held */
static void check(const char *name, int ok, const char *fmt, ...)
{
	char detail[512];
	va_list ap;

	va_start(ap, fmt);
	vsnprintf(detail, sizeof(detail), fmt, ap);
	va_end(ap);
	if (!ok)
		failures++;
	say("RO-TEST %s %s %s\n", name, ok ? "PASS" : "FAIL", detail);
}

static void info(const char *name, const char *fmt, ...)
{
	char detail[512];
	va_list ap;

	va_start(ap, fmt);
	vsnprintf(detail, sizeof(detail), fmt, ap);
	va_end(ap);
	say("RO-TEST %s INFO %s\n", name, detail);
}

static int read_text(const char *path, char *buf, size_t len)
{
	int fd = open(path, O_RDONLY | O_CLOEXEC);
	ssize_t n;

	if (fd < 0)
		return -1;
	n = read(fd, buf, len - 1);
	close(fd);
	if (n < 0)
		return -1;
	buf[n] = 0;
	while (n > 0 && (buf[n - 1] == '\n' || buf[n - 1] == ' '))
		buf[--n] = 0;
	return 0;
}

static int load_module(const char *path, const char *params)
{
	int fd = open(path, O_RDONLY | O_CLOEXEC);
	int rc;

	if (fd < 0)
		return -errno;
	rc = syscall(SYS_finit_module, fd, params, 0);
	rc = rc ? -errno : 0;
	close(fd);
	return rc;
}

/* simple 64-bit FNV-1a, to compare buffers in the log (test data only) */
static uint64_t fnv(const unsigned char *p, size_t n)
{
	uint64_t h = 1469598103934665603ULL;

	while (n--)
		h = (h ^ *p++) * 1099511628211ULL;
	return h;
}

static int direct_read(off_t off, void *buf, size_t len)
{
	int fd = open(DISK, O_RDONLY | O_DIRECT | O_CLOEXEC);
	ssize_t n;

	if (fd < 0)
		return -errno;
	n = pread(fd, buf, len, off);
	close(fd);
	return n == (ssize_t)len ? 0 : (n < 0 ? -errno : -EIO);
}

/* a data-path write attempt: guarded expects a refusal, control a write */
static void expect_write(const char *name, int rc, int err)
{
	if (guarded)
		check(name, rc < 0, "%s", rc < 0 ? strerror(err) : "the write was accepted");
	else
		check(name, rc >= 0, "%s", rc >= 0 ? "written (no guard)" : strerror(err));
}

static int nvme_cmd(int fd, unsigned long req, uint8_t opcode, uint32_t nsid, void *data,
		    uint32_t len, uint32_t cdw10, uint32_t cdw11, uint32_t cdw12, int *err)
{
	struct nvme_passthru_cmd c;
	int rc;

	memset(&c, 0, sizeof(c));
	c.opcode = opcode;
	c.nsid = nsid;
	c.addr = (uint64_t)(uintptr_t)data;
	c.data_len = len;
	c.cdw10 = cdw10;
	c.cdw11 = cdw11;
	c.cdw12 = cdw12;
	c.timeout_ms = 10000;
	rc = ioctl(fd, req, &c);
	*err = errno;
	return rc;	/* <0: kernel refused (errno), 0: success, >0: NVMe status from the controller */
}

/* an admin command that would change the controller or its media: refused before the controller in
 * guarded mode (ioctl -1, EOPNOTSUPP); never sent in control mode */
static void refused_admin(int ctrl, const char *name, uint8_t opcode, uint32_t nsid, uint32_t cdw10,
			  uint32_t cdw11)
{
	int err, rc;

	if (!guarded) {
		info(name, "not sent in control mode");
		return;
	}
	rc = nvme_cmd(ctrl, NVME_IOCTL_ADMIN_CMD, opcode, nsid, NULL, 0, cdw10, cdw11, 0, &err);
	check(name, rc < 0 && err == EOPNOTSUPP, "opcode 0x%02x: %s", opcode,
	      rc < 0 ? strerror(err) : rc ? "the controller saw it (NVMe status)" : "the controller accepted it");
	usleep(600000);	/* the refusal lines are rate limited (10 per 5 s) */
}

static void kmsg_lines(void)
{
	static const char *const keys[] = { "nvme", "iLinux", "read-only", "Trying to write", "EXT4",
					    "FAT-fs", "blk_update_request", "I/O error", NULL };
	char line[1024];
	int fd = open("/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
	ssize_t n;

	if (fd < 0)
		return;
	while ((n = read(fd, line, sizeof(line) - 1)) > 0 || (n < 0 && errno == EPIPE)) {
		char *msg;

		if (n <= 0)
			continue;
		line[n] = 0;
		msg = strchr(line, ';');
		msg = msg ? msg + 1 : line;
		for (int i = 0; keys[i]; i++)
			if (strstr(msg, keys[i])) {
				say("RO-TEST-KMSG %s", msg);
				break;
			}
	}
	close(fd);
}

static void try_mount(const char *name, const char *dev, const char *type)
{
	struct statvfs st;
	int fd, rc;

	mkdir("/mnt", 0755);
	rc = mount(dev, "/mnt", type, 0, NULL);
	if (rc < 0 && (errno == EACCES || errno == EROFS)) {
		int first = errno;

		/* what mount(8) does next on a write-protected device */
		rc = mount(dev, "/mnt", type, MS_RDONLY, NULL);
		info(name, "read-write mount refused (%s); read-only mount: %s", strerror(first),
		     rc < 0 ? strerror(errno) : "done");
	}
	if (rc < 0) {
		if (guarded)
			check(name, 1, "%s mount of %s failed: %s (nothing mounted)", type, dev, strerror(errno));
		else
			check(name, 0, "%s mount of %s failed in control mode: %s", type, dev, strerror(errno));
		return;
	}
	statvfs("/mnt", &st);
	fd = open("/mnt/ilinux-written", O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
	if (guarded)
		check(name, (st.f_flag & ST_RDONLY) && fd < 0, "%s mounted %s; creating a file: %s", type,
		      (st.f_flag & ST_RDONLY) ? "read-only" : "READ-WRITE", fd < 0 ? strerror(errno) : "created");
	else
		check(name, fd >= 0, "%s mounted %s; creating a file: %s", type,
		      (st.f_flag & ST_RDONLY) ? "read-only" : "read-write", fd < 0 ? strerror(errno) : "created");
	if (fd >= 0) {
		if (write(fd, "x\n", 2) < 0)
			info(name, "write: %s", strerror(errno));
		close(fd);
	}
	umount("/mnt");
}

int main(void)
{
	char text[4096], mode[32] = "guarded", *p;
	unsigned char *orig, *buf;
	long lbs = 512;
	int fd, ctrl, rc, err, nsid = 1, i;

	mkdir("/proc", 0755);
	mkdir("/sys", 0755);
	mkdir("/dev", 0755);
	mount("proc", "/proc", "proc", 0, NULL);
	mount("sysfs", "/sys", "sysfs", 0, NULL);
	mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);
	fd = open("/dev/console", O_RDWR);
	if (fd >= 0) {
		dup2(fd, 0);
		dup2(fd, 1);
		dup2(fd, 2);
	}
	if (read_text("/proc/cmdline", text, sizeof(text)) == 0 && (p = strstr(text, "ilinux.rotest=")))
		sscanf(p + 14, "%31[a-z]", mode);
	guarded = strcmp(mode, "control") != 0;
	say("RO-TEST start: mode %s\n", guarded ? "guarded" : "control");

	if (guarded) {
		/* the shipped module cannot be loaded with its read-only mode off */
		rc = load_module("/lib/modules/nvme-core.ko", "ilinux_read_only=0");
		check("refuse-off", rc == -EPERM && access("/sys/module/nvme_core", F_OK),
		      "loading with ilinux_read_only=0: %s", rc ? strerror(-rc) : "loaded");
		rc = load_module("/lib/modules/nvme-core.ko", "");
	} else {
		rc = load_module("/lib/modules/nvme-core-control.ko", "ilinux_read_only=0");
	}
	check("load-nvme-core", rc == 0, "%s%s", guarded ? "" : "control build: ", rc ? strerror(-rc) : "loaded");
	rc = load_module("/lib/modules/nvme.ko", "");
	check("load-nvme-pci", rc == 0, "%s", rc ? strerror(-rc) : "loaded");
	if (read_text("/sys/module/nvme_core/parameters/ilinux_read_only", text, sizeof(text)) == 0)
		check("param", strcmp(text, guarded ? "Y" : "N") == 0, "ilinux_read_only=%s", text);
	else
		check("param", 0, "no /sys/module/nvme_core/parameters/ilinux_read_only");

	for (i = 0; i < 600 && access("/sys/block/nvme0n1/nvme0n1p3", F_OK); i++)
		usleep(100000);
	check("disk", access(DISK, F_OK) == 0 && access("/sys/block/nvme0n1/nvme0n1p3", F_OK) == 0,
	      "%s and three partitions after %.1f s", DISK, i / 10.0);
	if (access(DISK, F_OK))
		goto out;
	if (read_text("/sys/block/nvme0n1/queue/logical_block_size", text, sizeof(text)) == 0)
		lbs = atol(text);

	/* the read-only flags, as the kernel reports them */
	for (i = 0; i <= 3; i++) {
		char path[128], name[32];

		if (i) {
			snprintf(path, sizeof(path), "/sys/block/nvme0n1/nvme0n1p%d/ro", i);
			snprintf(name, sizeof(name), "ro-flag-p%d", i);
		} else {
			snprintf(path, sizeof(path), "/sys/block/nvme0n1/ro");
			snprintf(name, sizeof(name), "ro-flag-disk");
		}
		if (read_text(path, text, sizeof(text)))
			strcpy(text, "?");
		check(name, strcmp(text, guarded ? "1" : "0") == 0, "%s = %s", path, text);
	}
	fd = open(DISK, O_RDONLY | O_CLOEXEC);
	if (fd >= 0) {
		int ro = -1;

		ioctl(fd, BLKROGET, &ro);
		check("blkroget", ro == (guarded ? 1 : 0), "BLKROGET %d", ro);
		close(fd);
	}

	/* reads work */
	if (posix_memalign((void **)&orig, 4096, MIB) || posix_memalign((void **)&buf, 4096, MIB))
		goto out;
	rc = direct_read(0, orig, MIB);
	check("read", rc == 0, "first MiB, O_DIRECT: %s, fnv %016llx", rc ? strerror(-rc) : "read",
	      (unsigned long long)fnv(orig, MIB));

	/* write(2) */
	memset(buf, 0x5a, 4096);
	fd = open(DISK, O_RDWR | O_CLOEXEC);
	info("open-rdwr", "%s", fd < 0 ? strerror(errno) : "opened (writes are refused later, not at open)");
	if (fd >= 0) {
		rc = pwrite(fd, buf, 4096, 8 * MIB);
		err = errno;
		expect_write("pwrite", rc, err);
		if (guarded) {
			int zero = 0;

			rc = ioctl(fd, BLKROSET, &zero);
			info("blkroset-0", "BLKROSET 0 (as root): %s", rc ? strerror(errno) : "accepted");
			rc = pwrite(fd, buf, 4096, 8 * MIB);
			err = errno;
			expect_write("pwrite-after-blkroset", rc, err);
		}
		close(fd);
	}

	/* a shared writable mapping: page-cache writeback reaches the driver even on a read-only disk */
	rc = direct_read(9 * MIB, orig, 4096);
	fd = open(DISK, O_RDWR | O_CLOEXEC);
	if (fd >= 0 && rc == 0) {
		unsigned char *map = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 9 * MIB);

		if (map == MAP_FAILED) {
			check("mmap-write", guarded, "mmap PROT_WRITE: %s", strerror(errno));
		} else {
			memset(map, 0xa5, 4096);
			rc = msync(map, 4096, MS_SYNC);
			err = errno;
			munmap(map, 4096);
			fsync(fd);
			close(fd);
			fd = -1;
			info("msync", "%s", rc ? strerror(err) : "returned 0");
			rc = direct_read(9 * MIB, buf, 4096);
			if (guarded)
				check("mmap-write", rc == 0 && memcmp(buf, orig, 4096) == 0,
				      "the disk still holds the original bytes at 9 MiB (fnv %016llx)",
				      (unsigned long long)fnv(buf, 4096));
			else
				check("mmap-write", rc == 0 && buf[0] == 0xa5 && buf[4095] == 0xa5,
				      "the disk now holds the mapped bytes at 9 MiB");
		}
	}
	if (fd >= 0)
		close(fd);

	/* discard, zero-out, secure discard */
	fd = open(DISK, O_RDWR | O_CLOEXEC);
	if (fd >= 0) {
		uint64_t range[2];

		range[0] = 10 * MIB;
		range[1] = MIB;
		rc = ioctl(fd, BLKDISCARD, range);
		err = errno;
		if (!guarded && rc < 0 && err == EOPNOTSUPP)
			info("blkdiscard", "the virtual controller does not support discard");
		else
			expect_write("blkdiscard", rc, err);
		range[0] = 11 * MIB;
		rc = ioctl(fd, BLKZEROOUT, range);
		err = errno;
		expect_write("blkzeroout", rc, err);
		range[0] = 12 * MIB;
		rc = ioctl(fd, BLKSECDISCARD, range);
		err = errno;
		if (!guarded && rc < 0 && err == EOPNOTSUPP)
			info("blksecdiscard", "the virtual controller does not support secure discard");
		else
			expect_write("blksecdiscard", rc, err);
		close(fd);
	}

	/* NVMe passthrough on the namespace (opened read-only: the guard, not the open mode, decides) */
	fd = open(DISK, O_RDONLY | O_CLOEXEC);
	if (fd >= 0) {
		rc = ioctl(fd, NVME_IOCTL_ID);
		if (rc > 0)
			nsid = rc;
		memset(buf, 0x3c, lbs);
		rc = nvme_cmd(fd, NVME_IOCTL_IO_CMD, 0x01, nsid, buf, lbs, (13 * MIB) / lbs, 0, 0, &err);
		if (guarded)
			check("passthru-write", rc < 0 && err == EOPNOTSUPP, "Write (0x01): %s",
			      rc < 0 ? strerror(err) : "reached the controller");
		else
			check("passthru-write", rc == 0, "Write (0x01): %s", rc < 0 ? strerror(err) : rc ? "NVMe status" : "written");
		rc = nvme_cmd(fd, NVME_IOCTL_IO_CMD, 0x02, nsid, buf, lbs, 0, 0, 0, &err);
		check("passthru-read", rc == 0, "Read (0x02) of LBA 0: %s",
		      rc < 0 ? strerror(err) : rc ? "NVMe status" : "read");
		if (guarded) {
			static const struct { const char *name; uint8_t op; } io[] = {
				{ "passthru-flush", 0x00 }, { "passthru-write-zeroes", 0x08 },
				{ "passthru-dsm", 0x09 }, { "passthru-write-uncorrectable", 0x04 },
			};

			for (i = 0; i < 4; i++) {
				usleep(600000);
				rc = nvme_cmd(fd, NVME_IOCTL_IO_CMD, io[i].op, nsid, NULL, 0, (14 * MIB) / lbs, 0, 0, &err);
				check(io[i].name, rc < 0 && err == EOPNOTSUPP, "opcode 0x%02x: %s", io[i].op,
				      rc < 0 ? strerror(err) : "reached the controller");
			}
		}
		close(fd);
	}

	/* admin commands: Identify passes; the ones that change a controller or its media do not */
	ctrl = open(CTRL_DEV, O_RDONLY | O_CLOEXEC);
	if (ctrl >= 0) {
		rc = nvme_cmd(ctrl, NVME_IOCTL_ADMIN_CMD, 0x06, 0, buf, 4096, 1, 0, 0, &err);
		if (rc == 0) {
			char model[41];

			memcpy(model, buf + 24, 40);	/* MN; the serial number (bytes 4-23) is not printed */
			model[40] = 0;
			for (i = 39; i >= 0 && model[i] == ' '; i--)
				model[i] = 0;
			check("admin-identify", 1, "Identify Controller passes: model '%s'", model);
		} else {
			check("admin-identify", 0, "Identify Controller: %s", rc < 0 ? strerror(err) : "NVMe status");
		}
		rc = nvme_cmd(ctrl, NVME_IOCTL_ADMIN_CMD, 0x02, 0xffffffff, buf, 512, (127u << 16) | 0x02, 0, 0, &err);
		check("admin-get-log", rc == 0, "Get Log Page (SMART): %s", rc < 0 ? strerror(err) : rc ? "NVMe status" : "read");
		refused_admin(ctrl, "admin-format", 0x80, nsid, 0, 0);
		refused_admin(ctrl, "admin-sanitize", 0x84, 0, 1, 0);
		refused_admin(ctrl, "admin-fw-commit", 0x10, 0, 1u << 3, 0);
		refused_admin(ctrl, "admin-fw-download", 0x11, 0, 0, 0);
		refused_admin(ctrl, "admin-ns-mgmt", 0x0d, nsid, 1, 0);
		refused_admin(ctrl, "admin-ns-attach", 0x15, nsid, 1, 0);
		refused_admin(ctrl, "admin-set-features-vwc", 0x09, 0, 0x06, 0);
		refused_admin(ctrl, "admin-set-features-save", 0x09, 0, (1u << 31) | 0x07, 0);
		refused_admin(ctrl, "admin-security-send", 0x81, 0, 0, 0);
		refused_admin(ctrl, "admin-vendor", 0xc1, 0, 0, 0);
		close(ctrl);
	} else {
		check("admin", 0, "%s: %s", CTRL_DEV, strerror(errno));
	}

	/* file systems: the ext4 partition carries a journal that asks for recovery */
	try_mount("mount-ext4", "/dev/nvme0n1p2", "ext4");
	try_mount("mount-vfat", "/dev/nvme0n1p3", "vfat");

out:
	sync();
	sleep(1);
	kmsg_lines();
	say("RO-TEST-RESULT %s %s: %d check(s) failed\n", failures ? "FAIL" : "PASS", guarded ? "guarded" : "control",
	    failures);
	sync();
	reboot(RB_POWER_OFF);
	return 0;
}
