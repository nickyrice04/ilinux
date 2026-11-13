// SPDX-License-Identifier: MIT
import AppKit
import AVFoundation
import Darwin

final class Preview: NSView {
    let video = AVCaptureVideoPreviewLayer()
    var zoom: CGFloat = 1 { didSet { pan = .zero; needsLayout = true } }
    var pan = CGPoint.zero
    var dragPoint = CGPoint.zero
    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true; layer?.backgroundColor = NSColor.black.cgColor; layer?.masksToBounds = true
        video.videoGravity = .resizeAspect // Keep all four camera-frame edges.
        layer?.addSublayer(video)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) unavailable") }
    override func layout() {
        super.layout()
        video.bounds = bounds; video.position = CGPoint(x: bounds.midX + pan.x, y: bounds.midY + pan.y)
        video.setAffineTransform(CGAffineTransform(scaleX: zoom, y: zoom))
    }
    override func mouseDown(with event: NSEvent) { dragPoint = event.locationInWindow }
    override func mouseDragged(with event: NSEvent) {
        guard zoom > 1 else { return }
        let point = event.locationInWindow
        pan.x += point.x - dragPoint.x; pan.y += point.y - dragPoint.y
        dragPoint = point; needsLayout = true
    }
}

final class CameraApp: NSObject, NSApplicationDelegate, AVCaptureFileOutputRecordingDelegate {
    var window: NSWindow!
    let preview = Preview(frame: .zero)
    let cameras = NSPopUpButton()
    let duration = NSPopUpButton()
    let inspectionZoom = NSPopUpButton()
    let startPreview = NSButton(title: "Start preview", target: nil, action: nil)
    let approval = NSButton(checkboxWithTitle: "Frame checked NOW: all corners and bottom text visible, sharp, no private information", target: nil, action: nil)
    let record = NSButton(title: "Record", target: nil, action: nil)
    let stop = NSButton(title: "Stop / close camera", target: nil, action: nil)
    let status = NSTextField(wrappingLabelWithString: "Camera closed. Select your external webcam, then Start preview.")
    let session = AVCaptureSession()
    let movie = AVCaptureMovieFileOutput()
    let queue = DispatchQueue(label: "ilinux.camera.session")
    var devices: [AVCaptureDevice] = []
    var policy = CapturePolicy()
    var timer: Timer?
    var watchdog: Timer?
    var startedAt: UInt64?
    var folder: URL?
    var events: FileHandle?
    var quitWhenFinished = false
    var interrupted = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        umask(0o077)
        let menu = NSMenu(); let item = NSMenuItem(); let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Quit iLinux Camera", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        item.submenu = appMenu; menu.addItem(item); NSApp.mainMenu = menu
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1060, height: 790),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "iLinux camera — local video only"
        let heading = NSTextField(wrappingLabelWithString: "Camera only • No microphone input • No boot commands\nRecheck framing after every move. The app cannot detect that you moved the camera.")
        heading.font = .systemFont(ofSize: 15, weight: .semibold)
        let controls = NSStackView(views: [cameras, startPreview, duration, record, stop])
        controls.orientation = .horizontal; controls.spacing = 12
        let inspectLabel = NSTextField(labelWithString: "Inspect text (preview only; drag to pan):")
        let inspectControls = NSStackView(views: [inspectLabel, inspectionZoom])
        inspectControls.orientation = .horizontal; inspectControls.spacing = 12
        let stack = NSStackView(views: [heading, preview, controls, inspectControls, approval, status])
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 12
        stack.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 16),
            stack.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -16),
            stack.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 16),
            stack.bottomAnchor.constraint(equalTo: window.contentView!.bottomAnchor, constant: -16),
            preview.widthAnchor.constraint(equalTo: stack.widthAnchor),
            preview.heightAnchor.constraint(greaterThanOrEqualToConstant: 360),
            status.widthAnchor.constraint(equalTo: stack.widthAnchor)
        ])
        duration.addItems(withTitles: ["10 seconds — quality check", "60 seconds", "180 seconds — boot capture", "300 seconds — camera maximum"])
        inspectionZoom.addItems(withTitles: ["1× full frame — required to approve", "1.5× inspect", "2× inspect", "3× inspect"])
        inspectionZoom.target = self; inspectionZoom.action = #selector(zoomChanged)
        startPreview.target = self; startPreview.action = #selector(beginPreview)
        approval.target = self; approval.action = #selector(approve)
        record.target = self; record.action = #selector(beginRecording)
        stop.target = self; stop.action = #selector(stopCapture)
        cameras.target = self; cameras.action = #selector(cameraChanged)
        devices = AVCaptureDevice.DiscoverySession(deviceTypes: [.builtInWideAngleCamera, .external], mediaType: .video, position: .unspecified).devices
        cameras.addItems(withTitles: devices.map { $0.localizedName }) // UI only; never saved in logs.
        if let i = devices.firstIndex(where: { $0.deviceType == .external }) { cameras.selectItem(at: i) }
        NotificationCenter.default.addObserver(self, selector: #selector(captureInterrupted), name: AVCaptureSession.wasInterruptedNotification, object: session)
        NotificationCenter.default.addObserver(self, selector: #selector(captureInterrupted), name: AVCaptureSession.runtimeErrorNotification, object: session)
        updateControls(); window.center(); window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func updateControls() {
        let idle = policy.state == .idle
        cameras.isEnabled = idle; startPreview.isEnabled = idle && !devices.isEmpty
        duration.isEnabled = idle || policy.state == .preview
        inspectionZoom.isEnabled = policy.state == .preview
        approval.isEnabled = policy.state == .preview && preview.zoom == 1
        if !approval.isEnabled { approval.state = .off }
        record.isEnabled = policy.state == .preview && policy.frameApproved
        stop.isEnabled = !idle && policy.state != .preparing && policy.state != .finishing
    }
    @objc func cameraChanged() { approval.state = .off; policy.approveFrame(false); updateControls() }
    @objc func approve() { policy.approveFrame(approval.state == .on && preview.zoom == 1); updateControls() }
    @objc func zoomChanged() {
        preview.zoom = [CGFloat(1), 1.5, 2, 3][inspectionZoom.indexOfSelectedItem]
        approval.state = .off; policy.approveFrame(false); updateControls()
        status.stringValue = preview.zoom == 1
            ? "Full frame restored. Recheck all four corners and bottom text, then approve."
            : "INSPECTION ONLY — enlarges existing pixels; does not add detail or crop the recording. Drag to inspect text; return to 1× before framing approval."
    }

    @objc func beginPreview() {
        guard cameras.indexOfSelectedItem >= 0, policy.prepare() else { return }
        inspectionZoom.selectItem(at: 0); preview.zoom = 1
        updateControls(); status.stringValue = "Opening selected camera preview; no recording."
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized: configurePreview()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { allowed in
                DispatchQueue.main.async {
                    if allowed { self.configurePreview() }
                    else { self.fail("Camera permission was not granted. Nothing recorded.") }
                }
            }
        default: fail("Camera permission unavailable. Nothing recorded; permissions were not changed by this app.")
        }
    }
    func configurePreview() {
        do {
            session.beginConfiguration()
            for input in session.inputs { session.removeInput(input) }
            for output in session.outputs { session.removeOutput(output) }
            let input = try AVCaptureDeviceInput(device: devices[cameras.indexOfSelectedItem])
            guard input.device.hasMediaType(.video), session.canAddInput(input), session.canAddOutput(movie) else {
                session.commitConfiguration(); fail("Selected video device cannot be configured."); return
            }
            session.addInput(input) // No audio input is ever created or requested.
            session.addOutput(movie)
            let presets: [AVCaptureSession.Preset] = [.hd1920x1080, .hd1280x720, .vga640x480]
            guard let preset = presets.first(where: { session.canSetSessionPreset($0) }) else {
                session.commitConfiguration(); fail("Camera does not support a bounded preview preset."); return
            }
            session.sessionPreset = preset
            // macOS selects its encoder from the bounded session preset.
            for connection in movie.connections where connection.inputPorts.contains(where: { $0.mediaType == .audio }) {
                connection.isEnabled = false
            }
            if let connection = movie.connection(with: .video), connection.isVideoMirroringSupported {
                connection.automaticallyAdjustsVideoMirroring = false; connection.isVideoMirrored = false
            }
            session.commitConfiguration()
            preview.video.session = session
            queue.async {
                self.session.startRunning()
                DispatchQueue.main.async {
                    guard self.session.isRunning, self.policy.previewReady() else {
                        self.fail("Camera preview did not start."); return
                    }
                    if let connection = self.preview.video.connection, connection.isVideoMirroringSupported {
                        connection.automaticallyAdjustsVideoMirroring = false; connection.isVideoMirrored = false
                    }
                    self.status.stringValue = "PREVIEW ONLY. Square the camera to the M5 screen; check smallest center/bottom text, glare and all four corners. Then tick the fresh framing check."
                    self.updateControls()
                }
            }
        } catch { session.commitConfiguration(); fail("Camera setup failed. No recording started.") }
    }

    func newFolder() throws -> URL {
        guard let path = Bundle.main.object(forInfoDictionaryKey: "CaptureWorkspaceRoot") as? String else { throw CaptureError.invalidPath }
        let root = URL(fileURLWithPath: path).standardizedFileURL
        guard root.resolvingSymlinksInPath() == root else { throw CaptureError.invalidPath }
        var base = root
        for name in ["build", "camera-capture"] {
            base.appendPathComponent(name, isDirectory: true)
            var directory: ObjCBool = false
            if FileManager.default.fileExists(atPath: base.path, isDirectory: &directory) {
                guard directory.boolValue, base.resolvingSymlinksInPath() == base else { throw CaptureError.invalidPath }
            } else if mkdir(base.path, 0o700) != 0 { throw CaptureError.invalidPath }
        }
        let dest = base.appendingPathComponent("session-" + UUID().uuidString.lowercased(), isDirectory: true)
        guard mkdir(dest.path, 0o700) == 0 else { throw CaptureError.invalidPath }
        return dest
    }
    enum CaptureError: Error { case invalidPath }
    @discardableResult func mark(_ label: String) -> Bool {
        let row: [String: Any] = ["schema": "ilinux-camera-event-v1", "event": label,
            "monotonic_ns": DispatchTime.now().uptimeNanoseconds, "utc_unix_seconds": Date().timeIntervalSince1970]
        if let data = try? JSONSerialization.data(withJSONObject: row, options: [.sortedKeys]) {
            do { try events?.write(contentsOf: data + Data([10])); return true }
            catch { interrupted = true; return false }
        }
        interrupted = true; return false
    }
    @objc func beginRecording() {
        let seconds = [10, 60, 180, 300][duration.indexOfSelectedItem]
        guard preview.zoom == 1, session.isRunning, session.inputs.count == 1,
              session.inputs.allSatisfy({ ($0 as? AVCaptureDeviceInput)?.device.hasMediaType(.video) == true }),
              movie.connections.allSatisfy({ !$0.isEnabled || !$0.inputPorts.contains(where: { $0.mediaType == .audio }) }),
              policy.start(seconds: seconds) else { return }
        updateControls()
        do {
            folder = try newFolder(); interrupted = false; startedAt = nil
            let log = folder!.appendingPathComponent("events.jsonl")
            let fd = open(log.path, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0o600)
            guard fd >= 0 else { throw CaptureError.invalidPath }
            events = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
            movie.maxRecordedDuration = CMTime(seconds: Double(seconds), preferredTimescale: 600)
            movie.maxRecordedFileSize = 256 * 1024 * 1024
            guard mark("frame_approved_and_record_requested") else {
                try? events?.close(); events = nil
                fail("Local event log failed; recording was not started."); return
            }
            movie.startRecording(to: folder!.appendingPathComponent("camera.mov"), recordingDelegate: self)
            status.stringValue = "Starting video-only recording. Wait for RECORDING before any separate boot cue."
            watchdog = Timer.scheduledTimer(withTimeInterval: 10, repeats: false) { _ in
                if self.policy.state == .starting {
                    self.interrupted = true; self.status.stringValue = "Recording start not confirmed within 10 seconds. Stop; no boot cue."; self.stopCapture()
                }
            }
        } catch { fail("Output creation refused. Existing files were not overwritten.") }
    }
    func fileOutput(_ output: AVCaptureFileOutput, didStartRecordingTo fileURL: URL, from connections: [AVCaptureConnection]) {
        DispatchQueue.main.async {
            self.watchdog?.invalidate()
            guard self.policy.recordingStarted() else { self.movie.stopRecording(); return }
            self.startedAt = DispatchTime.now().uptimeNanoseconds
            guard self.mark("recording_started") else { self.stopCapture(); return }
            self.status.stringValue = "RECORDING — VIDEO ONLY — stops after \(self.policy.seconds) seconds. This does not extend the separate M5 stop deadline."
            self.timer = Timer.scheduledTimer(withTimeInterval: Double(self.policy.seconds), repeats: false) { _ in self.stopCapture() }
            self.updateControls()
        }
    }
    @objc func stopCapture() {
        timer?.invalidate(); watchdog?.invalidate()
        if policy.state == .starting || policy.state == .recording {
            _ = policy.stop(); mark("stop_requested"); movie.stopRecording()
            status.stringValue = "Finalizing local movie. Do not treat this as an M5 stop/reboot command."
            updateControls()
        } else if policy.state == .preview { closePreview() }
    }
    func closePreview(message: String = "Camera closed. Every new recording requires a new preview and framing check.") {
        preview.video.session = nil
        policy.closingPreview(); updateControls()
        queue.async {
            self.session.stopRunning()
            DispatchQueue.main.async {
                self.policy.reset(); self.updateControls(); self.status.stringValue = message
                if self.quitWhenFinished { NSApp.reply(toApplicationShouldTerminate: true) }
            }
        }
    }
    @objc func captureInterrupted() {
        DispatchQueue.main.async {
            self.interrupted = true
            if self.policy.state == .starting || self.policy.state == .recording { self.stopCapture() }
            else if self.policy.state == .preview { self.closePreview(message: "Camera interrupted. Reopen and recheck framing.") }
        }
    }
    func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo url: URL, from connections: [AVCaptureConnection], error: Error?) {
        DispatchQueue.main.async { self.finished(url, error: error) }
    }
    func finished(_ url: URL, error: Error?) {
        timer?.invalidate(); watchdog?.invalidate(); mark("recording_finished")
        let asset = AVURLAsset(url: url)
        Task { @MainActor in
            do {
                let audio = try await asset.loadTracks(withMediaType: .audio)
                let videos = try await asset.loadTracks(withMediaType: .video)
                let time = try await asset.load(.duration)
                var size = CGSize.zero; var fps: Float = 0
                if let video = videos.first {
                    size = try await video.load(.naturalSize); fps = try await video.load(.nominalFrameRate)
                }
                self.saveReceipt(url, error: error, audioCount: audio.count, videoCount: videos.count,
                                 mediaDuration: time.seconds, size: size, fps: fps)
            } catch {
                self.interrupted = true
                self.saveReceipt(url, error: error, audioCount: -1, videoCount: -1,
                                 mediaDuration: 0, size: .zero, fps: 0)
            }
        }
    }
    func saveReceipt(_ url: URL, error: Error?, audioCount: Int, videoCount: Int,
                     mediaDuration: Double, size: CGSize, fps: Float) {
        let successful = error == nil || (error as NSError?)?.userInfo[AVErrorRecordingSuccessfullyFinishedKey] as? Bool == true
        let complete = successful && !interrupted && startedAt != nil && audioCount == 0 && videoCount == 1 && mediaDuration.isFinite && mediaDuration > 0 && mediaDuration <= Double(policy.seconds) + 1
        var receipt: [String: Any] = ["schema": "ilinux-camera-receipt-v1", "status": complete ? "LOCAL_VIDEO_RECORDED" : "PARTIAL_OR_UNVERIFIED",
            "framing": "HUMAN_CHECKED_BEFORE_THIS_RECORDING", "framing_quality_automatically_verified": false,
            "requested_seconds": policy.seconds, "duration_seconds": mediaDuration.isFinite ? mediaDuration : 0,
            "audio_tracks": audioCount, "video_tracks": videoCount, "native_boot_controlled": false,
            "interrupted": interrupted, "capture_error_present": error != nil, "dropped_frames_measured": false]
        if let bytes = (try? FileManager.default.attributesOfItem(atPath: url.path))?[.size] as? NSNumber {
            receipt["movie_bytes"] = bytes
        }
        if videoCount > 0 {
            receipt["width"] = abs(size.width); receipt["height"] = abs(size.height)
            receipt["nominal_fps"] = fps.isFinite ? fps : 0
        }
        if let start = startedAt { receipt["recording_started_monotonic_ns"] = start }
        receipt["recording_finished_monotonic_ns"] = DispatchTime.now().uptimeNanoseconds
        do {
            let data = try JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: url.deletingLastPathComponent().appendingPathComponent("receipt.json"), options: [.withoutOverwriting])
            try events?.synchronize(); try events?.close(); events = nil
        } catch { interrupted = true }
        let dir = url.deletingLastPathComponent().lastPathComponent
        closePreview(message: "\(complete && !interrupted ? "Saved; no audio track." : "PARTIAL/UNVERIFIED; preserve files and investigate.") build/camera-capture/\(dir)/ — preview closed; recheck framing next time.")
    }
    func fail(_ text: String) {
        closePreview(message: text)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if policy.state == .starting || policy.state == .recording || policy.state == .finishing {
            quitWhenFinished = true; stopCapture(); return .terminateLater
        }
        queue.sync { self.session.stopRunning() }; return .terminateNow
    }
}

let application = NSApplication.shared
let controller = CameraApp()
application.setActivationPolicy(.regular)
application.delegate = controller
application.run()
