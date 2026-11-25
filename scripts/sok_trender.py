"""Search-demand radar for Cluefishing: what people type into search engines on the site's theme.

Fetches autocomplete suggestions (Google, Bing) and recent Google News headlines for a fixed set
of theme words in Norway (Norwegian) and the UK (English). Needs no key and only the standard library.

What the numbers mean: a count is the number of DIFFERENT suggestions or headlines found, never the
number of searches or readers. Search volume is not available (Google Trends has no open API).

Usage:
  python scripts/sok_trender.py            # today's date
  python scripts/sok_trender.py 2026-11-25 # a given date

Writes:
  _stats/data/<dato>-sok.csv           every suggestion and headline (dato,land,kilde,sok,funn,kategori,nyhetsdato)
  _stats/data/<dato>-sok-sammendrag.md short summary in Norwegian, used by the news routine
Prints the sok_trend rows for _stats/data/<dato>.csv to stdout. If every lookup fails, it writes
DATA MANGLER and exits with status 2, so the routine can say so instead of guessing.
"""
import csv, datetime, html, json, os, re, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (cluefishing-sok-trender)"}

LAND = {
    "no": {"navn": "Norge", "hl": "no", "gl": "no", "bing": "nb-NO",
           "sok": ["deepfake", "ki-merking", "ki-generert", "ki-bilde", "ai detector", "ki-detektor",
                   "avsløre ki", "chatgpt juks", "ki-loven", "falske bilder"],
           "forledd": ["", "hvordan ", "hva er ", "er det lov "]},
    "gb": {"navn": "Storbritannia", "hl": "en", "gl": "gb", "bing": "en-GB",
           "sok": ["deepfake", "ai detector", "ai generated", "ai label", "content credentials",
                   "ai watermark", "eu ai act", "is it ai"],
           "forledd": ["", "how to ", "is ", "why "]},
}

# Order matters: the first match wins. Categories are the fixed list in _stats/README.md.
KATEGORI = [
    ("deepfakes", r"deepfake|deep fake|stemmeklon|voice clon|face ?swap|falsk(e)? (bilde|video)|fake (video|image|photo)"),
    ("merking_herkomst", r"merk|label|watermark|vannmerk|c2pa|content credential|synthid|herkomst|provenance|metadata"),
    ("norge", r"ki-loven|\bnorge\b|\bnorsk|datatilsynet|nkom"),
    ("regulering", r"\blov\b|lovlig|ulovlig|\blaw\b|legal|illegal|crime|straff|regel|regul|ai act|ki-forordning|forbud|ban\b"),
    ("misbruk_udeklarert", r"detect|detekt|oppdage|avsløre|sjekke|check|juks|cheat|plagiat|turnitin|is it ai|ai or not|ekte eller"),
    ("sikkerhet", r"svindel|scam|fraud|phishing|identitet"),
    ("modeller_verktoy", r"chatgpt|gemini|claude|copilot|midjourney|generator|app\b|tool|verktøy"),
]


def hent(url, forsok=2):
    feil = None
    for _ in range(forsok):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15).read().decode("utf-8", "replace")
        except Exception as e:
            feil = e
            time.sleep(1.5)
    raise feil


def google(q, L):
    return json.loads(hent("https://suggestqueries.google.com/complete/search?client=firefox&ie=utf-8&oe=utf-8&hl=%s&gl=%s&q=%s"
                           % (L["hl"], L["gl"], urllib.parse.quote(q))))[1]


def bing(q, L):
    return json.loads(hent("https://api.bing.com/osjson.aspx?mkt=%s&query=%s" % (L["bing"], urllib.parse.quote(q))))[1]


def nyheter(q, L):
    gl = L["gl"].upper()
    x = hent("https://news.google.com/rss/search?q=%s+when:14d&hl=%s&gl=%s&ceid=%s:%s"
             % (urllib.parse.quote(q), L["hl"], gl, gl, L["hl"]))
    ut = []
    for item in re.findall(r"<item>(.*?)</item>", x, re.S)[:20]:
        t = re.search(r"<title>(.*?)</title>", item, re.S)
        d = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
        if t:
            ut.append((html.unescape(t.group(1)).strip(), d.group(1).strip()[5:16] if d else ""))
    return ut


# A suggestion is kept only when it is still about AI. Autocomplete drifts ("er det lov ..." ends in
# winter tyres), and those suggestions say nothing about the site's theme.
OM_KI = re.compile(r"(^|[^a-zæøå])(ki|ai|a\.i\.)([^a-zæøå]|$)|ki-|kunstig intelligens|artificial intelligence|deep ?fake|chatgpt"
                   r"|c2pa|content credential|synthid|watermark|vannmerk|detekt|detector|gpt", re.I)


def om_ki(tekst):
    return bool(OM_KI.search(tekst))


def kategori(tekst):
    low = tekst.lower()
    for kat, rx in KATEGORI:
        if re.search(rx, low):
            return kat
    return "annet"


