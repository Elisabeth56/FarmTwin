"""Renders the 3D farm's stills and short video loops for the site and the app.

Run from the repo root after `pnpm install`:  python packages/twin/capture/capture.py
Needs Chrome (or Chromium), ffmpeg and `pip install playwright`.
"""
import functools
import http.server
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[3]
SITE = ROOT / "apps/site/public/assets"
APP = ROOT / "apps/web/public/twin"
FRAMES = pathlib.Path(tempfile.mkdtemp(prefix="twin-frames-"))
# budgets from #29: the landing page loads these on slow connections
MAX_VIDEO, MAX_STILL = 600_000, 100_000


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def loop(pg, name: str, rain: bool, seconds: int = 8, fps: int = 24) -> None:
    """A seamless back-and-forth sweep, encoded as WebM and MP4 for the site's lite tier."""
    pg.set_viewport_size({"width": 960, "height": 540})
    pg.evaluate(f"twin.setRain({str(rain).lower()})")
    pg.wait_for_timeout(2500)
    base = pg.evaluate("twin.azimuth")
    d = FRAMES / name
    d.mkdir()
    n = seconds * fps
    for i in range(n):
        pg.evaluate(f"twin.setView({base + 0.35 * math.sin(2 * math.pi * i / n)})")
        pg.wait_for_timeout(1000 // fps)
        pg.screenshot(path=str(d / f"{i:04d}.png"))
    frames = ["-framerate", str(fps), "-i", str(d / "%04d.png")]
    ffmpeg(*frames, "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "47", "-row-mt", "1", "-pix_fmt", "yuv420p", "-an", str(SITE / f"{name}.webm"))
    ffmpeg(*frames, "-c:v", "libx264", "-crf", "30", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(SITE / f"{name}.mp4"))


def still(pg, name: str, rain: bool, out: pathlib.Path) -> None:
    """One 1600x900 frame from the fixed three-quarter view, as WebP and JPEG."""
    pg.set_viewport_size({"width": 1600, "height": 900})
    pg.evaluate(f"twin.setRain({str(rain).lower()})")
    pg.evaluate("twin.setView(Math.PI / 4)")
    pg.wait_for_timeout(2500)
    png = FRAMES / f"{out.name}-{name}.png"
    pg.screenshot(path=str(png))
    ffmpeg("-i", str(png), "-c:v", "libwebp", "-quality", "80", str(out / f"{name}.webp"))
    ffmpeg("-i", str(png), "-q:v", "7", str(out / f"{name}.jpg"))


# the "Who it's for" cards: (name, azimuth, polar, zoom, rain), portrait 4:5
PEOPLE = [("officers", 0.6, 0.95, 0.78, True), ("farmers", -0.9, 1.05, 0.7, False), ("students", 2.6, 1.25, 0.6, False)]


def people(pg) -> None:
    pg.set_viewport_size({"width": 800, "height": 1000})
    for name, az, polar, zoom, rain in PEOPLE:
        pg.evaluate(f"twin.setRain({str(rain).lower()})")
        pg.evaluate(f"twin.setView({az}, {polar}); twin.zoom({zoom})")
        pg.wait_for_timeout(2500)
        png = FRAMES / f"people-{name}.png"
        pg.screenshot(path=str(png))
        ffmpeg("-i", str(png), "-vf", "scale=640:-1", "-c:v", "libwebp", "-quality", "78", str(SITE / f"people-{name}.webp"))
        ffmpeg("-i", str(png), "-vf", "scale=640:-1", "-q:v", "6", str(SITE / f"people-{name}.jpg"))


def serve() -> http.server.ThreadingHTTPServer:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def check_sizes() -> list[str]:
    over = []
    for f in [*SITE.glob("farm-*"), *SITE.glob("people-*"), *APP.glob("farm-*")]:
        limit = MAX_VIDEO if f.suffix in (".webm", ".mp4") else MAX_STILL
        if f.stat().st_size > limit:
            over.append(f"{f.relative_to(ROOT)}: {f.stat().st_size} bytes (limit {limit})")
    return over


def main() -> int:
    srv = serve()
    chrome = os.environ.get("CHROME_PATH") or shutil.which("google-chrome") or shutil.which("chromium")
    with sync_playwright() as p:
        # software WebGL so CI runners without a GPU render the same scene
        b = p.chromium.launch(executable_path=chrome, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1600, "height": 900})
        pg.goto(f"http://127.0.0.1:{srv.server_port}/packages/twin/capture/capture.html")
        pg.wait_for_function("window.twinReady === true", timeout=60000)
        pg.wait_for_timeout(2500)

        for name, rain in (("farm-dry", False), ("farm-rain", True)):
            still(pg, name, rain, SITE)
            loop(pg, name, rain)
        people(pg)
        # the app shows the farm's real risks beside the picture, so its stills carry no badge
        pg.add_style_tag(content=".badge{display:none!important}")
        for name, rain in (("farm-dry", False), ("farm-rain", True)):
            still(pg, name, rain, APP)
        b.close()
    srv.shutdown()
    shutil.rmtree(FRAMES, ignore_errors=True)

    over = check_sizes()
    for line in over:
        print("too big:", line)
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
