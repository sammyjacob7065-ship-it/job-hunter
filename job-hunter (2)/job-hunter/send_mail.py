"""Send a saved draft (state/drafts/<id>.json + pdf) from your Gmail. Max 10 per day.
Needs secrets GMAIL_USER and GMAIL_APP_PASSWORD (Google account > Security > App passwords)."""
import argparse, datetime as dt, json, os, re, smtplib, ssl, sys, requests
from email.message import EmailMessage
HERE = os.path.dirname(os.path.abspath(__file__))
DAILY_CAP = 10

def tg(text):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if tok: requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": chat, "text": text}, timeout=30)
    print(text)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--job-id", required=True); a = ap.parse_args()
    sid = re.sub(r"[^a-z0-9]", "", a.job_id.lower())
    base = os.path.join(HERE, "state", "drafts", sid)
    if not os.path.exists(base + ".json"): tg("❌ No draft found for " + sid + ". Tap Make CV first."); sys.exit(1)
    d = json.load(open(base + ".json"))
    sp = os.path.join(HERE, "state", "sent.json")
    sent = json.load(open(sp)) if os.path.exists(sp) else {}
    today = dt.date.today().isoformat()
    if sid in sent: tg(f"ℹ️ Already sent to {sent[sid]['to']} on {sent[sid]['day']}. Not sending again."); return
    if sum(1 for v in sent.values() if v["day"] == today) >= DAILY_CAP: tg(f"⛔ Daily limit of {DAILY_CAP} emails reached. Try tomorrow."); return
    m = EmailMessage(); m["From"] = os.environ["GMAIL_USER"]; m["To"] = d["to"]; m["Subject"] = d["subject"]
    m.set_content(d["body"])
    m.add_attachment(open(os.path.join(HERE, d["pdf"]), "rb").read(), maintype="application", subtype="pdf", filename="Jacob_Samson_CV.pdf")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"]); s.send_message(m)
    sent[sid] = {"to": d["to"], "day": today, "company": d["company"]}
    json.dump(sent, open(sp, "w"), indent=1)
    tg(f"✅ Sent to {d['to']} ({d['title']} @ {d['company']}) with your CV attached.")
if __name__ == "__main__": main()
