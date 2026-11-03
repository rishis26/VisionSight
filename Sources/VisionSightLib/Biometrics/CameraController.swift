import AVFoundation
import CoreImage
import CoreVideo
import Foundation
import Combine

/// Delegate protocol for receiving camera frames.
protocol CameraDelegate: AnyObject {
    func cameraDidCapture(pixelBuffer: CVPixelBuffer, timestamp: CMTime)
}

/// Manages AVFoundation camera capture session with zero frame conversion overhead.
public final class CameraController: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate, ObservableObject, @unchecked Sendable {
    @Published public var isRunning: Bool = false
    @Published public var errorMessage: String?

    weak var delegate: CameraDelegate?

    /// Callback invoked for each captured frame.
    public var onFrame: ((CVPixelBuffer) -> Void)?

    private var captureSession: AVCaptureSession?
    private let sessionQueue = DispatchQueue(label: "com.visionsight.camera", qos: .userInitiated)

    public override init() {
        super.init()
    }

    /// Check if camera permission has been granted.
    public static var isAuthorized: Bool {
        AVCaptureDevice.authorizationStatus(for: .video) == .authorized
    }

    /// Request camera permission from macOS.
    public static func requestPermission() async -> Bool {
        await AVCaptureDevice.requestAccess(for: .video)
    }

    /// Start camera capture.
    public func start(cameraIndex: Int = 0, width: Int = 640, height: Int = 480) {
        sessionQueue.async { [weak self] in
            guard let self else { return }
            guard self.captureSession == nil || !(self.captureSession?.isRunning ?? false) else { return }

            let session = AVCaptureSession()
            session.beginConfiguration()
            session.sessionPreset = .medium

            // Find available video capture device
            let devices = AVCaptureDevice.DiscoverySession(
                deviceTypes: [.builtInWideAngleCamera, .external],
                mediaType: .video,
                position: .unspecified
            ).devices

            let device: AVCaptureDevice?
            if cameraIndex < devices.count {
                device = devices[cameraIndex]
            } else {
                device = AVCaptureDevice.default(for: .video)
            }

            guard let selectedDevice = device else {
                DispatchQueue.main.async {
                    self.errorMessage = "No camera device available."
                    self.isRunning = false
                }
                session.commitConfiguration()
                return
            }

            do {
                let input = try AVCaptureDeviceInput(device: selectedDevice)
                if session.canAddInput(input) {
                    session.addInput(input)
                }

                let output = AVCaptureVideoDataOutput()
                output.alwaysDiscardsLateVideoFrames = true
                output.videoSettings = [
                    kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA)
                ]
                output.setSampleBufferDelegate(self, queue: self.sessionQueue)

                if session.canAddOutput(output) {
                    session.addOutput(output)
                }

                session.commitConfiguration()
                session.startRunning()

                self.captureSession = session
                DispatchQueue.main.async {
                    self.isRunning = true
                    self.errorMessage = nil
                }
            } catch {
                DispatchQueue.main.async {
                    self.errorMessage = "Failed to open camera: \(error.localizedDescription)"
                    self.isRunning = false
                }
                session.commitConfiguration()
            }
        }
    }

    /// Stop camera capture and release hardware resources.
    public func stop() {
        sessionQueue.async { [weak self] in
            guard let self, let session = self.captureSession else { return }
            if session.isRunning {
                session.stopRunning()
            }
            self.captureSession = nil
            DispatchQueue.main.async {
                self.isRunning = false
            }
        }
    }

    /// Capture a single frame synchronously (e.g. for registration).
    public func capturePhoto() -> CVPixelBuffer? {
        let semaphore = DispatchSemaphore(value: 0)
        var capturedBuffer: CVPixelBuffer?

        let prevOnFrame = self.onFrame
        self.onFrame = { buffer in
            capturedBuffer = buffer
            semaphore.signal()
        }

        if !isRunning {
            start()
        }

        _ = semaphore.wait(timeout: .now() + 2.0)
        self.onFrame = prevOnFrame
        return capturedBuffer
    }

    // MARK: - AVCaptureVideoDataOutputSampleBufferDelegate

    public func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let timestamp = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)

        delegate?.cameraDidCapture(pixelBuffer: pixelBuffer, timestamp: timestamp)
        onFrame?(pixelBuffer)
    }
}
