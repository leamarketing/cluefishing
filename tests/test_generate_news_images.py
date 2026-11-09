"""Checks for the image workflow's table parsing and page edits. No network calls."""

import importlib.util
from pathlib import Path
import re
import shutil
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load("check_news_images")
GEN = load("generate_news_images")
DATE = sorted(path.stem for path in (REPO / "news").glob("????-??-??.html")
              if path.stem >= CHECK.FIRST_ILLUSTRATED_EDITION)[-1]
NAMES = re.findall(rf'src="images/{DATE}-(\d{{2}}-[a-z0-9-]+)\.webp"',
                   (REPO / "news" / f"{DATE}.html").read_text(encoding="utf-8"))
BODY = "## Mangler bilder - ikke auto-merge\n\nNo tool.\n\n| Filename | Scene | EN | NO |\n| --- | --- | --- | --- |\n" + "".join(
    f'| `news/images/{DATE}-{name}.webp` | Scene {name}. | English "alt" {name}. | Norsk alt {name}. |\n' for name in NAMES
) + "\n## This week's items\n\n- [ ] Story images - see table above.\n"


class GenerateNewsImagesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(REPO / "news", self.root / "news")
        shutil.copytree(REPO / "no", self.root / "no")
        shutil.copyfile(REPO / "index.html", self.root / "index.html")
        self.rows = GEN.parse_brief(BODY)

    def strip_images(self):
        pages = [f"news/{DATE}.html", f"no/news/{DATE}.html", "index.html", "no/index.html"]
        for page in pages:
            target = self.root / page
            text = target.read_bytes().decode("utf-8")
            text = re.sub(r'[ \t]*<img [^>]*class="news-art"[^>]*>\r?\n', "", text)
            text = text.replace(f"https://cluefishing.com/news/images/{DATE}-{NAMES[0]}.webp", "https://cluefishing.com/og.png")
            target.write_bytes(text.encode("utf-8"))

    def test_brief_is_parsed_in_order(self):
        self.assertEqual([row.path for row in self.rows], [f"news/images/{DATE}-{name}.webp" for name in NAMES])
        self.assertEqual(GEN.check_brief(self.rows), DATE)

    def test_patched_edition_passes_the_image_check(self):
        self.strip_images()
        self.assertTrue(CHECK.check_site(self.root)[0])
        GEN.patch_pages(self.root, self.rows, DATE)
        self.assertEqual(CHECK.check_site(self.root)[0], [])

    def test_note_is_not_added_twice(self):
        self.strip_images()
        GEN.patch_pages(self.root, self.rows, DATE)
        text = (self.root / "news" / f"{DATE}.html").read_text(encoding="utf-8")
        self.assertEqual(text.count(GEN.NOTES["en"]), 1)

    def test_alt_text_is_escaped(self):
        self.strip_images()
        GEN.patch_pages(self.root, self.rows, DATE)
        text = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"English &quot;alt&quot; {NAMES[0]}.", text)

    def test_previous_edition_card_stays_text_only(self):
        self.strip_images()
        GEN.patch_pages(self.root, self.rows, DATE)
        text = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertEqual(text.count(f'class="news-art" src="news/images/{DATE}-'), 3)

    def test_row_count_mismatch_is_rejected(self):
        self.strip_images()
        with self.assertRaises(ValueError):
            GEN.patch_pages(self.root, self.rows[:2], DATE)

    def test_page_with_images_is_rejected(self):
        with self.assertRaises(ValueError):
            GEN.patch_pages(self.root, self.rows, DATE)

    def test_wrong_story_number_is_rejected(self):
        self.rows[0].path = f"news/images/{DATE}-02-fetal-mri.webp"
        with self.assertRaises(ValueError):
            GEN.check_brief(self.rows)

    def test_too_many_images_are_rejected(self):
        with self.assertRaises(ValueError):
            GEN.check_brief(self.rows * 2)

    def test_unsafe_filename_is_ignored(self):
        body = "| `../../index.html` | Scene. | EN. | NO. |"
        self.assertEqual(GEN.parse_brief(body), [])

    def test_brief_is_removed_from_description(self):
        clean = GEN.strip_brief(BODY)
        self.assertTrue(clean.startswith("## This week's items"))
        self.assertIn("- [x] Story images", clean)


if __name__ == "__main__":
    unittest.main()
