#!/usr/bin/env python3
"""Convert BOPA documents cached by ad_fetch.py into Markdown files."""
import datetime
import html as htmlmod
import json
import os
import re
import shutil
import sys
import unicodedata
import urllib.parse
from collections import Counter
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import MarkdownConverter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RAW = os.path.abspath(os.environ.get("AD_RAW", os.path.join(REPO, "..", "_raw", "ad")))
RETRIEVED = os.environ.get("AD_RETRIEVED", datetime.date.today().isoformat())
TZ = ZoneInfo("Europe/Andorra")

KEYS = [
    ("llibre", r"(?:LLIBRE|Llibre)"),
    ("part", r"(?:PART|Part)"),
    ("titol", r"(?:TÍTOL|Títol|TITOL|Titol)"),
    ("capitol", r"(?:CAPÍTOL|Capítol|CAPITOL|Capitol)"),
    ("seccio", r"(?:SECCIÓ|Secció|SECCIO|Seccio)"),
    ("subseccio", r"(?:SUBSECCIÓ|Subsecció)"),
]
ORD = r"(?:[IVXLC]+|\d+|preliminar|primer|primera|segon|segona|tercer|tercera|quart|quarta|cinquè|cinquena|" \
      r"sisè|sisena|setè|setena|vuitè|vuitena|novè|novena|desè|desena|onzè|onzena|dotzè|dotzena|tretzè|tretzena|" \
      r"catorzè|catorzena|quinzè|quinzena|setzè|setzena|dissetè|dissetena|divuitè|divuitena|dinovè|dinovena|" \
      r"vintè|vintena|únic|única|[a-zàèéíòóúç]+è|[a-zàèéíòóúç]+ena)\b"
KEY_RE = [(k, re.compile(r"^%s\s+%s" % (p, ORD), re.I)) for k, p in KEYS]
ART_RE = re.compile(r"^(?:Article|ARTICLE|Art\.)\s+(?:\d+[\w\s]{0,12}|únic|primer|[a-zàèéíòóú]+)\.?(?:\s.{0,200})?$")
OTHER_RE = re.compile(r"^(?:Disposici[óo](?:ns)?\s+(?:addicional|transit[òo]ria|derogat[òo]ria|final)s?|"
                      r"DISPOSICI[ÓO]|Exposició de motius|EXPOSICIÓ DE MOTIUS|Preàmbul|PREÀMBUL|Annex|ANNEX)\b.{0,200}$")


def slugify(s, maxlen=80):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen].rstrip("-") or "text"


def clean_sumari(s):
    s = s or ""
    s = urllib.parse.unquote(s)
    s = htmlmod.unescape(s)
    s = re.sub(r"<[^>]+>", "", s)
    if " " not in s.strip() and "+" in s:
        s = s.replace("+", " ")
    elif s.count("+") > 3 and s.count(" ") < s.count("+"):
        s = s.replace("+", " ")
    return re.sub(r"\s+", " ", s).strip()


def local_date(iso):
    if not iso:
        return None
    d = datetime.datetime.fromisoformat(iso)
    return d.astimezone(TZ).date().isoformat()


def classify(t, strict_len=200):
    if len(t) > strict_len:
        return None
    if ART_RE.match(t):
        return "art"
    for k, rx in KEY_RE:
        if rx.match(t):
            return k
    if OTHER_RE.match(t):
        return "other"
    return None


class MD(MarkdownConverter):
    def convert_a(self, el, text, *a, **k):
        href = el.get("href") or ""
        if href.startswith("/"):
            href = "https://www.bopa.ad" + href
        text = text.strip()
        if href.startswith("http") and text:
            return f"[{text}]({href})"
        return text

    def convert_img(self, el, text, *a, **k):
        return ""


def md(frag):
    return MD(heading_style="ATX", bullets="-").convert(frag).strip()


