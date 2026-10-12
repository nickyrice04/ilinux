// mac-battery-feed: stream the Mac's battery state to a Linux guest.
//
// Reads macOS's public IOKit power-source API (no root) and writes one line
//   capacity=<0-100> status=<charging|discharging|not-charging|full> ac=<on|off> tte=<min> ttf=<min>
// every 5 s and whenever the state changes, to QEMU's virtio-serial chardev
// socket (org.ilinux.battery).  The guest-side ilinux-battery-bridge feeds the
// values into the kernel's test_power power_supply device, which UPower and
// Omarchy's bar read.  Data flows host -> guest only; the guest cannot affect
// Mac power state.
//
//   swiftc -O mac-battery-feed.swift -o bin/mac-battery-feed
//   mac-battery-feed --unix virtualization/run/battery.sock
import Foundation
import IOKit.ps

func snapshot() -> String {
    guard let info = IOPSCopyPowerSourcesInfo()?.takeRetainedValue(),
          let list = IOPSCopyPowerSourcesList(info)?.takeRetainedValue() as? [CFTypeRef] else {
        return "capacity=100 status=full ac=on tte=-1 ttf=-1"
    }
    for ps in list {
        guard let d = IOPSGetPowerSourceDescription(info, ps)?.takeUnretainedValue() as? [String: Any],
              (d[kIOPSTypeKey] as? String) == kIOPSInternalBatteryType else { continue }
        let cur = d[kIOPSCurrentCapacityKey] as? Int ?? 0
        let max = d[kIOPSMaxCapacityKey] as? Int ?? 100
        let pct = max > 0 ? Int((Double(cur) / Double(max) * 100).rounded()) : cur
        let ac = (d[kIOPSPowerSourceStateKey] as? String) == kIOPSACPowerValue
        let charging = d[kIOPSIsChargingKey] as? Bool ?? false
        let charged = d[kIOPSIsChargedKey] as? Bool ?? false
        let status = charging ? "charging" : (charged || (ac && pct >= 99)) ? "full" :
            ac ? "not-charging" : "discharging"
        let tte = d[kIOPSTimeToEmptyKey] as? Int ?? -1
        let ttf = d[kIOPSTimeToFullChargeKey] as? Int ?? -1
        return "capacity=\(pct) status=\(status) ac=\(ac ? "on" : "off") tte=\(tte) ttf=\(ttf)"
    }
    return "capacity=100 status=full ac=on tte=-1 ttf=-1"   // desktop Mac: no battery
}

func connectUnix(_ path: String) -> Int32 {
    let fd = socket(AF_UNIX, SOCK_STREAM, 0)
    var addr = sockaddr_un()
    addr.sun_family = sa_family_t(AF_UNIX)
    withUnsafeMutableBytes(of: &addr.sun_path) { buf in
        buf.copyBytes(from: Array(path.utf8.prefix(buf.count - 1)))
    }
    let ok = withUnsafePointer(to: &addr) {
        $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
            connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size)) == 0
        }
    }
    if !ok { close(fd); return -1 }
    return fd
}

let args = CommandLine.arguments
guard args.count == 3, args[1] == "--unix" else {
    FileHandle.standardError.write("usage: mac-battery-feed --unix SOCKET\n".data(using: .utf8)!)
    exit(2)
}
signal(SIGPIPE, SIG_IGN)
var fd: Int32 = -1
var last = ""
var lastSent = Date.distantPast
while true {
    if fd < 0 { fd = connectUnix(args[2]); if fd < 0 { sleep(2); continue }; last = "" }
    let line = snapshot()
    if line != last || Date().timeIntervalSince(lastSent) >= 30 {
        let data = Array((line + "\n").utf8)
        if write(fd, data, data.count) != data.count { close(fd); fd = -1; continue }
        last = line; lastSent = Date()
    }
    sleep(5)
}
