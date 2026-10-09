# Weekly AI News images

Each Monday edition includes one photo-like topic image per story (usually three), placed above the headline. The picture should show the subject of that story, so a reader can tell what the item is about before reading it. The homepage card that only points at last week's edition stays text-only.

Save original images in `news/images/` as `YYYY-MM-DD-01-short-name.webp`, then `-02-` and `-03-`. Use a wide landscape band, about 1280×400 (16:5). Photographic or photo-like pictures are the default: a real scene, object, or interface that belongs to the story. Do not use abstract SVG icons or decorative diagrams. No stock-photo hosts and no external image hosts. Keep each file under about 150KB.

If an image is generated with an AI image tool, say so on the edition in the page language, in the same plain style as the rest of the site: "generated with an AI image tool, then cropped" (Norwegian: "generert med et AI-billedverktøy, og deretter beskåret").

```html
<img class="news-art" src="PATH" alt="One sentence describing what is in the photograph, in the page language." width="1280" height="400">
```

Put that line first inside `.news-item`, before the `<h3>`.

| Page | PATH |
| --- | --- |
| `index.html` | `news/images/YYYY-MM-DD-01-short-name.webp` |
| `news/YYYY-MM-DD.html` | `images/YYYY-MM-DD-01-short-name.webp` |
| `no/index.html` | `../news/images/YYYY-MM-DD-01-short-name.webp` |
| `no/news/YYYY-MM-DD.html` | `../../news/images/YYYY-MM-DD-01-short-name.webp` |

Use the same file on the English and Norwegian pages. Write the alt text in the language of that page, describing what is visible in the photograph rather than repeating the headline. `.news-art` uses `aspect-ratio: 16 / 5` and `object-fit: cover`. Copy that rule from `news/2026-09-28.html` when a new edition file does not already have it.

## Head tags and sitemap

There is no page generator. The weekly edition change has to add the tags and the sitemap entries itself. Copy the `<head>` block from the newest pair, `news/2026-10-05.html` and `no/news/2026-10-05.html`, and keep these rules:

- `<link rel="canonical">` is the absolute URL of that page (`https://cluefishing.com/news/YYYY-MM-DD.html` or `https://cluefishing.com/no/news/YYYY-MM-DD.html`).
- Add `hreflang` alternates for `en`, `no`, and `x-default`. `x-default` points at the English URL. Point `en` and `no` only at pages that exist. The 15 September 2026 edition is English-only, so it has no `hreflang="no"` and no Norwegian sitemap URL.
- Open Graph: `og:title`, `og:description`, `og:url`, `og:type` (`article`), `og:image`, `og:locale`, and `og:locale:alternate` when the other language exists. Twitter: `twitter:card` (`summary_large_image`), `twitter:title`, `twitter:description`, `twitter:image`.
- `og:title` and `twitter:title` match `<title>`. The descriptions match `<meta name="description">`.
- `og:image` and `twitter:image` are the absolute URL of that edition's lead image, `https://cluefishing.com/news/images/YYYY-MM-DD-01-short-name.webp` (the `-01-` file). If the edition has no story image, use `https://cluefishing.com/og.png`.
- English `og:locale` is `en_GB` (alternate `nb_NO`). Norwegian `og:locale` is `nb_NO` (alternate `en_GB`). Keep `hreflang` as `en` and `no`, matching `<html lang>`.
- Keep the favicon links (`/favicon.ico`, `/favicon.svg`, `/favicon-32.png`, `/apple-touch-icon.png`).
- In `sitemap.xml`, add each language URL that exists, with `<lastmod>` set to the publication date (`YYYY-MM-DD`). Set `<lastmod>` on `https://cluefishing.com/`, `/no/`, `/news/`, and `/no/news/` to that same date. Do not list a URL that has no file.
