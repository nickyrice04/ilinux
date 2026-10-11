// vzrun - minimal ARM64 Linux VM runner on Apple's Virtualization.framework.
//
// Purpose: disposable, workspace-contained Linux test environments (Layer 3 of
// the testing strategy) without installing host software.  Everything a VM
// touches (disk image, EFI variable store, shared folders) is passed
// explicitly; nothing outside the given paths is written.
//
// Build (ad-hoc signed with the virtualization entitlement, no install):
//   virtualization/vzrun/build.sh
//
// Examples:
//   vzrun --efi --disk images/arch.img --efi-vars images/arch.efivars --iso installer.iso --gui
//   vzrun --kernel Image --initrd initramfs.img --cmdline "console=hvc0 root=/dev/vda2 rw" --disk images/arch.img
//   vzrun ... --share ../benchmarks:bench:ro      (virtiofs tag "bench", read-only)
//
// Headless mode wires the guest's virtio console (hvc0) to this terminal.

import AppKit
import Foundation
import Virtualization

struct Options {
    var cpus = 8
    var memGiB: UInt64 = 16
    var disks: [String] = []
    var iso: String?
    var efi = false
    var efiVars: String?
    var kernel: String?
    var initrd: String?
    var cmdline = "console=hvc0"
    var gui = false
    var shares: [(path: String, tag: String, readOnly: Bool)] = []
    var nat = true
    var nested = false
    var nvme = false
    var diskCache = "automatic"     // automatic | cached | uncached
    var diskSync = "full"           // full | fsync | none
    var width = 1920, height = 1200
}

func usage() -> Never {
    FileHandle.standardError.write("""
    usage: vzrun [--cpus N] [--mem GiB] [--disk raw.img]... [--iso file.iso]
                 (--efi [--efi-vars file] | --kernel Image [--initrd file] [--cmdline str])
                 [--share hostdir:tag[:ro]]... [--no-net] [--nested] [--gui [--size WxH]]
                 [--nvme] [--disk-cache automatic|cached|uncached] [--disk-sync full|fsync|none]

    """.data(using: .utf8)!)
    exit(2)
}

func parse() -> Options {
    var o = Options()
    var it = CommandLine.arguments.dropFirst().makeIterator()
    func next() -> String { guard let v = it.next() else { usage() }; return v }
    while let a = it.next() {
        switch a {
        case "--cpus": o.cpus = Int(next()) ?? o.cpus
        case "--mem": o.memGiB = UInt64(next()) ?? o.memGiB
        case "--disk": o.disks.append(next())
        case "--iso": o.iso = next()
        case "--efi": o.efi = true
        case "--efi-vars": o.efiVars = next()
        case "--kernel": o.kernel = next()
        case "--initrd": o.initrd = next()
        case "--cmdline": o.cmdline = next()
        case "--gui": o.gui = true
        case "--no-net": o.nat = false
        case "--nested": o.nested = true
        case "--nvme": o.nvme = true
        case "--disk-cache": o.diskCache = next()
        case "--disk-sync": o.diskSync = next()
        case "--size":
            let p = next().split(separator: "x").compactMap { Int($0) }
            if p.count == 2 { o.width = p[0]; o.height = p[1] }
        case "--share":
            let p = next().split(separator: ":").map(String.init)
            guard p.count >= 2 else { usage() }
            o.shares.append((p[0], p[1], p.count > 2 && p[2] == "ro"))
        default: usage()
        }
    }
    if !o.efi && o.kernel == nil { usage() }
    return o
}

func fileURL(_ p: String) -> URL { URL(fileURLWithPath: (p as NSString).expandingTildeInPath) }

