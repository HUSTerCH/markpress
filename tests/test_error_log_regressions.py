import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from reportlab.lib.units import mm

from markpress.core import MarkPressEngine
from markpress.themes import StyleConfig
from markpress.utils.utils import strip_invalid_reportlab_img_tags


class ErrorLogRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = StyleConfig.get_pre_build_style("academic")

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        output = Path(self._tmp_dir.name) / "dummy.pdf"
        self.engine = MarkPressEngine(
            str(output),
            config=self.config,
            shared_katex=SimpleNamespace(close=lambda: None),
        )
        self.renderer = self.engine.list_renderer

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_strip_invalid_reportlab_img_tags_drops_missing_absolute_paths(self):
        broken = '<img src="/definitely/missing.png" width="24" height="24" alt="x" class="bad">'
        self.assertEqual(strip_invalid_reportlab_img_tags(broken), "")

    def test_strip_invalid_reportlab_img_tags_rebuilds_supported_attrs_only(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "ok.png"
            image_path.write_bytes(b"not-really-an-image")

            raw = (
                f'<img src="{image_path}" width="24" height="18" valign="-3" '
                'alt="x" class="bad" style="color:red">'
            )
            clean = strip_invalid_reportlab_img_tags(raw)

            self.assertIn('src="', clean)
            self.assertIn('width="24"', clean)
            self.assertIn('height="18"', clean)
            self.assertIn('valign="-3"', clean)
            self.assertNotIn("alt=", clean)
            self.assertNotIn("class=", clean)
            self.assertNotIn("style=", clean)

    def test_list_renderer_sanitizes_problematic_markup(self):
        raw = (
            'Kak bI noHmmeTe <a c yMhBm Jn11om ctana bI6upatb>? '
            '<img src="/definitely/missing.png" width="24" height="24" alt="x" class="bad">'
        )
        clean = self.renderer._sanitize_item_text(raw)

        self.assertNotIn("<a c", clean)
        self.assertNotIn("missing.png", clean)
        self.assertNotIn("alt=", clean)
        self.assertNotIn("class=", clean)

    def test_list_renderer_ignores_empty_nested_lists(self):
        flowables = self.renderer.render(["Parent", []])
        self.assertEqual(len(flowables), 1)
        self._assert_no_none_flowables(flowables[0])

    def test_media_height_keeps_safety_margin(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "dummy.pdf"
            engine = MarkPressEngine(
                str(output),
                config=self.config,
                shared_katex=SimpleNamespace(close=lambda: None),
            )

            plain_max = engine.get_media_max_height()
            reserved_max = engine.get_media_max_height(reserve_height=6 * mm)

            self.assertLess(plain_max, engine.doc.height)
            self.assertLess(reserved_max, plain_max)

    def _assert_no_none_flowables(self, node):
        stack = [node]
        seen = set()

        while stack:
            current = stack.pop()
            self.assertIsNotNone(current)

            current_id = id(current)
            if current_id in seen:
                continue
            seen.add(current_id)

            for attr_name in ("_flowables", "_content"):
                value = getattr(current, attr_name, None)
                if isinstance(value, list):
                    for item in value:
                        self.assertIsNotNone(item)
                        stack.append(item)


if __name__ == "__main__":
    unittest.main()
