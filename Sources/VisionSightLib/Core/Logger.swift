import Foundation

/// Thread-safe logger that writes to both stdout and a persistent log file.
///
/// Access the shared instance via ``shared``. All writes are serialized on a
/// private dispatch queue so the logger is safe to use from any thread or
/// Swift concurrency context.
///
/// Log lines follow the format:
/// ```
/// [2024-03-15 09:30:45] [INFO] Application started
/// ```
final class Logger: @unchecked Sendable {

    /// Shared singleton logger instance.
    static let shared = Logger()

    /// Log severity levels.
    enum Level: String {
        case info = "INFO"
        case warning = "WARN"
        case error = "ERROR"
        case event = "EVENT"
    }

    // MARK: - Private Properties

    /// File handle for append-mode writes to the log file.
    private let fileHandle: FileHandle?

    /// Serial queue that serializes all log writes.
    private let queue = DispatchQueue(label: "com.visionsight.logger")

    /// Date formatter producing `YYYY-MM-DD HH:MM:SS` timestamps.
    private let dateFormatter: DateFormatter

    // MARK: - Init

    private init() {
        // Configure the date formatter for log timestamps.
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone.current
        self.dateFormatter = formatter

        // Ensure the log directory exists and open the file for appending.
        AppPaths.ensureDirectoriesExist()
        let logURL = AppPaths.logFile

        // Create the file if it doesn't exist.
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }

        self.fileHandle = try? FileHandle(forWritingTo: logURL)
        self.fileHandle?.seekToEndOfFile()
    }

    deinit {
        fileHandle?.closeFile()
    }

    // MARK: - Public API

    /// Write a log message at the specified level.
    ///
    /// The message is printed to stdout and appended to the log file
    /// atomically on a serial queue.
    ///
    /// - Parameters:
    ///   - message: The message to log.
    ///   - level: The severity level (defaults to `.info`).
    func log(_ message: String, level: Level = .info) {
        let timestamp = dateFormatter.string(from: Date())
        let line = "[\(timestamp)] [\(level.rawValue)] \(message)\n"

        queue.async { [weak self] in
            // Write to stdout.
            print(line, terminator: "")

            // Write to log file.
            if let data = line.data(using: .utf8) {
                self?.fileHandle?.write(data)
            }
        }
    }

    /// Log an informational message.
    /// - Parameter message: The message to log.
    func info(_ message: String) {
        log(message, level: .info)
    }

    /// Log a warning message.
    /// - Parameter message: The message to log.
    func warning(_ message: String) {
        log(message, level: .warning)
    }

    /// Log an error message.
    /// - Parameter message: The message to log.
    func error(_ message: String) {
        log(message, level: .error)
    }

    /// Log a notable event.
    /// - Parameter message: The message to log.
    func event(_ message: String) {
        log(message, level: .event)
    }
}
