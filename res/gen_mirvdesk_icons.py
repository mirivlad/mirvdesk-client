#!/usr/bin/env python3
"""Generate MirvDesk application icons from one procedural master."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "res"
MASTER_SIZE = 1024


def master_icon(size=MASTER_SIZE):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = im.load()
    # Diagonal blue -> teal gradient.
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            px[x, y] = (
                int(18 + 8 * t), int(62 + 104 * t), int(126 + 86 * t), 255
            )
    # Mask gradient to a rounded app tile.
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((24, 24, size - 24, size - 24), radius=220, fill=255)
    im.putalpha(mask)
    d = ImageDraw.Draw(im)
    white = (255, 255, 255, 255)
    # Monitor frame.
    frame = (190, 250, 834, 708)
    d.rounded_rectangle(frame, radius=62, outline=white, width=48)
    d.line((512, 708, 512, 798), fill=white, width=46)
    d.line((382, 806, 642, 806), fill=white, width=46)
    # MirvDesk M: three clean strokes, readable even at 32 px.
    m = [(314, 584), (314, 388), (420, 510), (512, 398), (604, 510), (710, 388), (710, 584)]
    d.line(m, fill=white, width=54, joint="curve")
    return im


def save_png(path, size):
    icon = MASTER.resize((size, size), Image.Resampling.LANCZOS)
    icon.save(path, optimize=True)


def replace_existing_pngs(directory):
    for path in directory.rglob("*.png"):
        try:
            with Image.open(path) as old:
                width, height = old.size
        except Exception:
            continue
        if width != height or width < 16 or width > 2048:
            continue
        save_png(path, width)


def symbol_icon(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    scale = size / MASTER_SIZE
    def q(points):
        return tuple(int(v * scale) for v in points)
    white = (255, 255, 255, 255)
    d.rounded_rectangle(q((190, 250, 834, 708)), radius=int(62 * scale), outline=white, width=max(2, int(48 * scale)))
    d.line(q((512, 708, 512, 798)), fill=white, width=max(2, int(46 * scale)))
    d.line(q((382, 806, 642, 806)), fill=white, width=max(2, int(46 * scale)))
    m = [(314, 584), (314, 388), (420, 510), (512, 398), (604, 510), (710, 388), (710, 584)]
    d.line([(int(x * scale), int(y * scale)) for x, y in m], fill=white, width=max(2, int(54 * scale)), joint="curve")
    return im


MASTER = master_icon()
for name, size in {
    "icon.png": 1024, "mac-icon.png": 1024, "32x32.png": 32,
    "64x64.png": 64, "128x128.png": 128, "128x128@2x.png": 256,
}.items():
    save_png(RES / name, size)
ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
for path in [RES / "icon.ico", RES / "tray-icon.ico", ROOT / "flutter/windows/runner/resources/app_icon.ico"]:
    MASTER.save(path, format="ICO", sizes=ico_sizes)

# macOS menu-bar icon is loaded as a template image, so only alpha/shape matters.
symbol_icon(48).save(RES / "mac-tray-light-x2.png", optimize=True)
symbol_icon(60).save(RES / "mac-tray-dark-x2.png", optimize=True)

# Preserve platform-declared dimensions while replacing only app-icon assets.
replace_existing_pngs(ROOT / "flutter/ios/Runner/Assets.xcassets/AppIcon.appiconset")

for mipmap in (ROOT / "flutter/android/app/src/main/res").glob("mipmap-?*dpi"):
    for path in mipmap.glob("*.png"):
        try:
            with Image.open(path) as old:
                size = old.size[0]
        except Exception:
            continue
        if path.name in {"ic_launcher_foreground.png", "ic_stat_logo.png"}:
            symbol_icon(size).save(path, optimize=True)
        elif path.name in {"ic_launcher.png", "ic_launcher_round.png"}:
            save_png(path, size)

# Pillow writes a multi-resolution ICNS from the 1024 px master.
MASTER.save(ROOT / "flutter/macos/Runner/AppIcon.icns", format="ICNS")

# Vector form used by Linux packages and the in-app fallback logo.
SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img" aria-label="MirvDesk">
  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#123e7e"/><stop offset="1" stop-color="#1aa8cf"/></linearGradient></defs>
  <rect x="24" y="24" width="976" height="976" rx="220" fill="url(#bg)"/>
  <rect x="214" y="274" width="596" height="410" rx="50" fill="none" stroke="#fff" stroke-width="48"/>
  <path d="M512 684v114M382 806h260" fill="none" stroke="#fff" stroke-width="46" stroke-linecap="square"/>
  <path d="M314 584V388l106 122 92-112 92 112 106-122v196" fill="none" stroke="#fff" stroke-width="54" stroke-linejoin="round" stroke-linecap="square"/>
</svg>
"""
for path in [RES / "scalable.svg", RES / "logo.svg", ROOT / "flutter/assets/icon.svg"]:
    path.write_text(SVG, encoding="utf-8")

print("MirvDesk icons generated")
