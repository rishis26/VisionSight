# dmg_settings.py
import os.path

# DMG settings for VisionSight
title = "VisionSight"
background = "builtin-arrow"

# Window geometry
window_rect = ((100, 100), (600, 400))

# Options for icons
format = "UDBZ"
icon_size = 120
icon_locations = {
    "VisionSight.app": (140, 120),
    "Applications": (500, 120)
}
symlinks = {
    "Applications": "/Applications",
}