def main():
    dato = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    rader, oppslag, feil = [], 0, Counter()
    sett = set()
    # A source that has never answered and has failed 4 times is skipped for the rest of the run,
    # so a blocked search engine costs about a minute instead of stalling the routine.
    svar, sperret = Counter(), set()

    def gi_opp(kilde):
        if not svar[kilde] and feil[kilde] >= 4:
            sperret.add(kilde)

    for kode, L in LAND.items():
        for sok in L["sok"]:
            for forledd in L["forledd"]:
                q = forledd + sok
                for kilde, fn in (("google", google), ("bing", bing)):
                    if kilde in sperret:
                        continue
                    oppslag += 1
                    try:
                        forslag = fn(q, L)
                        svar[kilde] += 1
                    except Exception:
                        feil[kilde] += 1
                        gi_opp(kilde)
                        continue
                    for f in forslag:
                        nok = (kode, f.strip().lower())
                        if f.strip().lower() == q.lower() or nok in sett or not om_ki(f):
                            continue
                        sett.add(nok)
                        rader.append({"dato": dato, "land": L["navn"], "kilde": kilde, "sok": q, "funn": f.strip(),
                                      "kategori": kategori(f), "nyhetsdato": ""})
                    time.sleep(0.15)
            if "nyheter" in sperret:
                continue
            oppslag += 1
            try:
                treff = nyheter(sok, L)
                svar["nyheter"] += 1
                for tittel, nd in treff:
                    nok = (kode, "nyhet", tittel.lower())
                    if nok in sett:
                        continue
                    sett.add(nok)
                    rader.append({"dato": dato, "land": L["navn"], "kilde": "nyheter", "sok": sok, "funn": tittel,
                                  "kategori": kategori(sok + " " + tittel), "nyhetsdato": nd})
            except Exception:
                feil["nyheter"] += 1
                gi_opp("nyheter")

    os.makedirs(os.path.join(ROT, "_stats", "data"), exist_ok=True)
    csvf = os.path.join(ROT, "_stats", "data", "%s-sok.csv" % dato)
    mdf = os.path.join(ROT, "_stats", "data", "%s-sok-sammendrag.md" % dato)
    feiltekst = ", ".join("%s %d" % kv for kv in sorted(feil.items())) or "ingen"
    if sperret:
        feiltekst += "; ga opp: %s (svarte aldri)" % ", ".join(sorted(sperret))

    if not rader:
        with open(mdf, "w", encoding="utf-8") as f:
            f.write("# Søketrender %s\n\nDATA MANGLER: ingen svar fra søkemotorene (%d oppslag, feil: %s).\n" % (dato, oppslag, feiltekst))
        print("DATA MANGLER: ingen svar fra søkemotorene (%d oppslag, feil: %s)" % (oppslag, feiltekst))
        sys.exit(2)

    with open(csvf, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["dato", "land", "kilde", "sok", "funn", "kategori", "nyhetsdato"])
        w.writeheader()
        w.writerows(rader)

    forslag = [r for r in rader if r["kilde"] != "nyheter"]
    nyh = [r for r in rader if r["kilde"] == "nyheter"]
    per_kat = Counter(r["kategori"] for r in forslag)
    eksempler = defaultdict(list)
    for r in forslag:
        if len(eksempler[r["kategori"]]) < 6:
            eksempler[r["kategori"]].append(r["funn"])

    md = ["# Søketrender %s" % dato, "",
          "Kilder: søkeforslag fra Google og Bing, og overskrifter fra Google Nyheter siste 14 dager, i Norge og Storbritannia.",
          "Antall = antall ulike forslag eller overskrifter. Det viser hva folk skriver i søkefeltet, ikke hvor mange som søker.",
          "Antallet avhenger også av hvilke ord skriptet spør med, så sammenlign en kategori med seg selv over tid, ikke kategoriene med hverandre.",
          "Oppslag: %d. Feil: %s." % (oppslag, feiltekst), "",
          "## Søkeforslag per kategori", "", "| Kategori | Ulike forslag | Eksempler |", "|---|---|---|"]
    for kat, n in per_kat.most_common():
        md.append("| %s | %d | %s |" % (kat, n, "; ".join(eksempler[kat])))
    for land in ("Norge", "Storbritannia"):
        rr = [r for r in forslag if r["land"] == land and r["sok"].split(" ")[0] in ("hvordan", "hva", "er", "how", "is", "why")]
        md += ["", "## Spørsmål folk stiller, %s" % land, ""]
        md += ["- %s" % r["funn"] for r in rr[:25]] or ["- (ingen)"]
    md += ["", "## Nyeste overskrifter, Norge", ""]
    md += ["- %s (%s)" % (r["funn"], r["nyhetsdato"]) for r in nyh if r["land"] == "Norge"][:20] or ["- (ingen)"]
    with open(mdf, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    for kat, n in per_kat.most_common():
        if kat == "annet":
            continue
        merk = "; ".join(eksempler[kat][:3]).replace('"', "'")
        print('%s,sok_trend,%s,%d,"%s"' % (dato, kat, n, merk))
    print("# %d ulike søkeforslag, %d overskrifter, %d oppslag, feil: %s" % (len(forslag), len(nyh), oppslag, feiltekst), file=sys.stderr)


if __name__ == "__main__":
    main()
