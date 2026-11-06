"""The homepage stays fast only if fonts and news images stay off the critical path."""

from pathlib import Path
import re
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


if __name__ == "__main__":
    unittest.main()
