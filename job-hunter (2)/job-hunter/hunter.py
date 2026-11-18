"""Job hunter: fetch -> filter to the niche -> Telegram. Run by GitHub Actions ~20x/day."""
import datetime as dt, email.utils, json, os, re, sys, requests
import ai
from sources import SOURCES

DRY = os.environ.get("DRY_RUN") == "1"
HERE = os.path.dirname(os.path.abspath(__file__))
SEEN, JOBS = os.path.join(HERE, "state", "seen.json"), os.path.join(HERE, "state", "jobs.json")
GMAIL = re.compile(r"[A-Za-z0-9._%+-]+@gmail\.com", re.I)
ANYMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", re.I)

def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def save(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True); json.dump(o, open(p, "w"), indent=1)

def parse_date(raw):
    if not raw: return None
    try:
        if isinstance(raw, (int, float)): return dt.datetime.fromtimestamp(raw, dt.timezone.utc)
        s = str(raw).strip()
        if s.isdigit(): return dt.datetime.fromtimestamp(int(s), dt.timezone.utc)
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            d = email.utils.parsedate_to_datetime(s)
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None

def has(text, w):
    return re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text) is not None

def match(j, cfg):
    """Return (hits, region) or None. region: ok | unsure."""
    title, desc = j["title"].lower(), j["description"].lower()
    if any(has(title, a) for a in cfg["avoid"]): return None
    t_hits = [w for w in cfg["titles"] if has(title, w)]
    d_hits = [w for w in cfg["titles"] if has(desc, w)]
    if not t_hits and len(set(d_hits)) < 3: return None
    hits = t_hits or sorted(set(d_hits))[:4]
    loc = (j["location"] + " " + title + " " + desc[:600]).lower()
    world = any(has(loc, w) for w in ["worldwide", "anywhere", "global", "africa", "nigeria", "any location"])
    restricted = any(r in loc for r in cfg["restricted_regions"])
    if restricted and not world: return None
    region = "ok" if (world or not j["location"]) else "unsure"
    return hits, region

def why_not(j, cfg):
    title, desc = j["title"].lower(), j["description"].lower()
    if any(has(title, a) for a in cfg["avoid"]): return "avoid-word"
    t = [w for w in cfg["titles"] if has(title, w)]; d = {w for w in cfg["titles"] if has(desc, w)}
    if not t and len(d) < 3: return "not-niche"
    return "region-restricted"

def ai_fit(j, cfg):
    r = ai.ask_json(
        "You screen jobs for Jacob: instructional designer / e-learning developer / AI video storyteller / "
        "documentary or video producer-editor / content writer, based in Nigeria, wants fully remote work open to "
        "Nigeria or worldwide. Reply JSON: {\"fit\":0-10,\"nigeria_ok\":true|false|null,\"why\":\"max 12 words\"}",
        f"Title: {j['title']}\nCompany: {j['company']}\nLocation: {j['location']}\n{j['description'][:2500]}", 200)
    return r

def tg(text, buttons=None):
    if DRY: print("---TG---\n" + text + ("\n[buttons] " + json.dumps(buttons) if buttons else "")); return
    tok, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    body = {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if buttons: body["reply_markup"] = {"inline_keyboard": buttons}
    r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", timeout=30, json=body)
    if not r.ok: print("telegram error", r.text[:200])

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def short_id(i): return re.sub(r"[^a-z0-9]", "", i.lower())[-14:]

def fmt(j, hits, region, fit):
    gm = GMAIL.findall(j["description"]); other = [e for e in ANYMAIL.findall(j["description"]) if e not in gm]
    lines = [f"💼 <b>{esc(j['title'])}</b>" + (f" — {esc(j['company'])}" if j["company"] else ""),
             f"📍 {esc(j['location'] or 'Remote')}" + ("  ⚠️ check region" if region == "unsure" else "  ✅ open")
             + (f"   💰 {esc(j['salary'])}" if j["salary"] else ""),
             "🏷 " + esc(", ".join(hits))]
    if fit: lines.append(f"🤖 fit {fit.get('fit')}/10 — {esc(str(fit.get('why', '')))}")
    if gm: lines.append("📧 public Gmail: " + esc(gm[0]))
    elif other: lines.append("✉️ contact: " + esc(other[0]))
    lines += [j["url"], f"🆔 <code>{short_id(j['id'])}</code>"]
    return "\n".join(lines)

def run():
    cfg = load(os.path.join(HERE, "config.json"), {})
    seen, store = load(SEEN, {}), load(JOBS, {})
    first = not seen
    now = dt.datetime.now(dt.timezone.utc); today = now.strftime("%Y-%m-%d")
    allj, status = [], {}
    for name in cfg["sources"] + (["browser"] if cfg.get("browser_sources") else []):
        try:
            got = SOURCES[name](cfg); allj += got; status[name] = len(got)
        except Exception as e:
            status[name] = f"FAILED {type(e).__name__}: {str(e)[:80]}"
    print("sources:", status)
    new = [j for j in allj if j["id"] not in seen]
    sent = 0
    stats = {"too-old": 0, "avoid-word": 0, "not-niche": 0, "region-restricted": 0, "ai-rejected": 0}
    dropped = []
    for j in new:
        seen[j["id"]] = today
        d = parse_date(j["date"])
        if d and (now - d).days > cfg["max_age_days"]:
            stats["too-old"] += 1
            if match(j, cfg): dropped.append("OLD but niche: " + j["title"] + " | " + str(j["date"])[:16])
            continue
        m = match(j, cfg)
        if not m:
            w = why_not(j, cfg); stats[w] += 1
            if w == "region-restricted": dropped.append(j["title"] + " | " + j["location"])
            continue
        if first and sent >= 5: continue       # first run: don't flood
        if sent >= cfg["max_messages_per_run"]: seen.pop(j["id"]); continue  # keep for next run
        hits, region = m
        fit = ai_fit(j, cfg)
        if fit and isinstance(fit.get("fit"), (int, float)):
            if fit["fit"] < cfg["min_ai_fit"] or fit.get("nigeria_ok") is False:
                stats["ai-rejected"] += 1; dropped.append("AI no: " + j["title"] + " | " + str(fit.get("why"))); continue
        tg(fmt(j, hits, region, fit), [[{"text": "📄 Make CV", "callback_data": "cv:" + short_id(j["id"])},
                                        {"text": "🔗 Open job", "url": j["url"]}]]); sent += 1
        store[short_id(j["id"])] = j
    # keep state small
    seen = {k: v for k, v in seen.items() if (now - dt.datetime.strptime(v, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)).days < 60}
    store = dict(list(store.items())[-300:])
    bad = {k: v for k, v in status.items() if isinstance(v, str)}
    last = load(os.path.join(HERE, "state", "status_day.json"), {})
    if bad and last.get("day") != today:
        tg("⚠️ Job hunter: some sources failed today\n" + "\n".join(f"• {k}: {v}" for k, v in bad.items()))
        save(os.path.join(HERE, "state", "status_day.json"), {"day": today})
    if not DRY or os.environ.get("SAVE_STATE"):
        save(SEEN, seen); save(JOBS, store)
    print(f"new={len(new)} sent={sent}")
    print("why dropped:", stats)
    for x in dropped[:12]: print("  dropped ->", x)

if __name__ == "__main__":
    run()
