// SPDX-License-Identifier: MIT
import Foundation

// Pure state gate: no camera, files, network or boot operations.
struct CapturePolicy {
    enum State { case idle, preparing, preview, starting, recording, finishing }
    private(set) var state: State = .idle
    private(set) var frameApproved = false
    private(set) var seconds = 10

    mutating func prepare() -> Bool {
        guard state == .idle else { return false }
        frameApproved = false; state = .preparing; return true
    }
    mutating func previewReady() -> Bool {
        guard state == .preparing else { return false }
        state = .preview; return true
    }
    mutating func approveFrame(_ approved: Bool) {
        frameApproved = state == .preview && approved
    }
    mutating func start(seconds: Int) -> Bool {
        guard state == .preview, frameApproved, (1...300).contains(seconds) else { return false }
        self.seconds = seconds; frameApproved = false; state = .starting; return true
    }
    mutating func recordingStarted() -> Bool {
        guard state == .starting else { return false }
        state = .recording; return true
    }
    mutating func stop() -> Bool {
        guard state == .starting || state == .recording else { return false }
        state = .finishing; frameApproved = false; return true
    }
    mutating func closingPreview() { state = .finishing; frameApproved = false }
    mutating func reset() { state = .idle; frameApproved = false }
}
