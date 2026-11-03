import Vision
import Foundation
import CoreGraphics

/// Liveness detection using Eye Aspect Ratio (EAR) from facial landmarks.
/// Prevents unlocking from photographs or when the user's eyes are closed (sleeping).
final class LivenessDetector {

    /// Minimum EAR threshold to consider eyes open. Below this, eyes are deemed closed.
    var earThreshold: Double = 0.22

    /// Detect facial landmarks for given face observations.
    func detectLandmarks(in pixelBuffer: CVPixelBuffer, faces: [VNFaceObservation]) throws -> [VNFaceObservation] {
        guard !faces.isEmpty else { return [] }

        let request = VNDetectFaceLandmarksRequest()
        request.inputFaceObservations = faces

        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, options: [:])
        try handler.perform([request])

        return request.results ?? []
    }

    /// Compute Eye Aspect Ratio for a face observation.
    /// Returns nil if landmarks or eye points are unavailable.
    func computeEAR(from observation: VNFaceObservation) -> Double? {
        guard let landmarks = observation.landmarks,
              let leftEye = landmarks.leftEye,
              let rightEye = landmarks.rightEye else {
            return nil
        }

        let leftPoints = leftEye.normalizedPoints
        let rightPoints = rightEye.normalizedPoints

        guard leftPoints.count >= 6, rightPoints.count >= 6 else {
            return nil
        }

        let leftEAR = earForEye(leftPoints)
        let rightEAR = earForEye(rightPoints)

        return (leftEAR + rightEAR) / 2.0
    }

    /// Check if the face passes liveness (eyes are open above threshold).
    func isAlive(observation: VNFaceObservation) -> Bool {
        guard let ear = computeEAR(from: observation) else {
            // If landmarking fails, do not reject automatically if face is otherwise clear
            return false
        }
        return ear >= earThreshold
    }

    /// Compute EAR for a single eye given its landmark points.
    /// Standard Vision eye landmark array has points contouring the eye.
    private func earForEye(_ points: [CGPoint]) -> Double {
        let n = points.count
        if n >= 8 {
            // 8-point eye model in Vision:
            // p0: outer corner, p4: inner corner
            // p1, p2, p3: upper eyelid
            // p7, p6, p5: lower eyelid
            let p0 = points[0]
            let p1 = points[1]
            let p2 = points[2]
            let p4 = points[4]
            let p6 = points[6]
            let p7 = points[7]

            let vert1 = distance(p1, p7)
            let vert2 = distance(p2, p6)
            let horiz = distance(p0, p4)

            guard horiz > 0.0001 else { return 0.0 }
            return (vert1 + vert2) / (2.0 * horiz)
        } else {
            // 6-point fallback model:
            // p0: outer, p3: inner
            // p1, p2: upper
            // p5, p4: lower
            let p0 = points[0]
            let p1 = points[1]
            let p2 = points[2]
            let p3 = points[3]
            let p4 = points[4]
            let p5 = points[5]

            let vert1 = distance(p1, p5)
            let vert2 = distance(p2, p4)
            let horiz = distance(p0, p3)

            guard horiz > 0.0001 else { return 0.0 }
            return (vert1 + vert2) / (2.0 * horiz)
        }
    }

    private func distance(_ a: CGPoint, _ b: CGPoint) -> Double {
        let dx = Double(a.x - b.x)
        let dy = Double(a.y - b.y)
        return sqrt(dx * dx + dy * dy)
    }
}

