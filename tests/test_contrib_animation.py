"""Browser regressions for calendar animation and static-artwork validation."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import build_contrib_animation as animation


# The bar lies inside the radar group's bounding rectangle, in transparent
# space between its two shapes. Cropping that rectangle also captures the bar.
SOURCE = """<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="370">
  <rect width="1080" height="370" fill="black"/>
  <g id="isometric-grid">
    <g class="cell bar">
      <polygon points="820,270 820,230 830,235 830,275" fill="#155026"/>
      <polygon points="830,275 830,235 840,230 840,270" fill="#0e381b"/>
      <polygon points="830,225 840,230 830,235 820,230" fill="#2ea043"/>
    </g>
  </g>
  <g id="radar-chart">
    <rect id="widget-marker" x="810" y="220" width="240" height="5" fill="red"/>
    <rect x="1000" y="275" width="5" height="5" fill="red"/>
  </g>
</svg>"""


class AnimationValidationTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.source = Path(directory.name) / "chart.svg"
        self.source.write_text(SOURCE, encoding="utf-8")
        # Exercise the start, an intermediate frame and the completed chart.
        patcher = patch.object(animation, "FRAME_MS", 1800)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_calendar_inside_transparent_widget_bounds_is_allowed(self):
        frames, metrics = animation.render_frames(self.source)
        self.assertEqual(len(frames), 3)
        self.assertEqual(metrics, {"bars": 1, "cells": 1})

    def test_transient_widget_change_is_rejected(self):
        script = animation.SET_FRAME.replace(
            "time => {",
            """time => {
                document.querySelector('#widget-marker').setAttribute(
                    'fill', time > 0 && time < 3.6 ? 'white' : 'red');
            """,
            1,
        )
        with patch.object(animation, "SET_FRAME", script):
            with self.assertRaisesRegex(AssertionError, "non-calendar widget changed"):
                animation.render_frames(self.source)

    def test_incorrect_final_calendar_is_rejected(self):
        script = animation.SET_FRAME.replace(
            "face.setAttribute('points', bar.originals[f])",
            "face.setAttribute('points', '0,0 1,0 1,1')",
        )
        with patch.object(animation, "SET_FRAME", script):
            with self.assertRaisesRegex(AssertionError, "Final frame differs"):
                animation.render_frames(self.source)


if __name__ == "__main__":
    unittest.main()
