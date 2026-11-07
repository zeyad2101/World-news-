import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

TZ = timezone(timedelta(hours=3))
TZ_LABEL = "GMT+3"

FEEDS = [
    ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("The Guardian", "https://www.theguardian.com/world/rss"),
    ("NPR", "https://feeds.npr.org/1004/rss.xml"),
    ("DW", "https://rss.dw.com/rdf/rss-en-world"),
]

KEYWORDS = [
    "election", "vote", "president", "prime minister", "minister", "parliament",
    "government", "congress", "senate", "leader", "talks", "ceasefire", "war",
    "sanction", "treaty", "summit", "coalition", "diplomat", "military",
    "protest", "law", "court", "trump", "putin", "nato", "un ", "eu ",
]

SKIP = {"What", "Why", "How", "Who", "When", "Where", "With", "After", "Over",
        "From", "Amid", "Says", "Will", "Could", "Would", "This", "That", "Their",
        "They", "Here", "Live", "Watch", "More", "Into", "Before", "Against"}


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


def parse_time(text):
    if not text:
        return 0
    try:
        dt = parsedate_to_datetime(text)
    except Exception:
        try:
            dt = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
        except Exception:
            return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def load(name, url):
    try:
        root = ET.fromstring(fetch(url))
    except Exception as e:
        print(f"Skipping {name}: {e}", file=sys.stderr)
        return []
    items = []
    for it in root.iter():
        if it.tag.split("}")[-1] != "item":
            continue
        def get(*tags):
            for c in it:
                if c.tag.split("}")[-1] in tags and c.text:
                    return c.text
            return ""
        title = clean(get("title"), 160)
        link = (get("link") or "").strip()
        desc = clean(get("description"))
        ts = parse_time(get("pubDate", "date"))
        if title and link.startswith("http"):
            items.append({"source": name, "title": title, "link": link, "desc": desc,
                          "ts": ts, "score": score(title, desc)})
    return items


def pick(pools, n=5):
    chosen, seen = [], []
    while len(chosen) < n and any(pools):
        for pool in pools:
            while pool:
                item = pool.pop(0)
                words = set(re.findall(r"[a-z]{4,}", item["title"].lower()))
                if any(len(words & s) >= 3 for s in seen):
                    continue
                seen.append(words)
                chosen.append(item)
                break
            if len(chosen) == n:
                break
    return chosen


def topics(title):
    out = []
    for w in re.findall(r"\b[A-Z][a-zA-Z]{3,}\b", title):
        if w not in SKIP and w not in out:
            out.append(w)
    return out[:5]