func makeConfig(_ o: Options) throws -> VZVirtualMachineConfiguration {
    let c = VZVirtualMachineConfiguration()
    c.cpuCount = max(VZVirtualMachineConfiguration.minimumAllowedCPUCount,
                     min(o.cpus, VZVirtualMachineConfiguration.maximumAllowedCPUCount))
    c.memorySize = min(o.memGiB << 30, VZVirtualMachineConfiguration.maximumAllowedMemorySize)
    let platform = VZGenericPlatformConfiguration()
    if o.nested {
        // Nested virtualization (KVM inside the guest) needs M3 or later and macOS 15+.
        guard VZGenericPlatformConfiguration.isNestedVirtualizationSupported else {
            throw NSError(domain: "vzrun", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "nested virtualization not supported on this host"])
        }
        platform.isNestedVirtualizationEnabled = true
    }
    c.platform = platform

    if o.efi {
        let boot = VZEFIBootLoader()
        let varsURL = fileURL(o.efiVars ?? "efi-vars.fd")
        if FileManager.default.fileExists(atPath: varsURL.path) {
            boot.variableStore = VZEFIVariableStore(url: varsURL)
        } else {
            boot.variableStore = try VZEFIVariableStore(creatingVariableStoreAt: varsURL)
        }
        c.bootLoader = boot
    } else {
        let boot = VZLinuxBootLoader(kernelURL: fileURL(o.kernel!))
        if let i = o.initrd { boot.initialRamdiskURL = fileURL(i) }
        boot.commandLine = o.cmdline
        c.bootLoader = boot
    }

    var storage: [VZStorageDeviceConfiguration] = []
    let caching: VZDiskImageCachingMode = o.diskCache == "cached" ? .cached :
        o.diskCache == "uncached" ? .uncached : .automatic
    let sync: VZDiskImageSynchronizationMode = o.diskSync == "none" ? .none :
        o.diskSync == "fsync" ? .fsync : .full
    for (i, d) in o.disks.enumerated() {
        // The first disk is the root disk and always uses safe settings; the
        // cache/sync/NVMe experiment flags apply to additional (data) disks.
        let isRoot = i == 0
        let att = try VZDiskImageStorageDeviceAttachment(url: fileURL(d), readOnly: false,
                                                         cachingMode: isRoot ? .automatic : caching,
                                                         synchronizationMode: isRoot ? .full : sync)
        if !isRoot && o.nvme {
            storage.append(VZNVMExpressControllerDeviceConfiguration(attachment: att))
        } else {
            storage.append(VZVirtioBlockDeviceConfiguration(attachment: att))
        }
    }
    if let iso = o.iso {
        let att = try VZDiskImageStorageDeviceAttachment(url: fileURL(iso), readOnly: true)
        storage.append(VZUSBMassStorageDeviceConfiguration(attachment: att))
    }
    c.storageDevices = storage

    if o.nat {
        let net = VZVirtioNetworkDeviceConfiguration()
        net.attachment = VZNATNetworkDeviceAttachment()
        c.networkDevices = [net]
    }

    c.entropyDevices = [VZVirtioEntropyDeviceConfiguration()]
    c.memoryBalloonDevices = [VZVirtioTraditionalMemoryBalloonDeviceConfiguration()]

    // Console: virtio console on stdio (headless) - always present for logs.
    let console = VZVirtioConsoleDeviceSerialPortConfiguration()
    console.attachment = VZFileHandleSerialPortAttachment(
        fileHandleForReading: o.gui ? nil : FileHandle.standardInput,
        fileHandleForWriting: FileHandle.standardOutput)
    c.serialPorts = [console]

    var shares: [VZDirectorySharingDeviceConfiguration] = []
    for s in o.shares {
        let fs = VZVirtioFileSystemDeviceConfiguration(tag: s.tag)
        fs.share = VZSingleDirectoryShare(directory: VZSharedDirectory(url: fileURL(s.path),
                                                                       readOnly: s.readOnly))
        shares.append(fs)
    }
    c.directorySharingDevices = shares

    if o.gui {
        let g = VZVirtioGraphicsDeviceConfiguration()
        g.scanouts = [VZVirtioGraphicsScanoutConfiguration(widthInPixels: o.width,
                                                           heightInPixels: o.height)]
        c.graphicsDevices = [g]
        c.keyboards = [VZUSBKeyboardConfiguration()]
        c.pointingDevices = [VZUSBScreenCoordinatePointingDeviceConfiguration()]
        c.audioDevices = []
    }
    try c.validate()
    return c
}

final class Delegate: NSObject, VZVirtualMachineDelegate {
    func guestDidStop(_ vm: VZVirtualMachine) {
        FileHandle.standardError.write("vzrun: guest stopped\n".data(using: .utf8)!)
        exit(0)
    }
    func virtualMachine(_ vm: VZVirtualMachine, didStopWithError error: Error) {
        FileHandle.standardError.write("vzrun: stopped with error: \(error)\n".data(using: .utf8)!)
        exit(1)
    }
}

let opts = parse()
let config: VZVirtualMachineConfiguration
do { config = try makeConfig(opts) } catch {
    FileHandle.standardError.write("vzrun: invalid configuration: \(error)\n".data(using: .utf8)!)
    exit(1)
}
let vm = VZVirtualMachine(configuration: config)
let delegate = Delegate()
vm.delegate = delegate

// Headless: put the terminal in raw mode so the guest console behaves, and
// restore it at exit (Ctrl-C goes to the guest; power the guest off to quit).
var savedTermios = termios()
var termiosSaved = false
func restoreTerminal() {
    if termiosSaved { tcsetattr(STDIN_FILENO, TCSANOW, &savedTermios) }
}
if !opts.gui && isatty(STDIN_FILENO) != 0 && tcgetattr(STDIN_FILENO, &savedTermios) == 0 {
    termiosSaved = true
    var raw = savedTermios
    cfmakeraw(&raw)
    tcsetattr(STDIN_FILENO, TCSANOW, &raw)
    atexit { restoreTerminal() }
}

vm.start { result in
    if case .failure(let e) = result {
        FileHandle.standardError.write("vzrun: start failed: \(e)\n".data(using: .utf8)!)
        exit(1)
    }
    FileHandle.standardError.write("vzrun: VM started (\(config.cpuCount) vCPU, \(config.memorySize >> 30) GiB)\r\n".data(using: .utf8)!)
}

if opts.gui {
    let app = NSApplication.shared
    app.setActivationPolicy(.regular)
    let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: opts.width / 2, height: opts.height / 2),
                          styleMask: [.titled, .closable, .resizable, .miniaturizable],
                          backing: .buffered, defer: false)
    window.title = "vzrun"
    let view = VZVirtualMachineView()
    view.virtualMachine = vm
    view.capturesSystemKeys = true
    window.contentView = view
    window.center()
    window.makeKeyAndOrderFront(nil)
    app.activate(ignoringOtherApps: true)
    app.run()
} else {
    dispatchMain()
}
