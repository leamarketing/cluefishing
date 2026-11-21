# _stats: theme radar and statistics per edition

Not part of the public site: GitHub Pages (Jekyll) skips folders that start with `_`. The repository itself is public, so nothing private goes here.

The news routine (Monday, Wednesday and Friday) writes two files here in the same PR as each edition:

- `_stats/data/YYYY-MM-DD.csv`: columns `dato,maling,kategori,antall,merknad`.
  - `radar_anslag`: stories on the site's theme that the web search found since the previous edition, per category (an estimate, not a full count).
  - `publisert`: stories in this week's edition, per category (measured).
  - `kilde`: source domains of this week's stories (measured).
- `_stats/cluefishing_trender_YYYY-MM-DD.md`: short analysis in Norwegian (what is moving, what grows or shrinks against earlier editions, use in marketing).

Categories (fixed): `merking_herkomst`, `deepfakes`, `regulering`, `misbruk_udeklarert`, `norge` (the site's own theme), and `sikkerhet`, `helse`, `biologi`, `forskning`, `modeller_verktoy`.

Never write a number that was not counted or found. Missing data is written as `DATA MANGLER`.

`2026-11-18-grunnlag.csv` is the baseline: every story published 14.09-16.11.2026, counted from the HTML files, plus the first radar.

The files are copied into Geir's Obsidian vault (`Statistikk/cluefishing/`) by `hent_statistikk.py` there, which also builds the over-time summary.
