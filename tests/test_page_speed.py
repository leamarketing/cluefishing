"""The homepage stays fast only if fonts and news images stay off the critical path."""

import importlib.util
from pathlib import Path
import re
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
FONTS = {
    "source-serif-4-latin.woff2": 60 * 1024,
    "big-shoulders-display-latin.woff2": 40 * 1024,
    "ibm-plex-mono-latin.woff2": 15 * 1024,
}


class PageSpeedTest(unittest.TestCase):
    def test_pages_do_not_block_on_google_fonts(self):
        for page in REPO.rglob("*.html"):
            text = page.read_text(encoding="utf-8")
            self.assertNotIn("fonts.googleapis.com", text, page)
            self.assertNotIn("fonts.gstatic.com", text, page)
            self.assertIn('rel="preload" href="/fonts/source-serif-4-latin.woff2"', text, page)

    def test_local_fonts_are_small_woff2(self):
        for name, limit in FONTS.items():
            path = REPO / "fonts" / name
            data = path.read_bytes()
            self.assertTrue(data.startswith(b"wOF2"), name)
            self.assertLess(len(data), limit, name)

    def test_homepage_news_images_offer_a_mobile_candidate(self):
        text = (REPO / "index.html").read_text(encoding="utf-8")
        srcsets = re.findall(r'srcset="(news/images/[^"]+)"', text)
        self.assertEqual(len(srcsets), 3)
        self.assertEqual(text.count('loading="lazy"'), 3)
        self.assertIn("92vw", text)
        self.assertNotIn("100vw, 880px", text)
        for srcset in srcsets:
            small, large = (part.strip().split(" ", 1)[0] for part in srcset.split(","))
            small_path = REPO / small
            large_path = REPO / large
            self.assertTrue(small.endswith("-720.webp"), small)
            self.assertLess(small_path.stat().st_size, 40 * 1024, small)
            self.assertLess(small_path.stat().st_size, large_path.stat().st_size, small)


class WebpImagesTest(unittest.TestCase):
    def check(self):
        spec = importlib.util.spec_from_file_location("check_news_images", REPO / "scripts/check_news_images.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_repository_images_are_genuine_webp_except_favicons(self):
        self.assertEqual(self.check().check_website_images(REPO), [])

    def test_share_card_is_webp_without_a_png_copy(self):
        data = (REPO / "og.webp").read_bytes()
        self.assertEqual(data[8:12], b"WEBP")
        self.assertFalse((REPO / "og.png").exists())
        self.assertNotIn("og.png", (REPO / "index.html").read_text(encoding="utf-8"))

    def test_renamed_or_extra_raster_files_fail(self):
        check = self.check()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "photo.webp").write_bytes(b"\xff\xd8\xff\xe0not-a-webp")
            (root / "shot.png").write_bytes(b"\x89PNG\r\n")
            (root / "index.html").write_text(
                '<meta property="og:image" content="https://cluefishing.com/shot.png">',
                encoding="utf-8",
            )
            for name in check.FAVICON_EXCEPTIONS:
                (root / name).write_bytes(b"platform-icon")
            errors = check.check_website_images(root)
        self.assertTrue(any("photo.webp: not a genuine WebP file" in error for error in errors))
        self.assertTrue(any("shot.png: website image must be genuine WebP" in error for error in errors))
        self.assertTrue(any("image reference must be WebP" in error for error in errors))
        self.assertFalse(any(error.startswith(f"{name}:") for name in check.FAVICON_EXCEPTIONS for error in errors))


if __name__ == "__main__":
    unittest.main()
