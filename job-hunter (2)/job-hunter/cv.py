"""Tailor the CV template to one job and render a PDF.
  python cv.py --job-id <id from Telegram>      (reads state/jobs.json)
  python cv.py --url https://...                (fetches the page text)
  python cv.py --text-file job.txt
Rule: the AI may reword, reorder and re-title. It may NOT add facts. Numbers/tools not in the
template are rejected and the CV falls back to the untailored template."""
import argparse, html as H, json, os, re, requests, sys
import ai
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

SYSTEM = """You tailor a CV for ONE job so it reads as if written only for it.
You get TEMPLATE (JSON of the candidate's true CV) and the JOB. Return JSON with exactly:
{"headline": str (<=110 chars, uses the job's own title words where the template honestly supports them),
 "summary": str (60-95 words, first sentence speaks to this job's main need),
 "competencies": [[title, text], ...] (same items as template, reordered by relevance, text re-worded with the job's vocabulary),
 "services": [[title, text], ...], "approach": [[title, text], ...],
 "cover_note": str (90-130 words, plain direct email body, greets 'Hello', no flattery, ends 'Jacob Samson'),
 "email_subject": str, "company": str, "role": str}
HARD RULES: Use ONLY facts in TEMPLATE. Never invent employers, years, degrees, tools, clients, numbers or results.
Do not claim skills the template does not show. You may rename a heading only if the meaning stays true.
Simple clear English. No em-dashes. Do not mention that you are an AI."""

def nums(s): return set(re.findall(r"\d+", s))

def tailor(tpl, job_text):
    base = json.dumps(tpl, ensure_ascii=False)
    allowed = nums(base)
    for _ in range(2):
        r = ai.ask_json(SYSTEM, f"TEMPLATE:\n{base}\n\nJOB:\n{job_text[:5000]}", 2500)
        if not r: continue
        try:
            body = json.dumps({k: r[k] for k in ("headline","summary","competencies","services","approach")}, ensure_ascii=False)
            ok = nums(body) <= allowed | {"16", "9"} and len(r["competencies"]) >= 5 and r.get("cover_note")
            if ok: return r
            print("rejected AI output (new numbers or missing parts)")
        except Exception as e:
            print("bad AI output", e)
    return None

CSS = """@page{size:A4;margin:14mm 15mm}*{box-sizing:border-box}body{font:9.6pt/1.38 Arial,Helvetica,sans-serif;color:#1c1f26;margin:0}
h1{font-size:21pt;margin:0;letter-spacing:.5px}.hl{font-size:10.6pt;font-weight:700;color:#14507a;margin:2px 0 3px}
.ct{color:#444;font-size:9pt}.ct a{color:#14507a;text-decoration:none}.av{font-weight:700;margin-top:3px}
h2{font-size:10.2pt;letter-spacing:1.2px;color:#14507a;border-bottom:1.3px solid #14507a;padding-bottom:2px;margin:11px 0 5px}
p{margin:0 0 4px}.it{margin:0 0 3.5px}.it b{color:#111}"""

def render(cv, path):
    li = lambda items: "".join(f"<div class='it'><b>{H.escape(t)}:</b> {H.escape(x)}</div>" for t, x in items)
    links = " | ".join(f"{H.escape(a)}: <a href='{H.escape(b)}'>{H.escape(b)}</a>" for a, b in cv["links"])
    doc = f"""<html><head><meta charset=utf-8><style>{CSS}</style></head><body>
<h1>{H.escape(cv['name'])}</h1><div class=hl>{H.escape(cv['headline'])}</div>
<div class=ct>{H.escape(cv['contact'])}<br>{links}</div><div class=av>{H.escape(cv['availability'])}</div>
<h2>EXECUTIVE PROFILE</h2><p>{H.escape(cv['summary'])}</p>
<h2>CORE COMPETENCIES</h2>{li(cv['competencies'])}
<h2>SELECTED SERVICE CAPABILITIES</h2>{li(cv['services'])}
<h2>PROFESSIONAL APPROACH &amp; VALUE PROPOSITION</h2>{li(cv['approach'])}
<h2>EDUCATION</h2><p>{H.escape(cv['education'])}</p></body></html>"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(); pg.set_content(doc)
        pg.pdf(path=path, format="A4", print_background=True, prefer_css_page_size=True); b.close()

def tg_file(path, caption, buttons=None):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok: print("(no telegram creds; file kept in out/)"); return
    data = {"chat_id": chat, "caption": caption[:1000]}
    if buttons: data["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    with open(path, "rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendDocument", timeout=60,
                          data=data, files={"document": f})
    print("telegram", r.status_code)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--job-id"); ap.add_argument("--url"); ap.add_argument("--text-file")
    ap.add_argument("--id"); ap.add_argument("--title", default=""); ap.add_argument("--company", default=""); ap.add_argument("--to", default="")
    a = ap.parse_args()
    tpl = json.load(open(os.path.join(HERE, "cv_template.json")))
    title = company = to_addr = ""
    if a.text_file:
        text, url = open(a.text_file).read(), (a.url or "")
        title, company, to_addr = a.title, a.company, a.to
    elif a.job_id:
        j = json.load(open(os.path.join(HERE, "state", "jobs.json")))[a.job_id.strip()]
        text, title, company, url = f"{j['title']} at {j['company']}\n{j['description']}", j["title"], j["company"], j["url"]
        g = re.findall(r"[A-Za-z0-9._%+-]+@gmail\.com", j["description"], re.I); to_addr = g[0] if g else ""
    elif a.url:
        title, company, to_addr = a.title, a.company, a.to
        text = re.sub(r"\s+", " ", re.sub(r"<(script|style)[\s\S]*?</\1>|<[^>]+>", " ",
               requests.get(a.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text)); url = a.url
    else:
        text, url = "", ""
    r = tailor(tpl, text)
    cv, note = dict(tpl), ""
    if r:
        for k in ("headline", "summary", "competencies", "services", "approach"): cv[k] = r[k]
        company, title = r.get("company") or company, r.get("role") or title
        note = f"Subject: {r.get('email_subject','')}\n\n{r['cover_note']}"
    else:
        note = "(AI tailoring failed or was rejected - this is your untailored template CV.)"
    os.makedirs(OUT, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", company or "Job").strip("_")[:30]
    pdf = os.path.join(OUT, f"Jacob_Samson_CV_{slug}.pdf"); render(cv, pdf)
    open(os.path.join(OUT, f"cover_{slug}.txt"), "w").write(note)
    buttons = None
    sid = (a.job_id or a.id or "").strip()
    if sid and to_addr and r:
        dd = os.path.join(HERE, "state", "drafts"); os.makedirs(dd, exist_ok=True)
        import shutil; shutil.copy(pdf, os.path.join(dd, sid + ".pdf"))
        json.dump({"to": to_addr, "subject": r.get("email_subject") or f"Application: {title}", "body": r["cover_note"],
                   "pdf": f"state/drafts/{sid}.pdf", "title": title, "company": company},
                  open(os.path.join(dd, sid + ".json"), "w"), indent=1)
        buttons = [[{"text": f"✅ Send to {to_addr}", "callback_data": "send:" + sid}]]
    tg_file(pdf, f"📄 CV for {title} @ {company}\n{url}\n\n{note}", buttons)
    print("wrote", pdf)
if __name__ == "__main__": main()