CSS = """:root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);--bg:#faf8f4;--card:#fff;--text:#1b1b1f;--muted:#6b6b73;--accent:#b3261e;--line:#e6e2d9;--pin:#fff4d6;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#121214;--card:#1c1c20;--text:#ececf0;--muted:#9a9aa5;--accent:#ff6b5e;--line:#2c2c33;--pin:#2a2415;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 Georgia,"Times New Roman",serif}
main{max-width:640px;margin:0 auto;padding:28px 18px 40px}
header{border-bottom:3px double var(--line);padding-bottom:14px;margin-bottom:18px}
.kicker{font:600 12px/1 system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
h1{font-size:30px;line-height:1.15;margin:8px 0 6px}
.date{font:14px system-ui,sans-serif;color:var(--muted)}
.pinbar{display:flex;gap:8px;margin:0 0 16px}
.pinbar input{flex:1;min-width:0;font:16px system-ui,sans-serif;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--text)}
button{font:600 14px system-ui,sans-serif;padding:9px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--text);cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
article{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 16px 14px;margin:0 0 14px}
article.pinned{background:var(--pin);border-color:var(--accent)}
.num{font:700 13px system-ui,sans-serif;color:var(--accent)}
h2{font-size:19px;line-height:1.25;margin:4px 0 8px}
h2 a{color:inherit;text-decoration:none}
p{margin:0 0 8px}
.src{font:13px system-ui,sans-serif;color:var(--muted)}
.row{display:flex;justify-content:space-between;align-items:center;gap:8px}
.pinbtn{font-size:13px;padding:5px 9px}
.chips{display:none;flex-wrap:wrap;gap:6px;margin-top:10px}
.chips.open{display:flex}
.chips button{font-size:13px;padding:5px 10px;border-radius:99px}
.pinhead{display:flex;justify-content:space-between;align-items:center;margin:0 0 10px;font:700 15px system-ui,sans-serif;color:var(--accent)}
.empty{font:14px system-ui,sans-serif;color:var(--muted);margin:0 0 14px}
footer{font:13px system-ui,sans-serif;color:var(--muted);text-align:center;margin-top:24px}"""

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>World Politics: 5 Things Today</title>
<style>__CSS__</style></head>
<body><main>
<header><div class="kicker">World Politics · Daily Brief</div>
<h1>5 Things to Know Today</h1><div class="date">__DATE__</div></header>
<div class="pinbar"><input id="topic" placeholder="Pin a topic, e.g. Iran" autocomplete="off"><button class="primary" id="pinGo">📌 Pin</button></div>
<section id="pinned"></section>
__CARDS__
<footer>Updated automatically from public news feeds. Pins are saved on this device only.</footer>
</main>
<script>
var ALL = __DATA__;
var KEY = "pinnedTopic";
function getPin(){ try { return localStorage.getItem(KEY) || ""; } catch(e){ return window.__pin || ""; } }
function setPin(v){ try { if(v){ localStorage.setItem(KEY, v); } else { localStorage.removeItem(KEY); } } catch(e){ window.__pin = v; } }
function ago(ts){
  if(!ts) return "";
  var m = Math.max(0, Math.round((Date.now()/1000 - ts)/60));
  if(m < 60) return m + " min ago";
  var h = Math.round(m/60);
  if(h < 48) return h + " h ago";
  return Math.round(h/24) + " d ago";
}
function el(tag, cls, text){
  var e = document.createElement(tag);
  if(cls) e.className = cls;
  if(text) e.textContent = text;
  return e;
}
function renderPin(){
  var box = document.getElementById("pinned");
  box.textContent = "";
  var topic = getPin();
  if(!topic) return;
  var q = topic.toLowerCase();
  var hits = ALL.filter(function(i){ return (i.t + " " + i.d).toLowerCase().indexOf(q) !== -1; })
                .sort(function(a,b){ return b.ts - a.ts; }).slice(0, 6);
  var head = el("div", "pinhead");
  head.appendChild(el("span", "", "📌 Pinned: " + topic + " (latest first)"));
  var un = el("button", "pinbtn", "Unpin");
  un.onclick = function(){ setPin(""); document.getElementById("topic").value = ""; renderPin(); };
  head.appendChild(un);
  box.appendChild(head);
  if(!hits.length){
    box.appendChild(el("p", "empty", "No new stories on this topic right now. It will fill in at the next refresh."));
    return;
  }
  hits.forEach(function(i){
    var a = el("article", "pinned");
    var h = el("h2");
    var link = el("a", "", i.t);
    link.href = i.l; link.target = "_blank"; link.rel = "noopener";
    h.appendChild(link);
    a.appendChild(h);
    if(i.d) a.appendChild(el("p", "", i.d));
    a.appendChild(el("div", "src", i.s + (i.ts ? " · " + ago(i.ts) : "")));
    box.appendChild(a);
  });
}
function pin(v){
  v = (v || "").trim();
  if(!v) return;
  setPin(v);
  document.getElementById("topic").value = v;
  renderPin();
  window.scrollTo(0, 0);
}
document.getElementById("pinGo").onclick = function(){ pin(document.getElementById("topic").value); };
document.getElementById("topic").onkeydown = function(e){ if(e.key === "Enter") pin(this.value); };
Array.prototype.forEach.call(document.querySelectorAll(".pinbtn[data-toggle]"), function(b){
  b.onclick = function(){ document.getElementById(b.getAttribute("data-toggle")).classList.toggle("open"); };
});
Array.prototype.forEach.call(document.querySelectorAll(".chips button"), function(b){
  b.onclick = function(){ pin(b.getAttribute("data-topic")); };
});
document.getElementById("topic").value = getPin();
renderPin();
</script></body></html>
"""


def render(items, everything):
    now = datetime.now(TZ)
    date = now.strftime("%A, %d %B %Y · updated %H:%M") + f" ({TZ_LABEL})"
    e = html.escape
    cards = ""
    for i, it in enumerate(items, 1):
        chips = "".join(
            f'<button data-topic="{e(t)}">{e(t)}</button>' for t in topics(it["title"]))
        cards += (
            f'<article><div class="num">{i:02d}</div>'
            f'<h2><a href="{e(it["link"])}" target="_blank" rel="noopener">{e(it["title"])}</a></h2>'
            f'<p>{e(it["desc"])}</p>'
            f'<div class="row"><div class="src">{e(it["source"])}</div>'
            f'<button class="pinbtn" data-toggle="c{i}">📌 Pin a topic</button></div>'
            f'<div class="chips" id="c{i}">{chips}</div></article>\n'
        )
    data = json.dumps(
        [{"t": x["title"], "d": x["desc"], "l": x["link"], "s": x["source"], "ts": x["ts"]}
         for x in everything], ensure_ascii=False).replace("</", "<\\/")
    return (PAGE.replace("__CSS__", CSS).replace("__DATE__", e(date))
            .replace("__CARDS__", cards).replace("__DATA__", data))


if __name__ == "__main__":
    pools = [load(n, u) for n, u in FEEDS]
    everything, seen_links = [], set()
    for x in sorted((i for p in pools for i in p), key=lambda i: i["ts"], reverse=True):
        if x["link"] not in seen_links:
            seen_links.add(x["link"])
            everything.append(x)
    everything = everything[:80]
    pick_pools = [[i for i in p if i["score"] > 0] or list(p) for p in pools]
    items = pick(pick_pools)
    if not items:
        sys.exit("No stories fetched; keeping the old page.")
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(render(items, everything))
    print(f"Wrote {len(items)} stories, {len(everything)} searchable.")
