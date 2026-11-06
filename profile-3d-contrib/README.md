# Contribution dashboard animation

The dashboard is authored as SVG by `generate_3d_contrib.py`, using the real GitHub
GraphQL contribution calendar. `build_contrib_animation.py` reads that SVG's
existing three-face voxels and renders 91 deterministic frames with Chromium at
the original **1080 × 370** resolution. Each cap translates vertically; the side
faces extend from fixed base vertices. Original face colors, depth order, dates,
font, doughnut, radar, labels and border remain unchanged.

The 3.64-second timeline starts with a dark grid, then staggers bars by horizontal
position, with cubic ease-out and approximately 2% overshoot for taller bars.
No activity is inferred from pixels or invented. The checked-in SVG is also
sufficient to regenerate the animations offline without changing its data.

- `profile-night-green.png`: lossless animated PNG (APNG), one play, with a
  fully rendered static default image for PNG-only decoders. Preferred by the
  README's `<picture>` to preserve all original colors and transparent corners.
- `profile-night-green.gif`: one-shot GIF fallback, with no loop extension and
  keep-frame disposal. A shared palette and disabled dithering keep pixels and
  static widgets stable. GIF's 256-color limit slightly quantizes gradients and
  anti-aliased edges; its corner background is black.
- `profile-night-green.svg`: the static source chart, selected for reduced-motion
  users through the README's existing `<picture>` pattern. The generator writes
  only this variant; the unused rainbow and view copies have been removed.

## Generate and preview

From the repository root, install the same dependencies used by Actions:

```sh
python -m pip install fonttools==4.63.0 Pillow==12.2.0 playwright==1.62.0
python -m playwright install --with-deps chromium
python -c "import sys; sys.path.insert(0, 'assets/readme-panels'); from alpino import download_fonts; download_fonts()"

# Browser regressions, including calendar bars behind transparent widget bounds.
python -m unittest discover -s tests -v

# Offline: animate the exact checked-in chart, preserving its data and dates.
python build_contrib_animation.py --preview-dir .cache/contribution-animation

# Online: fetch current data, regenerate the static SVG, then both animations.
# Requires authenticated gh, GITHUB_TOKEN, or GH_TOKEN with access to the user.
python generate_3d_contrib.py
```

Open `preview_contrib_animation.html` in a browser. Its replay button gives each
image a fresh local URL. The optional preview directory contains a contact sheet
and the exact final PNG. Generation checks that non-calendar artwork never
changes by temporarily hiding the calendar in validation-only screenshots. This
allows bars to move behind transparent parts of widget bounding rectangles.
It also checks that the final rendered frame is pixel-identical to the source
SVG, the APNG decodes to that exact final frame, and the GIF decodes to its
palette equivalent.

`.github/workflows/profile-3d.yml` refreshes the SVG and both animations together
daily at **18:00 UTC** (23:30 India time), or via **Run workflow**. It commits the
generated assets as **voxelepic** (`voxelepic@gmail.com`). If the API returns no
data or a request fails, generation stops and the previous images stay published.

## Playback and GitHub limitations

Both assets are ordinary README images: no scripts, CSS animation or SVG
animation run on GitHub. PNG and GIF are [supported GitHub image formats](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files).
APNG uses the PNG container and is [supported by current browsers](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Formats/Image_types#apng_animated_portable_network_graphics).
The GIF [omits `loop`](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif)
and the APNG sets one play; supported decoders stop on the completed chart.

An image starts when the viewer loads/decodes it, which can happen before the
reader scrolls to it. Browsers may reuse decoded images on refresh or navigation;
GitHub's CDN/Camo may temporarily serve an older asset. Neither a README nor an
image file can force a replay on every profile visit or bypass viewer autoplay
preferences. [GitHub documents image caching delays](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-anonymized-urls#an-image-that-changed-recently-is-not-updating).
Reopening the image with a fresh URL can replay it, but the README intentionally
has no per-visit cache-busting service. PNG-only clients see the final static
chart; clients honoring reduced-motion receive the static SVG.
