"""Generate the images a weekly edition's PR asks for, and add them to its pages.

The PR description holds a table with one row per story: filename, what the
photo should show, English alt text, Norwegian alt text. Nothing is paid for
until the table and the pages have been checked against each other, and each
image gets one API call with no retry.
"""

import argparse
import base64
from dataclasses import dataclass
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


MAX_IMAGES = 5
MAX_BYTES = 150 * 1024
SIZE = (1280, 400)
FILENAME = re.compile(r"news/images/(\d{4}-\d{2}-\d{2})-(\d{2})-[a-z0-9-]+\.webp")
CARD = re.compile(r'<div class="news-item">.*?(?=<div class="news-item">|<div class="news-foot">|<footer|\Z)', re.S)
SOURCED = re.compile(r'<a [^>]*class="source"[^>]*href="https?://')
NOTES = {
    "en": "Topic illustrations: generated with an AI image tool, then cropped.",
    "no": "Tematiske illustrasjoner: generert med et AI-billedverktøy, og deretter beskåret.",
}
NOTE_STYLE = 'class="mono" style="font-size:12px; color:var(--ink-soft); margin-top:14px;"'
PROMPT = (
    "Editorial news photograph, realistic and unposed, natural light. {scene} "
    "Wide composition with everything important in the middle horizontal band, "
    "because the top and bottom will be cropped away. No readable text, letters, "
    "numbers, logos or watermarks anywhere in the picture."
)


@dataclass
class Row:
    path: str
    scene: str
    alt_en: str
    alt_no: str


def parse_brief(body):
    """Return the image rows from a PR description, in story order."""
    rows = []
    for line in body.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and FILENAME.fullmatch(cells[0].strip("`")):
            rows.append(Row(cells[0].strip("`"), *cells[1:]))
    return rows


def check_brief(rows):
    """Reject a brief that could not produce a valid edition. Returns the edition date."""
    if not rows:
        raise ValueError("no image table found in the PR description")
    if len(rows) > MAX_IMAGES:
        raise ValueError(f"{len(rows)} images requested, the limit is {MAX_IMAGES}")
    dates = {FILENAME.fullmatch(row.path).group(1) for row in rows}
    if len(dates) != 1:
        raise ValueError(f"the table mixes editions: {sorted(dates)}")
    for number, row in enumerate(rows, 1):
        if FILENAME.fullmatch(row.path).group(2) != f"{number:02d}":
            raise ValueError(f"{row.path} should be story {number:02d}")
        if not (row.scene and row.alt_en and row.alt_no):
            raise ValueError(f"{row.path} has an empty cell in the table")
    return dates.pop()


def add_images(text, tags):
    """Put one image tag before the headline of each sourced story."""
    position = [0]

    def edit(match):
        card = match.group(0)
        if not SOURCED.search(card):
            return card
        if "news-art" in card:
            raise ValueError("a story already has an image")
        position[0] += 1
        if position[0] > len(tags):
            return card
        tag = tags[position[0] - 1]
        newline = "\r\n" if "\r\n" in card else "\n"
        return re.sub(r"([ \t]*)<h3", lambda m: f"{m.group(1)}{tag}{newline}{m.group(1)}<h3", card, count=1)

    result = CARD.sub(edit, text)
    if position[0] != len(tags):
        raise ValueError(f"the page has {position[0]} sourced stories, the table has {len(tags)} rows")
    return result


def patch_edition(text, rows, language, prefix):
    tags = []
    for number, row in enumerate(rows):
        alt = escape(row.alt_en if language == "en" else row.alt_no, quote=True)
        lazy = 'loading="lazy" decoding="async" ' if number else ""
        src = prefix + row.path.removeprefix("news/images/")
        tags.append(f'<img {lazy}class="news-art" src="{src}" alt="{alt}" width="1280" height="400">')
    text = add_images(text, tags)
    lead = f"https://cluefishing.com/{rows[0].path}"
    text, count = re.subn(r'(<meta (?:property="og:image"|name="twitter:image") content=")[^"]*(")',
                          rf"\g<1>{lead}\g<2>", text)
    if count != 2:
        raise ValueError("expected one og:image and one twitter:image tag")
    if NOTES[language] not in text:
        text, count = re.subn(r'(<footer>.*?)(\s*<a href="index\.html">)', rf"\g<1> {NOTES[language]}\g<2>", text, count=1, flags=re.S)
        if count != 1:
            raise ValueError("could not find the edition footer")
    return text


def patch_homepage(text, rows, language, prefix):
    tags = []
    for row in rows:
        alt = escape(row.alt_en if language == "en" else row.alt_no, quote=True)
        tags.append(f'<img class="news-art" src="{prefix}{row.path}" alt="{alt}" width="1280" height="400">')
    text = add_images(text, tags)
    if NOTES[language] not in text:
        note = f'<p {NOTE_STYLE}>{NOTES[language]}</p>'
        text, count = re.subn(r'([ \t]*)(<div class="news-foot">)', lambda m: f"{m.group(1)}{note}\n{m.group(1)}{m.group(2)}", text, count=1)
        if count != 1:
            raise ValueError("could not find the homepage news footer")
    return text


def patch_pages(root, rows, date):
    pages = {
        root / "news" / f"{date}.html": lambda t: patch_edition(t, rows, "en", "images/"),
        root / "no" / "news" / f"{date}.html": lambda t: patch_edition(t, rows, "no", "../../news/images/"),
        root / "index.html": lambda t: patch_homepage(t, rows, "en", ""),
        root / "no" / "index.html": lambda t: patch_homepage(t, rows, "no", "../"),
    }
    edited = {page: edit(page.read_bytes().decode("utf-8")) for page, edit in pages.items()}
    for page, text in edited.items():
        page.write_bytes(text.encode("utf-8"))


