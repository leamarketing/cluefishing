"""Regression checks for the missing images that reached the live site."""

import importlib.util
from pathlib import Path
import re
import shutil
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_news_images", REPO / "scripts/check_news_images.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class NewsImagesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(REPO / "news", self.root / "news")
        shutil.copytree(REPO / "no", self.root / "no")
        shutil.copyfile(REPO / "index.html", self.root / "index.html")

    def errors(self):
        return CHECK.check_site(self.root)[0]

    def change(self, path, edit):
        target = self.root / path
        target.write_text(edit(target.read_text(encoding="utf-8")), encoding="utf-8")

    def test_complete_site_passes(self):
        self.assertEqual(self.errors(), [])

    def test_text_only_edition_fails(self):
        self.change("news/2026-10-26.html", lambda text: re.sub(r'<img class="news-art"[^>]*>', "", text))
        self.assertTrue(any("needs one news-art image" in error for error in self.errors()))

    def test_missing_file_fails(self):
        (self.root / "news/images/2026-10-19-01-agent-vocabulary.webp").unlink()
        self.assertTrue(any("image invalid or missing" in error for error in self.errors()))

    def test_html_error_saved_as_webp_fails(self):
        (self.root / "news/images/2026-10-26-01-fetal-mri.webp").write_bytes(b"<html>404</html>")
        self.assertTrue(any("not a WebP file" in error for error in self.errors()))

    def test_empty_alt_fails(self):
        self.change("news/2026-10-26.html", lambda text: re.sub(r'alt="[^"]*"', 'alt=""', text, count=1))
        self.assertTrue(any("needs alt text" in error for error in self.errors()))

    def test_old_homepage_images_fail(self):
        self.change("index.html", lambda text: text.replace("2026-10-26-01-fetal-mri.webp", "2026-10-19-01-agent-vocabulary.webp"))
        self.assertTrue(any("homepage images must match" in error for error in self.errors()))

    def test_missing_translation_fails(self):
        (self.root / "no/news/2026-10-26.html").unlink()
        self.assertTrue(any("missing language page" in error for error in self.errors()))

    def test_external_image_fails(self):
        self.change("news/2026-10-26.html", lambda text: text.replace('src="images/', 'src="https://example.com/'))
        self.assertTrue(any("must use a local image path" in error for error in self.errors()))

    def test_generic_sharing_card_fails(self):
        self.change("news/2026-10-26.html", lambda text: text.replace("https://cluefishing.com/news/images/2026-10-26-01-fetal-mri.webp", "https://cluefishing.com/og.png"))
        self.assertTrue(any("must reference the lead story image" in error for error in self.errors()))


if __name__ == "__main__":
    unittest.main()
