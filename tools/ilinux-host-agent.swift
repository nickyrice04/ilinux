// ilinux-host-agent: feed Mac host state into the Linux guest.
//
// Writes newline-terminated key=value lines to QEMU's virtio-serial chardev
// socket (port org.ilinux.host); the guest's ilinux-host-bridge applies them:
//   capacity=<0-100> status=<charging|discharging|not-charging|full> ac=<on|off> tte=<min> ttf=<min>
//       battery, from the public IOKit power-source API, on change / every 30 s
//   time=<unix seconds.millis>
//       wall clock, on connect, every 60 s and at once after the Mac wakes:
//       the guest's counter does not advance while the host sleeps, so its
//       clock lags by the sleep time until it is stepped
//   tz=<Area/City>
//       the Mac's time zone, on connect and when it changes (travel)
// Data flows host -> guest only; nothing the guest sends is read.  No root.
//
//   swiftc -O ilinux-host-agent.swift -o bin/ilinux-host-agent
//   ilinux-host-agent --unix virtualization/run/host.sock [--parent PID]
// With --parent the agent exits when that process (QEMU) is gone.
import Foundation
import IOKit.ps

func battery() -> String {
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

func timeZone() -> String {
    NSTimeZone.resetSystemTimeZone()
    return TimeZone.current.identifier
}

func clock() -> String { String(format: "time=%.3f", Date().timeIntervalSince1970) }

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

var args = Array(CommandLine.arguments.dropFirst())
var path: String?
var parent: pid_t = 0
while !args.isEmpty {
    let a = args.removeFirst()
    if a == "--unix", !args.isEmpty { path = args.removeFirst() }
    else if a == "--parent", !args.isEmpty, let p = pid_t(args.removeFirst()) { parent = p }
    else { path = nil; break }
}
guard let socketPath = path else {
    FileHandle.standardError.write("usage: ilinux-host-agent --unix SOCKET [--parent PID]\n".data(using: .utf8)!)
    exit(2)
}
signal(SIGPIPE, SIG_IGN)

var fd: Int32 = -1
var lastBattery = "", lastTz = ""
var lastBatterySent = Date.distantPast, lastTimeSent = Date.distantPast
var lastWall = Date().timeIntervalSince1970
var lastUptime = ProcessInfo.processInfo.systemUptime

func send(_ line: String) -> Bool {
    let data = Array((line + "\n").utf8)
    if write(fd, data, data.count) == data.count { return true }
    close(fd); fd = -1
    return false
}

while true {
    if parent > 0 && kill(parent, 0) != 0 && errno == ESRCH { exit(0) }
    if fd < 0 {
        fd = connectUnix(socketPath)
        if fd < 0 { sleep(2); continue }
        lastBattery = ""; lastTz = ""; lastTimeSent = .distantPast
    }
    // Host sleep shows up as wall-clock time passing without uptime (which
    // stops while asleep): resend the time immediately.
    let wall = Date().timeIntervalSince1970, uptime = ProcessInfo.processInfo.systemUptime
    let slept = (wall - lastWall) - (uptime - lastUptime) > 3
    lastWall = wall; lastUptime = uptime

    let now = Date()
    if slept || now.timeIntervalSince(lastTimeSent) >= 60 {
        if !send(clock()) { continue }
        lastTimeSent = now
    }
    let tz = timeZone()
    if tz != lastTz {
        if !send("tz=\(tz)") { continue }
        lastTz = tz
    }
    let bat = battery()
    if bat != lastBattery || now.timeIntervalSince(lastBatterySent) >= 30 {
        if !send(bat) { continue }
        lastBattery = bat; lastBatterySent = now
    }
    sleep(5)
}
