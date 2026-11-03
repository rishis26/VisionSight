// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "VisionSight",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(name: "VisionSightLib", targets: ["VisionSightLib"]),
        .executable(name: "VisionSightApp", targets: ["VisionSightApp"]),
        .executable(name: "vs", targets: ["vs"]),
    ],
    targets: [
        .target(
            name: "VisionSightLib",
            linkerSettings: [
                .linkedFramework("AVFoundation"),
                .linkedFramework("CoreGraphics"),
                .linkedFramework("CoreMedia"),
                .linkedFramework("Foundation"),
                .linkedFramework("Security"),
                .linkedFramework("Vision"),
                .linkedFramework("AppKit"),
            ]
        ),
        .executableTarget(
            name: "VisionSightApp",
            dependencies: ["VisionSightLib"]
        ),
        .executableTarget(
            name: "vs",
            dependencies: ["VisionSightLib"]
        ),
    ]
)