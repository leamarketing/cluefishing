# Cluefishing

Static GitHub Pages site. English lives at the site root. Norwegian lives under `/no/`. Weekly AI News editions are `news/YYYY-MM-DD.html` and `no/news/YYYY-MM-DD.html`, listed from `news/index.html` and `no/news/index.html`.

There is no page generator. A weekly edition change has to update the pages and `sitemap.xml` by hand.

## Weekly edition

Ship both languages in the same change unless an edition is deliberately English-only (the 15 September 2026 edition is the existing case). Image files and alt text are specified in `news/NEWS.md`.

On every new HTML page, after the description, include the same head tags as `news/2026-10-05.html` and `no/news/2026-10-05.html`:

- `<link rel="canonical">` with that page's absolute `https://cluefishing.com/...` URL.
- `hreflang` alternates for `en`, `no`, and `x-default`. `x-default` is the English URL. Link `en` and `no` only to pages that exist. Do not add `hreflang="no"` for a missing Norwegian edition.
- Open Graph: `og:title`, `og:description`, `og:url`, `og:type` (`article` on an edition, `website` on a homepage or archive), `og:image`, `og:locale`, and `og:locale:alternate` when the other language exists.
- Twitter card: `twitter:card` (`summary_large_image`), `twitter:title`, `twitter:description`, `twitter:image`.
- Favicon links: `/favicon.ico`, `/favicon.svg`, `/favicon-32.png`, `/apple-touch-icon.png`.

`og:title` and `twitter:title` match `<title>`. Descriptions match `<meta name="description">`. On an edition, `og:image` and `twitter:image` are the absolute URL of that edition's lead story image (`https://cluefishing.com/news/images/YYYY-MM-DD-01-….webp`). Homepages, archives, and an edition with no story image use `https://cluefishing.com/og.png`.

English `og:locale` is `en_GB` and its alternate is `nb_NO`. Norwegian `og:locale` is `nb_NO` and its alternate is `en_GB`. `hreflang` stays `en` and `no`, matching `<html lang>`.

In `sitemap.xml`, add each language URL that exists and set `<lastmod>` to the publication date (`YYYY-MM-DD`). Set `<lastmod>` on `/`, `/no/`, `/news/`, and `/no/news/` to that same date. Do not list a URL that has no file.
