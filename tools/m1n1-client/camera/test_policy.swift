// SPDX-License-Identifier: MIT
import Foundation

@main struct PolicyTests {
    static func main() {
        var p = CapturePolicy()
        precondition(!p.start(seconds: 10))
        p.approveFrame(true); precondition(!p.frameApproved)
        precondition(p.prepare()); precondition(!p.prepare())
        p.approveFrame(true); precondition(!p.frameApproved)
        precondition(p.previewReady()); precondition(!p.start(seconds: 10))
        p.approveFrame(true)
        for bad in [Int.min, -1, 0, 301, Int.max] { precondition(!p.start(seconds: bad)) }
        precondition(p.start(seconds: 10)); precondition(!p.frameApproved)
        precondition(!p.start(seconds: 10)); precondition(p.recordingStarted())
        precondition(!p.recordingStarted()); precondition(p.stop()); precondition(!p.stop())
        p.reset(); precondition(p.state == .idle && !p.frameApproved)
        precondition(!p.start(seconds: 300)) // A consumed framing check cannot be reused.
        precondition(p.prepare()); precondition(p.previewReady()); p.approveFrame(true)
        precondition(p.start(seconds: 300)); precondition(p.stop()) // Stop during startup.
        precondition(!p.recordingStarted()) // Late callback cannot re-arm recording.
        p.reset(); precondition(p.prepare()); p.reset() // Setup failure consumes approval.
        precondition(!p.frameApproved && !p.previewReady())
        precondition(p.prepare()); precondition(p.previewReady()); p.approveFrame(true)
        p.closingPreview(); precondition(!p.frameApproved && !p.prepare() && !p.start(seconds: 10))
        print("PASS: framing required/fresh, duration bounds, no duplicate recording, stop/late callback and failure reset")
    }
}