def esc(t):
    t = re.sub(r"^(\d+)\.(\s)", r"\1\\.\2", t)
    t = re.sub(r"^([#>+])", r"\\\1", t)
    t = re.sub(r"^([-*])(\s)", r"\\\1\2", t)
    return t


def units_modern(soup):
    """Paragraph units from InDesign-exported HTML: (text, is_title_style, raw_markdown_block)."""
    out = []
    body = soup.body or soup
    for el in body.find_all(["p", "table", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6"]):
        if el.find_parent(["table", "ul", "ol"]):
            continue
        if el.name in ("table", "ul", "ol"):
            out.append((None, False, md(str(el))))
            continue
        cls = " ".join(el.get("class") or [])
        txt = re.sub(r"\s+", " ", el.get_text(" ")).strip()
        if not txt:
            continue
        out.append((txt, cls.startswith("Titol") or el.name.startswith("h"), md(str(el)).replace("\n", " ")))
    return out


def units_old(text):
    """Old documents: one physical line per <br>; rebuild paragraphs."""
    text = re.sub(r"[\r\n]+", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</?(p|div|tr|td|table|li)[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = htmlmod.unescape(text)
    lines = [re.sub(r"[ \t\xa0]+", " ", l).strip() for l in text.split("\n")]
    nonempty = [len(l) for l in lines if l]
    if not nonempty:
        return []
    width = sorted(nonempty)[int(len(nonempty) * 0.9)]
    out, cur = [], []
    end = re.compile(r"[.;:!?»\")]\s*$")
    listre = re.compile(r"^(?:[a-z]{1,3}\)|\d+[.)]\s|[-–•]\s)")

    def flush():
        if cur:
            t = re.sub(r"\s+", " ", " ".join(cur)).strip()
            out.append((t, False, esc(t)))
            cur.clear()
    prev = ""
    for ln in lines:
        if not ln:
            flush()
            prev = ""
            continue
        k = classify(ln, 160)
        if k:
            flush()
            out.append((ln, True, esc(ln)))
            prev = ""
            continue
        if cur and (end.search(prev) or len(prev) < width * 0.6 or listre.match(ln)):
            flush()
        cur.append(ln)
        prev = ln
    flush()
    return out


def render(units, title):
    present = []
    for t, is_title, _ in units:
        if t and is_title:
            k = classify(t)
            if k in dict(KEYS) and k not in present:
                present.append(k)
    order = [k for k, _ in KEYS if k in present]
    lvl = {k: min(6, 2 + i) for i, k in enumerate(order)}
    art_lvl = min(6, 2 + len(order))
    blocks = []
    skipped_title = False
    for t, is_title, block in units:
        if t is None:
            if block:
                blocks.append(block)
            continue
        if is_title:
            k = classify(t)
            if not skipped_title and not blocks and k is None:
                # leading document title (already in H1) - keep it as plain text only if it differs
                skipped_title = True
                if re.sub(r"\W+", "", t.lower()) == re.sub(r"\W+", "", title.lower()):
                    continue
                blocks.append(f"**{t}**")
                continue
            if k == "art":
                blocks.append("#" * art_lvl + " " + t)
            elif k in lvl:
                blocks.append("#" * lvl[k] + " " + t)
            elif k == "other":
                blocks.append("## " + t)
            else:
                blocks.append(f"**{t}**")
        else:
            blocks.append(block)
    return "\n\n".join(b for b in blocks if b)


def doc_type(tema, title):
    t = title.lower()
    if tema.startswith("Constitució"):
        return "constitution"
    if t.startswith("decret legislatiu") or tema == "Legislació delegada":
        return "legislative_decree"
    if "codi" in t[:60] and not t.startswith("llei"):
        return "code"
    if "qualificada" in t[:80]:
        return "qualified_act"
    if t.startswith("llei") or "llei" in t[:40]:
        return "act"
    return "other"


def identifier(title):
    m = re.match(r"^(Llei(?: qualificada)?|Decret legislatiu)\s+(\d+/\d{4})", title, re.I)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return None


def main():
    docs = json.load(open(os.path.join(RAW, "index.json")))
    for d in ("constitucio", "lleis", "legislacio-delegada"):
        if os.path.isdir(os.path.join(REPO, d)):
            shutil.rmtree(os.path.join(REPO, d))
    seen, used = set(), set()
    stats, missing = Counter(), []
    for d in sorted(docs, key=lambda x: (x["dataPublicacioButlleti"], x["nomDocument"])):
        if d["nomDocument"] in seen:
            continue
        seen.add(d["nomDocument"])
        parts = d["metadata_storage_path"].split("/")
        f = os.path.join(RAW, "docs", parts[-3] + "_" + d["nomDocument"] + ".html")
        if not os.path.exists(f) or os.path.getsize(f) == 0:
            missing.append(d["nomDocument"])
            continue
        b = open(f, "rb").read()
        if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
            raw = b.decode("utf-16")
        else:
            try:
                raw = b.decode("utf-8")
            except UnicodeDecodeError:
                raw = b.decode("cp1252", "replace")
        sumari = clean_sumari(d.get("sumari"))
        modern = 'class="Titol' in raw or 'class="Body' in raw
        soup = BeautifulSoup(raw, "lxml")
        title = sumari
        if modern:
            t3 = soup.find("p", class_=re.compile(r"^Titol-[1-4]$"))
            if t3:
                title = re.sub(r"\s+", " ", t3.get_text(" ")).strip() or sumari
            units = units_modern(soup)
        else:
            units = units_old(raw)
        title = title.rstrip()
        body = render(units, title)
        if not body.strip():
            missing.append(d["nomDocument"])
            continue
        tema = d.get("tema") or ""
        typ = doc_type(tema, title)
        pub = local_date(d.get("dataPublicacioButlleti"))
        dart = local_date(d.get("dataArticle"))
        ident = identifier(title)
        meta = {"title": title}
        if ident:
            meta["identifier"] = ident
        meta["type"] = typ
        meta["jurisdiction"] = "ad"
        meta["language"] = "ca"
        if dart:
            meta["date"] = dart
        meta["published"] = pub
        meta["bopa"] = f"BOPA núm. {d.get('numButlleti')}, any {d.get('anyButlleti')}" + (" (extra)" if d.get("isExtra") == "True" else "")
        meta["status"] = "unknown"
        meta["consolidated"] = False
        meta["source"] = "https://www.bopa.ad/Documents/Detall?doc=" + d["nomDocument"]
        meta["document_url"] = d["metadata_storage_path"]
        meta["retrieved"] = RETRIEVED
        fm = ["---"]
        for k, v in meta.items():
            if isinstance(v, bool):
                fm.append(f"{k}: {'true' if v else 'false'}")
            elif k in ("type", "jurisdiction", "language", "status", "date", "published", "retrieved"):
                fm.append(f"{k}: {v}")
            else:
                fm.append(f"{k}: " + json.dumps(v, ensure_ascii=False))
        fm.append("---")
        text = "\n".join(fm) + f"\n\n# {title}\n\n{body}\n"
        if typ == "constitution":
            rp = "constitucio/constitucio.md"
        else:
            top = "legislacio-delegada" if tema == "Legislació delegada" else "lleis"
            year = (pub or "0000")[:4]
            name = slugify(ident) if ident else slugify(re.sub(r",.*", "", title), 70)
            name = f"{pub}-{name}"
            base, k = name, 2
            while f"{top}/{year}/{name}" in used:
                name = f"{base}-{k}"
                k += 1
            used.add(f"{top}/{year}/{name}")
            rp = f"{top}/{year}/{name}.md"
        fp = os.path.join(REPO, rp)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, "w", encoding="utf-8").write(text)
        stats[rp.split("/")[0]] += 1
        stats["type:" + typ] += 1
    print(dict(stats), file=sys.stderr)
    print("missing", len(missing), missing[:20], file=sys.stderr)


if __name__ == "__main__":
    main()
