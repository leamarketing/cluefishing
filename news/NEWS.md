# Weekly AI News images

Each Monday edition includes one small illustration per story (usually three), placed above the headline. The homepage card that only points at last week's edition stays text-only.

Save original SVGs in `news/images/` as `YYYY-MM-DD-01-short-name.svg`, then `-02-` and `-03-`. Draw with ink `#10202B`, teal `#0E7C7B`, and brass `#8F6423` on a `#E7EBE9` band. Add a `prefers-color-scheme: dark` block (ink `#EDF2F1`, teal `#3BC0BB`, brass `#D9A054`, band `#16262F`) so the art follows the page. Keep each file to a few kilobytes. No stock photos and no external image hosts.

```html
<img class="news-art" src="PATH" alt="One sentence describing the picture, in the page language." width="640" height="160">
```

Put that line first inside `.news-item`, before the `<h3>`.

| Page | PATH |
| --- | --- |
| `index.html` | `news/images/YYYY-MM-DD-01-short-name.svg` |
| `news/YYYY-MM-DD.html` | `images/YYYY-MM-DD-01-short-name.svg` |
| `no/index.html` | `../news/images/YYYY-MM-DD-01-short-name.svg` |
| `no/news/YYYY-MM-DD.html` | `../../news/images/YYYY-MM-DD-01-short-name.svg` |

Use the same file on the English and Norwegian pages. Write the alt text in the language of that page, describing the picture rather than repeating the headline. Copy the `.news-art` CSS from `news/2026-09-28.html` when a new edition file does not already have it.
