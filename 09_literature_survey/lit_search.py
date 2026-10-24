"""Stage 1: candidate pool from Crossref + arXiv + PMC. No OpenAlex."""
import urllib.request, urllib.parse, json, time, re, xml.etree.ElementTree as ET

UA = {"User-Agent": "python-urllib"}


def get(url, tries=3, pause=2.0):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(pause * (k + 1))
    raise last


def strip_tags(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- Crossref
def crossref(query, rows=60):
    qs = urllib.parse.urlencode({
        "query": query, "rows": rows,
        "filter": "from-pub-date:2019-01-01,until-pub-date:2026-12-31",
        "select": "DOI,title,container-title,issued,abstract,URL,type,publisher",
    })
    d = json.loads(get("https://api.crossref.org/works?" + qs))
    out = []
    for it in d["message"]["items"]:
        yr = None
        try:
            yr = it["issued"]["date-parts"][0][0]
        except Exception:
            pass
        out.append({
            "source": "crossref", "doi": (it.get("DOI") or "").lower(),
            "title": strip_tags((it.get("title") or [""])[0]),
            "venue": strip_tags((it.get("container-title") or [""])[0]),
            "year": yr, "type": it.get("type"),
            "abstract": strip_tags(it.get("abstract", "")),
            "url": it.get("URL", ""), "query": query,
        })
    return out


# ------------------------------------------------------------------- arXiv
def arxiv(query, max_results=60):
    qs = urllib.parse.urlencode({"search_query": query, "max_results": max_results,
                                 "sortBy": "relevance"})
    raw = get("http://export.arxiv.org/api/query?" + qs)
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(raw)
    out = []
    for e in root.findall("a:entry", ns):
        aid = e.findtext("a:id", "", ns)
        doi = e.findtext("arxiv:doi", "", ns) or ""
        pub = e.findtext("a:published", "", ns)
        out.append({
            "source": "arxiv", "arxiv_id": aid.rsplit("/", 1)[-1],
            "doi": doi.lower(),
            "title": strip_tags(e.findtext("a:title", "", ns)),
            "venue": "arXiv preprint",
            "year": int(pub[:4]) if pub[:4].isdigit() else None,
            "type": "preprint",
            "abstract": strip_tags(e.findtext("a:summary", "", ns)),
            "url": aid, "query": query,
        })
    time.sleep(3)          # arXiv asks for >=3s between requests
    return out


# --------------------------------------------------------------------- PMC
def pmc(term, retmax=60):
    qs = urllib.parse.urlencode({"db": "pmc", "term": term, "retmax": retmax,
                                 "retmode": "json", "datetype": "pdat",
                                 "mindate": "2019", "maxdate": "2026"})
    ids = json.loads(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + qs))
    ids = ids.get("esearchresult", {}).get("idlist", [])
    time.sleep(0.4)
    out = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        qs2 = urllib.parse.urlencode({"db": "pmc", "id": ",".join(chunk), "retmode": "json"})
        s = json.loads(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + qs2))
        for pid in chunk:
            r = s.get("result", {}).get(pid)
            if not r:
                continue
            doi = ""
            for aid in r.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = (aid.get("value") or "").lower()
            yr = re.search(r"(20\d\d)", r.get("pubdate", "") or "")
            out.append({
                "source": "pmc", "pmcid": "PMC" + pid, "doi": doi,
                "title": strip_tags(r.get("title", "")),
                "venue": strip_tags(r.get("fulljournalname") or r.get("source", "")),
                "year": int(yr.group(1)) if yr else None,
                "type": "journal-article", "abstract": "",
                "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pid}/",
                "query": term,
            })
        time.sleep(0.4)
    return out