def to_webp(data):
    """Crop to the 16:5 band and compress until the file fits the size limit."""
    from PIL import Image

    image = Image.open(BytesIO(data)).convert("RGB")
    height = round(image.width * SIZE[1] / SIZE[0])
    top = (image.height - height) // 2
    image = image.crop((0, top, image.width, top + height)).resize(SIZE, Image.LANCZOS)
    for quality in range(82, 30, -6):
        buffer = BytesIO()
        image.save(buffer, "WEBP", quality=quality, method=6)
        if buffer.tell() <= MAX_BYTES:
            return buffer.getvalue()
    raise ValueError("could not compress the image under 150 KiB")


def generate(scene, key, model):
    """One paid API call. Returns the raw picture bytes."""
    payload = {"model": model, "prompt": PROMPT.format(scene=scene), "size": "1536x1024", "quality": "medium", "n": 1}
    request = Request("https://api.openai.com/v1/images/generations", data=json.dumps(payload).encode(),
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=300) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise ValueError(f"image API returned {exc.code}: {exc.read().decode(errors='replace')[:500]}") from exc
    return base64.b64decode(result["data"][0]["b64_json"])


def strip_brief(body):
    """Remove the missing-images section once the images exist."""
    body = re.sub(r"## Mangler bilder.*?(?=^## |\Z)", "", body, flags=re.S | re.M).lstrip()
    return re.sub(r"- \[ \] Story images[^\n]*", "- [x] Story images: generated by the news image workflow.", body)


def pull_requests_waiting_for_images(pulls):
    """Open pull requests whose titles still say the story images are missing.

    An edition opened before this workflow existed never receives the `opened`
    event, so a later run has to find it from the list of open pull requests.
    """
    numbers = []
    for pull in pulls:
        if str(pull.get("state") or "OPEN").upper() != "OPEN":
            continue
        if "[MANGLER BILDER]" not in (pull.get("title") or ""):
            continue
        number = pull.get("number")
        if isinstance(number, int) and not isinstance(number, bool) and number > 0:
            numbers.append(number)
    return numbers


def images_still_missing(root, rows):
    """True when the brief's files or page tags are not all in place yet."""
    root = Path(root)
    names = []
    for row in rows:
        names.append(Path(row.path).name)
        path = root / row.path
        if not path.is_file() or path.stat().st_size < 12:
            return True
    date = check_brief(rows)
    pages = [
        root / "news" / f"{date}.html",
        root / "no" / "news" / f"{date}.html",
        root / "index.html",
        root / "no" / "index.html",
    ]
    for page in pages:
        if not page.is_file():
            return True
        text = page.read_text(encoding="utf-8")
        if text.count("news-art") < len(rows):
            return True
        for name in names:
            if name not in text:
                return True
    return False


def should_mark_ready(event_name, generated_now):
    """Lift the draft hold only after this run actually adds the images.

    A scheduled look at a pull request that already has its images must leave
    the draft in place. Generating the missing files is what unblocks review.
    """
    if isinstance(generated_now, str):
        generated_now = generated_now == "true"
    if generated_now is not True:
        return False
    return event_name in {"pull_request", "workflow_dispatch", "schedule"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", type=Path, help="the PR description")
    parser.add_argument("--clean-body", type=Path, help="write the description without the brief here")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--select-waiting", action="store_true",
                        help="read pull-request JSON on stdin and print numbers that still need images")
    parser.add_argument("--images-needed", action="store_true",
                        help="print 'needed' or 'ready' for the brief, without calling the image API")
    parser.add_argument("--should-mark-ready", nargs=2, metavar=("EVENT", "GENERATED"),
                        help="print yes or no for whether this run should take the PR out of draft")
    args = parser.parse_args()

    if args.select_waiting:
        for number in pull_requests_waiting_for_images(json.load(sys.stdin)):
            print(number)
        return 0
    if args.should_mark_ready:
        event_name, generated_now = args.should_mark_ready
        print("yes" if should_mark_ready(event_name, generated_now) else "no")
        return 0
    if args.body_file is None:
        parser.error("--body-file is required")
    if args.images_needed:
        body = args.body_file.read_text(encoding="utf-8")
        rows = parse_brief(body)
        check_brief(rows)
        print("needed" if images_still_missing(args.root, rows) else "ready")
        return 0

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        print("OPENAI_API_KEY is not set for this repository.", file=sys.stderr)
        return 1
    model = os.environ.get("OPENAI_IMAGE_MODEL", "").strip() or "gpt-image-1"
    body = args.body_file.read_text(encoding="utf-8")
    try:
        rows = parse_brief(body)
        date = check_brief(rows)
        # Dry run against the pages, so a mismatch costs nothing.
        for page, edit in {
            args.root / "news" / f"{date}.html": lambda t: patch_edition(t, rows, "en", "images/"),
            args.root / "no" / "news" / f"{date}.html": lambda t: patch_edition(t, rows, "no", "../../news/images/"),
            args.root / "index.html": lambda t: patch_homepage(t, rows, "en", ""),
            args.root / "no" / "index.html": lambda t: patch_homepage(t, rows, "no", "../"),
        }.items():
            edit(page.read_bytes().decode("utf-8"))
        pictures = {row.path: to_webp(generate(row.scene, key, model)) for row in rows}
    except (OSError, ValueError, KeyError) as exc:
        print(f"Image generation stopped: {exc}", file=sys.stderr)
        return 1
    for path, data in pictures.items():
        (args.root / path).write_bytes(data)
        print(f"{path}: {len(data) // 1024} KB")
    patch_pages(args.root, rows, date)
    if args.clean_body:
        args.clean_body.write_text(strip_brief(body), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
