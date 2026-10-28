"""Check the static news image contract without network calls or dependencies."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


FIRST_ILLUSTRATED_EDITION = "2026-09-28"
MAX_BYTES = 150 * 1024
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}


class NewsPage(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.cards = []
        self.current = None
        self.meta = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            self.meta[attrs.get("property", attrs.get("name"))] = attrs.get("content")
        if "news-item" in attrs.get("class", "").split():
            self.current = {"depth": len(self.stack) + 1, "first": None,
                            "images": [], "sources": []}
            self.cards.append(self.current)
        elif self.current:
            if len(self.stack) == self.current["depth"] and self.current["first"] is None:
                self.current["first"] = tag
            if tag == "img" and "news-art" in attrs.get("class", "").split():
                self.current["images"].append(attrs)
            if tag == "a" and "source" in attrs.get("class", "").split():
                self.current["sources"].append(attrs.get("href", ""))
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack:
                if self.stack.pop() == tag:
                    break
        if self.current and len(self.stack) < self.current["depth"]:
            self.current = None


def webp_size(data):
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a WebP file")
    if int.from_bytes(data[4:8], "little") + 8 != len(data):
        raise ValueError("truncated or invalid WebP container")
    pos = 12
    while pos + 8 <= len(data):
        kind = data[pos:pos + 4]
        length = int.from_bytes(data[pos + 4:pos + 8], "little")
        chunk = data[pos + 8:pos + 8 + length]
        if len(chunk) != length:
            raise ValueError("truncated WebP chunk")
        if kind == b"VP8 " and len(chunk) >= 10 and chunk[3:6] == b"\x9d\x01\x2a":
            return (int.from_bytes(chunk[6:8], "little") & 0x3fff,
                    int.from_bytes(chunk[8:10], "little") & 0x3fff)
        if kind == b"VP8L" and len(chunk) >= 5 and chunk[0] == 0x2f:
            bits = int.from_bytes(chunk[1:5], "little")
            return ((bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1)
        if kind == b"VP8X" and len(chunk) >= 10:
            return (int.from_bytes(chunk[4:7], "little") + 1,
                    int.from_bytes(chunk[7:10], "little") + 1)
        pos += 8 + length + length % 2
    raise ValueError("missing WebP dimensions")


def check_site(root):
    root = root.resolve()
    errors = []
    checked = set()

    def error(page, message):
        errors.append(f"{page.relative_to(root)}: {message}")

    def check_page(page, edition, homepage=False):
        if not page.is_file():
            error(page, "missing language page")
            return []
        parsed = NewsPage(page.read_text(encoding="utf-8"))
        paths = []
        stories = [c for c in parsed.cards if any(
            urlsplit(href).scheme in ("http", "https") for href in c["sources"])]
        if not stories:
            error(page, "no sourced news stories found")
        for number, card in enumerate(stories, 1):
            label = f"story {number}"
            if len(card["images"]) != 1 or card["first"] != "img":
                error(page, f"{label} needs one news-art image before its headline")
                continue
            image = card["images"][0]
            if not image.get("alt", "").strip():
                error(page, f"{label} needs alt text")
            if (image.get("width"), image.get("height")) != ("1280", "400"):
                error(page, f"{label} needs width=1280 and height=400")
            src = urlsplit(image.get("src", ""))
            if src.scheme or src.netloc or not src.path or src.query or src.fragment:
                error(page, f"{label} must use a local image path")
                continue
            path = ((root if src.path.startswith("/") else page.parent)
                    / unquote(src.path).lstrip("/")).resolve()
            if not path.is_relative_to(root / "news" / "images"):
                error(page, f"{label} must use news/images/")
                continue
            paths.append(path)
            if not re.fullmatch(rf"{re.escape(edition)}-{number:02d}-[a-z0-9-]+\.webp", path.name):
                error(page, f"{label} image date or story number does not match")
            if path not in checked:
                checked.add(path)
                try:
                    data = path.read_bytes()
                    if len(data) > MAX_BYTES:
                        raise ValueError("WebP exceeds 150 KiB")
                    if webp_size(data) != (1280, 400):
                        raise ValueError("WebP must be 1280x400")
                except (OSError, ValueError) as exc:
                    error(page, f"{label} image invalid or missing: {path.name}: {exc}")
        if paths and not homepage:
            lead = "https://cluefishing.com/" + paths[0].relative_to(root).as_posix()
            for key in ("og:image", "twitter:image"):
                if parsed.meta.get(key) != lead:
                    error(page, f"{key} must reference the lead story image")
        return paths

    editions = sorted(p.stem for p in (root / "news").glob("????-??-??.html")
                      if p.stem >= FIRST_ILLUSTRATED_EDITION)
    if not editions:
        return ["No illustrated editions found."], 0, 0
    latest_paths = []
    for edition in editions:
        en = check_page(root / "news" / f"{edition}.html", edition)
        no = check_page(root / "no" / "news" / f"{edition}.html", edition)
        if en != no:
            errors.append(f"{edition}: English and Norwegian story images must match in order")
        latest_paths = en
    # Also catch an accidentally unpaired Norwegian-only edition.
    for page in (root / "no" / "news").glob("????-??-??.html"):
        if page.stem >= FIRST_ILLUSTRATED_EDITION and page.stem not in editions:
            error(page, "missing English edition")
    for homepage in (root / "index.html", root / "no" / "index.html"):
        paths = check_page(homepage, editions[-1], homepage=True)
        if paths != latest_paths:
            error(homepage, "homepage images must match the latest edition")
    return errors, len(editions), len(checked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors, editions, images = check_site(args.root)
    if errors:
        print("News image validation failed:", file=sys.stderr)
        print("\n".join(f"- {message}" for message in errors), file=sys.stderr)
        return 1
    print(f"News image validation passed: {editions} bilingual editions, {images} local WebP images, both homepages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
