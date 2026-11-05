"""Builds index.html with 5 world politics stories from free RSS feeds."""
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = [
    ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("The Guardian", "https://www.theguardian.com/world/rss"),
    ("NPR", "https://feeds.npr.org/1004/rss.xml"),
    ("DW", "https://rss.dw.com/rdf/rss-en-world"),
]

# Stories mentioning these words are preferred (keeps the page political).
KEYWORDS = [
    "election", "vote", "president", "prime minister", "minister", "parliament",
    "government", "congress", "senate", "leader", "talks", "ceasefire", "war",
    "sanction", "treaty", "summit", "coalition", "diplomat", "military",
    "protest", "law", "court", "trump", "putin", "nato", "un ", "eu ",
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (daily-news-page)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def clean(text, limit=220):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text


def score(title, desc):
    blob = (title + " " + desc).lower()
    return sum(1 for k in KEYWORDS if k in blob)


def load(name, url):
    try:
        root = ET.fromstring(fetch(url))
    except Exception as e:  # one broken feed should not break the page
        print(f"Skipping {name}: {e}", file=sys.stderr)
        return []
    items = []
    for it in root.iter():
        if it.tag.split("}")[-1] != "item":
            continue
        get = lambda t: next((c.text for c in it if c.tag.split("}")[-1] == t and c.text), "")
        title, link, desc = clean(get("title"), 160), (get("link") or "").strip(), clean(get("description"))
        if title and link.startswith("http"):
            items.append({"source": name, "title": title, "link": link, "desc": desc,
                          "score": score(title, desc)})
    preferred = [i for i in items if i["score"] > 0]
    return preferred or items


def pick(pools, n=5):
    chosen, seen = [], []
    while len(chosen) < n and any(pools):
        for pool in pools:
            while pool:
                item = pool.pop(0)
                words = set(re.findall(r"[a-z]{4,}", item["title"].lower()))
                if any(len(words & s) >= 3 for s in seen):
                    continue  # skip near-duplicate headlines
                seen.append(words)
                chosen.append(item)
                break
            if len(chosen) == n:
                break
    return chosen


CSS = """:root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);--bg:#faf8f4;--card:#fff;--text:#1b1b1f;--muted:#6b6b73;--accent:#b3261e;--line:#e6e2d9;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#121214;--card:#1c1c20;--text:#ececf0;--muted:#9a9aa5;--accent:#ff6b5e;--line:#2c2c33;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 Georgia,"Times New Roman",serif}
main{max-width:640px;margin:0 auto;padding:28px 18px 40px}
header{border-bottom:3px double var(--line);padding-bottom:14px;margin-bottom:22px}
.kicker{font:600 12px/1 system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
h1{font-size:30px;line-height:1.15;margin:8px 0 6px}
.date{font:14px system-ui,sans-serif;color:var(--muted)}
article{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 16px 14px;margin:0 0 14px}
.num{font:700 13px system-ui,sans-serif;color:var(--accent)}
h2{font-size:19px;line-height:1.25;margin:4px 0 8px}
h2 a{color:inherit;text-decoration:none}
p{margin:0 0 8px}
.src{font:13px system-ui,sans-serif;color:var(--muted)}
footer{font:13px system-ui,sans-serif;color:var(--muted);text-align:center;margin-top:24px}"""


def render(items):
    now = datetime.now(timezone.utc)
    date = now.strftime("%A, %d %B %Y")
    cards = ""
    for i, it in enumerate(items, 1):
        e = html.escape
        cards += (
            f'<article><div class="num">{i:02d}</div>'
            f'<h2><a href="{e(it["link"])}" target="_blank" rel="noopener">{e(it["title"])}</a></h2>'
            f'<p>{e(it["desc"])}</p><div class="src">{e(it["source"])}</div></article>\n'
        )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>World Politics: 5 Things Today</title>
<style>{CSS}</style></head>
<body><main>
<header><div class="kicker">World Politics · Daily Brief</div>
<h1>5 Things to Know Today</h1><div class="date">{date} (UTC)</div></header>
{cards}<footer>Updated automatically from public news feeds. Tap a headline to read the full story.</footer>
</main></body></html>
"""


if __name__ == "__main__":
    pools = [load(n, u) for n, u in FEEDS]
    items = pick(pools)
    if not items:
        sys.exit("No stories fetched; keeping the old page.")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(render(items))
    print(f"Wrote {len(items)} stories.")
