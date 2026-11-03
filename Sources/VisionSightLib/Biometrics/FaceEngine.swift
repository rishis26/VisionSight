import Vision
import CoreImage
import CoreGraphics
import Foundation

// MARK: - FaceEngine

/// Face detection and recognition engine built on Apple's Vision framework.
///
/// Uses `VNDetectFaceRectanglesRequest` for detection and
/// `VNGenerateImageFeaturePrintRequest` for generating face embeddings
/// (feature prints). Thread-safe — each method creates its own request handler.
public final class FaceEngine {

    // MARK: Result types

    /// Detection result for a single frame.
    public struct DetectionResult {
        /// Detected face bounding boxes.
        public let faces: [VNFaceObservation]
        /// Feature-print embeddings, one per successfully encoded face.
        public let featurePrints: [VNFeaturePrintObservation]
    }

    /// Match result when comparing a live feature print against a stored identity.
    public struct MatchResult {
        /// The matched identity's name.
        public let name: String
        /// The computed distance (lower is better).
        public let distance: Float
        /// The full matched identity record.
        public let identity: Identity
    }

    public init() {}

    // MARK: - Private helpers

    /// Shared `CIContext` for pixel-buffer → `CGImage` conversion.
    private let ciContext = CIContext(options: [.useSoftwareRenderer: false])

    /// Padding factor applied to each side of a detected face bounding box
    /// before cropping (20 %).
    private let facePaddingFactor: CGFloat = 0.20

    // MARK: - Detection

    /// Detect all faces in a pixel buffer.
    public func detectFaces(in pixelBuffer: CVPixelBuffer) throws -> [VNFaceObservation] {
        let request = VNDetectFaceRectanglesRequest()
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, options: [:])
        try handler.perform([request])
        return request.results ?? []
    }

    // MARK: - Feature-print generation

    /// Generate a feature-print embedding for a single detected face.
    public func generateFeaturePrint(
        from pixelBuffer: CVPixelBuffer,
        face: VNFaceObservation
    ) throws -> VNFeaturePrintObservation? {
        guard let cgImage = cgImage(from: pixelBuffer) else { return nil }
        let cropped = cropFace(from: cgImage, boundingBox: face.boundingBox)
        guard let faceImage = cropped else { return nil }
        return try runFeaturePrintRequest(on: faceImage)
    }

    /// Generate a feature-print embedding from an arbitrary `CGImage`.
    public func generateFeaturePrint(from image: CGImage) throws -> VNFeaturePrintObservation? {
        // Detect faces in the static image.
        let detectRequest = VNDetectFaceRectanglesRequest()
        let handler = VNImageRequestHandler(cgImage: image, options: [:])
        try handler.perform([detectRequest])

        guard let firstFace = detectRequest.results?.first else { return nil }
        let cropped = cropFace(from: image, boundingBox: firstFace.boundingBox)
        guard let faceImage = cropped else { return nil }
        return try runFeaturePrintRequest(on: faceImage)
    }

    // MARK: - Matching

    /// Match a live feature print against all stored identities.
    public func match(
        featurePrint: VNFeaturePrintObservation,
        against identities: [Identity],
        tolerance: Float
    ) -> MatchResult? {
        var bestResult: MatchResult?

        for identity in identities {
            guard let stored = identity.loadFeaturePrint() else { continue }

            var distance: Float = 0
            do {
                try featurePrint.computeDistance(&distance, to: stored)
            } catch {
                continue
            }

            if distance < tolerance {
                if bestResult == nil || distance < bestResult!.distance {
                    bestResult = MatchResult(
                        name: identity.name,
                        distance: distance,
                        identity: identity
                    )
                }
            }
        }

        return bestResult
    }

    // MARK: - Full pipeline

    /// Detect faces and generate feature prints in one call.
    ///
    /// Runs face detection followed by feature-print generation for every
    /// detected face.
    ///
    /// - Parameter pixelBuffer: A camera frame.
    /// - Returns: A `DetectionResult` containing faces and their embeddings.
    /// - Throws: Vision framework errors.
    func detectAndEncode(in pixelBuffer: CVPixelBuffer) throws -> DetectionResult {
        let faces = try detectFaces(in: pixelBuffer)
        var prints: [VNFeaturePrintObservation] = []

        for face in faces {
            if let fp = try generateFeaturePrint(from: pixelBuffer, face: face) {
                prints.append(fp)
            }
        }

        return DetectionResult(faces: faces, featurePrints: prints)
    }

    // MARK: - Private helpers

    /// Convert a `CVPixelBuffer` to a `CGImage`.
    private func cgImage(from pixelBuffer: CVPixelBuffer) -> CGImage? {
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        return ciContext.createCGImage(ciImage, from: ciImage.extent)
    }

    /// Crop a face region from a `CGImage`.
    ///
    /// The Vision `boundingBox` uses normalised coordinates with origin at
    /// the bottom-left.  This method converts to pixel coordinates, adds
    /// configurable padding, clamps to image bounds, and crops.
    private func cropFace(from image: CGImage, boundingBox: CGRect) -> CGImage? {
        let imgW = CGFloat(image.width)
        let imgH = CGFloat(image.height)

        // Convert normalised (bottom-left origin) → pixel coordinates (top-left origin).
        let x = boundingBox.origin.x * imgW
        let y = (1.0 - boundingBox.origin.y - boundingBox.height) * imgH
        let w = boundingBox.width * imgW
        let h = boundingBox.height * imgH

        // Apply padding.
        let padX = w * facePaddingFactor
        let padY = h * facePaddingFactor
        var rect = CGRect(
            x: x - padX,
            y: y - padY,
            width: w + 2 * padX,
            height: h + 2 * padY
        )

        // Clamp to image bounds.
        rect = rect.intersection(CGRect(x: 0, y: 0, width: imgW, height: imgH))

        guard !rect.isEmpty, rect.width > 1, rect.height > 1 else { return nil }
        return image.cropping(to: rect)
    }

    /// Run a `VNGenerateImageFeaturePrintRequest` on a `CGImage`.
    private func runFeaturePrintRequest(on image: CGImage) throws -> VNFeaturePrintObservation? {
        let request = VNGenerateImageFeaturePrintRequest()
        let handler = VNImageRequestHandler(cgImage: image, options: [:])
        try handler.perform([request])
        return request.results?.first as? VNFeaturePrintObservation
    }
}
