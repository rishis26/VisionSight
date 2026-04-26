/*
 * unlock_helper.c — VisionSight HID Injection Helper
 *
 * A tiny standalone binary that types a password at the macOS lock screen
 * using CGEventPost(kCGHIDEventTap).
 *
 * WHY THIS EXISTS:
 * The main VisionSight.app has LSUIElement=True (background-only tray app).
 * macOS Sonoma silently drops CGEventPost HID events from LSUIElement
 * processes when the lock screen is active. This helper binary is NOT
 * LSUIElement — it's a plain CLI executable. WindowServer classifies it
 * as a foreground-capable process and allows its HID events through.
 *
 * USAGE:
 *   echo "mypassword" | ./unlock_helper
 *
 * Password is read from stdin — never appears in `ps aux` output.
 *
 * BUILD:
 *   clang -O2 -o unlock_helper unlock_helper.c \
 *       -framework CoreGraphics -framework CoreFoundation \
 *       -arch arm64
 */

#include <CoreGraphics/CoreGraphics.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void post_key(CGEventSourceRef source, CGKeyCode keycode, bool down) {
    CGEventRef event = CGEventCreateKeyboardEvent(source, keycode, down);
    if (event) {
        CGEventPost(kCGHIDEventTap, event);
        CFRelease(event);
    }
}

static void post_char(CGEventSourceRef source, UniChar c) {
    CGEventRef down = CGEventCreateKeyboardEvent(source, 0, true);
    CGEventKeyboardSetUnicodeString(down, 1, &c);
    CGEventPost(kCGHIDEventTap, down);
    CFRelease(down);

    usleep(20000); /* 20ms key-down hold */

    CGEventRef up = CGEventCreateKeyboardEvent(source, 0, false);
    CGEventKeyboardSetUnicodeString(up, 1, &c);
    CGEventPost(kCGHIDEventTap, up);
    CFRelease(up);

    usleep(20000); /* 20ms inter-key gap */
}

int main(void) {
    /* Read password from stdin (single line, no newline) */
    char buf[1024];
    if (fgets(buf, sizeof(buf), stdin) == NULL) {
        fprintf(stderr, "unlock_helper: no input on stdin\n");
        return 1;
    }
    /* Strip trailing newline */
    buf[strcspn(buf, "\r\n")] = '\0';

    size_t len = strlen(buf);
    if (len == 0) {
        fprintf(stderr, "unlock_helper: empty password\n");
        return 1;
    }

    CGEventSourceRef source = CGEventSourceCreate(kCGEventSourceStatePrivate);
    if (!source) {
        fprintf(stderr, "unlock_helper: CGEventSourceCreate failed\n");
        return 1;
    }

    /* 1. SPACEBAR — wake the lock screen */
    post_key(source, 49, true);
    post_key(source, 49, false);

    /* 2. Wait for password field to render */
    usleep(800000); /* 0.8s */

    /* 3. Type each character */
    for (size_t i = 0; i < len; i++) {
        post_char(source, (UniChar)buf[i]);
    }

    /* 4. Brief settle before Enter */
    usleep(50000); /* 50ms */

    /* 5. ENTER — submit */
    post_key(source, 36, true);
    post_key(source, 36, false);

    CFRelease(source);

    /* Zero out password in memory */
    memset(buf, 0, sizeof(buf));

    return 0;
}
