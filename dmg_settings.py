# dmg_settings.py
import os.path

# DMG settings for VisionSight
application = "VisionSight.app"
appname = "VisionSight"
title = "VisionSight Installer"

# Background (use builtin or provide custom image path)
background = "builtin-arrow"

# Window geometry (x, y, width, height)
window_rect = ((100, 100), (640, 480))

# DMG format - UDBZ is compressed, UDZO is compatible
format = "UDBZ"

# Icon settings
icon_size = 128
text_size = 12

# Icon positions (x, y from top-left)
icon_locations = {
    "VisionSight.app": (160, 200),
    "Applications": (480, 200),
    ".installer": (320, 380)
}

# Create symlink to Applications folder
symlinks = {
    "Applications": "/Applications"
}

# Files to include
files = [
    "VisionSight.app",
    ".installer"
]

# License agreement (optional)
# license = {
#     'default-language': 'en_US',
#     'licenses': { 'en_US': 'LICENSE.txt' }
# }
