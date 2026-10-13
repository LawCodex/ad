#!/usr/bin/env python3
"""Fetch Andorran laws (Constitució, Lleis, Legislació delegada) from the BOPA.

The list comes from the BOPA web site's public API (the same calls its "Legislació"
page makes); each document is then downloaded from the BOPA document store
(bopadocuments.blob.core.windows.net) as HTML (or PDF for documents without HTML).
Everything is cached under _raw/ad/.
"""
import json
import os
import re
import sys
import time

import requests

UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
API = "https://bopaazurefunctions.azurewebsites.net/api/"
# The API function keys are public (embedded in the site's JavaScript bundle); they are read
# from https://www.bopa.ad/static/js/main.*.js at run time rather than hard-coded here.
SITE = "https://www.bopa.ad/"
RAW = os.path.abspath(os.environ.get("AD_RAW", os.path.join(os.path.dirname(__file__), "..", "..", "_raw", "ad")))
S = requests.Session()
S.headers["User-Agent"] = UA


def get(url, tries=5):
    for i in range(tries):
        try:
            r = S.get(url, timeout=120)
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
            print("HTTP", r.status_code, url, file=sys.stderr)
        except requests.RequestException as e:
            print("ERR", e, url, file=sys.stderr)
        time.sleep(5 * (i + 1))
    return None


def api_keys():
    home = S.get(SITE, timeout=60).text
    js = re.search(r'src="(/static/js/main\.[0-9a-f]+\.js)"', home).group(1)
    code = S.get(SITE.rstrip("/") + js, timeout=120).text
    k_filters = re.search(r'GetFiltersLaws\?code=([A-Za-z0-9_\-=]+)', code).group(1)
    k_docs = re.search(r'GetPaginatedDocuments2Indexes\?code=([A-Za-z0-9_\-=]+)', code).group(1)
    return k_filters, k_docs


def list_docs():
    k_filters, k_docs = api_keys()
    f = S.get(API + "GetFiltersLaws?code=" + k_filters, timeout=60).json()
    temes = [t for g in f["temes"] for t in g["temes"]]
    print("temes", [t["name"] for t in temes], file=sys.stderr)
    out, skip = [], 0
    while True:
        body = {"textSearch": "", "temaFilter": [{"filterType": "eq", "filterValue": t["guid"]} for t in temes],
                "dateFilter": [], "size": 100, "skip": skip,
                "orderBy": "DataPublicacioButlleti asc, DataArticle asc,OrganismeOrder,OrganismeChildOrder",
                "searchMode": 1}
        r = S.post(API + "GetPaginatedDocuments2Indexes?code=" + k_docs, json=body, timeout=120)
        r.raise_for_status()
        d = r.json()
        docs = [x["document"] for x in d["paginatedDocuments"]]
        out += docs
        skip += 100
        print("listed", len(out), d["totalCount"], file=sys.stderr)
        if not docs or skip >= d["totalCount"]:
            return out
        time.sleep(1)


def cache_name(d):
    # <bulletin folder>_<document name>.html
    parts = d["metadata_storage_path"].split("/")
    return parts[-3] + "_" + d["nomDocument"] + ".html"


def main():
    os.makedirs(os.path.join(RAW, "docs"), exist_ok=True)
    idx = os.path.join(RAW, "index.json")
    if not os.path.exists(idx):
        json.dump(list_docs(), open(idx, "w"), ensure_ascii=False, indent=0)
    docs = json.load(open(idx))
    seen = set()
    for n, d in enumerate(docs):
        if d["nomDocument"] in seen:
            continue
        seen.add(d["nomDocument"])
        f = os.path.join(RAW, "docs", cache_name(d))
        if os.path.exists(f):
            continue
        url = d["metadata_storage_path"]
        base, name = url.rsplit("/", 1)
        m = re.match(r"^\d+_(.+)$", name)
        if m:
            # split document (1_X.html, 2_X.html...): the unsplit X.html holds the whole text
            c = get(base + "/" + m.group(1))
            if c is None:
                parts, k = [], 1
                while True:
                    p = get(f"{base}/{k}_{m.group(1)}")
                    if p is None:
                        break
                    parts.append(p)
                    k += 1
                    time.sleep(0.3)
                c = b"\n<!-- LAWCODEX-PART -->\n".join(parts) if parts else None
        else:
            c = get(url)
        if c is None:
            print("MISSING", url, file=sys.stderr)
            continue
        open(f, "wb").write(c)
        time.sleep(0.3)
        if n % 100 == 0:
            print("fetched", n, file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
