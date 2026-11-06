"""Render the existing SVG's voxel geometry into one-shot PNG and GIF images.

No API calls, inferred activity, screenshot warping, or runtime README JavaScript.
The SVG remains the source of truth, including its embedded font and widgets.
"""
import argparse
import io
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "profile-3d-contrib/profile-night-green.svg"
FRAME_MS = 40
DURATION = 3.6

# Only the elevated vertices move. Base vertices, horizontal coordinates, face
# colors, footprint widths and SVG painter order remain exactly as authored.
INITIALIZE = """() => {
    const grid = document.querySelector('#isometric-grid');
    const bars = [...grid.querySelectorAll('.bar')].map(group => {
        const faces = [...group.querySelectorAll('polygon')];
        if (faces.length !== 3) throw Error('Expected three voxel faces');
        const points = faces.map(face => [...face.points].map(p => [p.x, p.y]));
        const height = points[0][0][1] - points[0][1][1];
        if (height <= 0) throw Error('Expected positive voxel height');
        const x = (points[0][0][0] + points[1][3][0]) / 2;
        const tile = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        // The cap projected down to the original base gives the exact day tile.
        tile.setAttribute('points', points[2].map(([x,y]) => `${x},${y+height}`).join(' '));
        tile.setAttribute('fill', '#0e131a');
        tile.setAttribute('stroke', '#18202c');
        tile.setAttribute('stroke-width', '0.5');
        group.prepend(tile);
        return {faces, points, height, x, tile,
                originals: faces.map(face => face.getAttribute('points'))};
    });
    const xs = bars.map(bar => bar.x);
    const min = Math.min(...xs), span = Math.max(...xs) - min;
    bars.forEach(bar => bar.delay = 0.18 + (span ? (bar.x-min)/span : 0) * 2.4);
    window.voxels = bars;
    return {bars: bars.length, cells: grid.querySelectorAll('.cell').length};
}"""

SET_FRAME = """time => {
    for (const bar of window.voxels) {
        const tall = bar.height >= 54;
        const u = Math.max(0, Math.min(1, (time-bar.delay)/(tall ? 0.72 : 0.52)));
        // Cubic ease-out for small bars; ease-out-back (~2% overshoot) for tall.
        const c = 0.85;
        const growth = u === 1 ? 1 : tall
            ? 1 + (c+1)*(u-1)**3 + c*(u-1)**2 : 1-(1-u)**3;
        bar.tile.style.display = u === 0 ? '' : 'none';
        bar.faces.forEach((face, f) => {
            face.style.display = u === 0 ? 'none' : '';
            if (u === 1) face.setAttribute('points', bar.originals[f]);
            else face.setAttribute('points', bar.points[f].map(([x,y], v) =>
                `${x},${y + ((f === 2 || v === 1 || v === 2) ? bar.height*(1-growth) : 0)}`
            ).join(' '));
        });
    }
}"""


def capture(page, *, hide_calendar=False):
    # Screenshot styles are temporary and never enter the encoded frames.
    style = "#isometric-grid { visibility: hidden !important; }" if hide_calendar else None
    pixels = page.screenshot(omit_background=True, style=style)
    return Image.open(io.BytesIO(pixels)).convert("RGBA")


def render_frames(source):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 370}, device_scale_factor=1)
        page.set_content('<html><head><style>html,body{margin:0;background:transparent}</style></head><body>'
                         + source.read_text(encoding="utf-8") + '</body></html>')
        page.evaluate("document.fonts.ready")
        if not page.evaluate("document.fonts.check('12px GeistPixelTriangle')"):
            raise RuntimeError("Embedded dashboard font did not load")
        original = capture(page)
        static_artwork = capture(page, hide_calendar=True)
        metrics = page.evaluate(INITIALIZE)
        if not metrics["cells"]:
            raise ValueError("Source SVG has no calendar cells; refusing an empty replacement")
        frames = []
        for index in range(round(DURATION * 1000 / FRAME_MS) + 1):
            page.evaluate(SET_FRAME, index * FRAME_MS / 1000)
            frame = capture(page)
            # Widget bounding rectangles include transparent space where calendar
            # bars can move. Isolate all non-calendar artwork before comparing it.
            static_frame = capture(page, hide_calendar=True)
            if ImageChops.difference(static_frame, static_artwork).getbbox(alpha_only=False):
                raise AssertionError("A non-calendar widget changed")
            frames.append(frame)
        if ImageChops.difference(frames[-1], original).getbbox(alpha_only=False):
            raise AssertionError("Final frame differs from the original static SVG rendering")
        browser.close()
    return frames, metrics


def write_animation(source=SOURCE, preview_dir=None):
    frames, metrics = render_frames(source)
    png_path = source.with_suffix(".png")
    gif_path = source.with_suffix(".gif")
    # Lossless APNG is the primary README image: exact colors, anti-aliasing and
    # alpha. A separate static default image serves clients without APNG support.
    frames[-1].save(png_path, save_all=True, default_image=True,
                    append_images=frames, duration=FRAME_MS, loop=1,
                    disposal=0, blend=0, optimize=True)

    # One stable palette avoids flickering widgets. No dithering or resizing.
    # GIF's 256-color ceiling is why the lossless PNG is preferred in <picture>.
    palette = frames[-1].convert("RGB").quantize(colors=256)
    indexed = [frame.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
               for frame in frames]
    indexed[0].save(gif_path, save_all=True, append_images=indexed[1:],
                    duration=FRAME_MS, disposal=1, optimize=True)

    # Check decoded frames, not just the encoder arguments. APNG frame 0 is the
    # static fallback; animation starts at frame 1 with an empty dark grid.
    with Image.open(png_path) as image:
        assert image.info["loop"] == 1 and image.info["default_image"]
        image.seek(image.n_frames - 1)
        assert not ImageChops.difference(image.convert("RGBA"), frames[-1]).getbbox(alpha_only=False)
    with Image.open(gif_path) as image:
        assert "loop" not in image.info
        image.seek(image.n_frames - 1)
        assert not ImageChops.difference(image.convert("RGB"), indexed[-1].convert("RGB")).getbbox()
    if preview_dir:
        preview_dir.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGBA", (1080, 370 * 4), "#0d1117")
        for row, index in enumerate((0, 28, 55, len(frames)-1)):
            sheet.paste(frames[index], (0, row * 370), frames[index])
        sheet.save(preview_dir / "frames.png")
        frames[-1].save(preview_dir / "final.png")
    print(f"Rendered {metrics['bars']} real bars / {metrics['cells']} days; "
          f"{len(frames)} frames at {1000/FRAME_MS:g} fps; {len(frames)*FRAME_MS/1000:g}s, one play")
    for path in (png_path, gif_path):
        print(f"Generated: {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir", type=Path, help="Also save a contact sheet and exact final PNG")
    args = parser.parse_args()
    write_animation(preview_dir=args.preview_dir)
