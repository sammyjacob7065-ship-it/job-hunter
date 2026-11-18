"""Job sources. Each returns a list of dicts:
id,title,company,location,salary,description,url,date(raw),source.
Field names come from each site's public API/feed. They were NOT live-tested
(the build sandbox blocks job sites) - hunter.py reports any source that fails."""
import html, re, requests
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=30, **kw)
    r.raise_for_status()
    return r

def clean(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    return re.sub(r"\s+", " ", t).strip()

def job(src, id_, title, company, loc, desc, url, date="", salary=""):
    return {"id": f"{src}:{id_}", "title": clean(title), "company": clean(company),
            "location": clean(loc if isinstance(loc, str) else ", ".join(loc or [])),
            "salary": clean(str(salary or "")), "description": clean(desc)[:6000],
            "url": url, "date": date, "source": src}

def remoteok(cfg):
    out = []
    for j in get("https://remoteok.com/api").json()[1:]:
        sal = f"${j['salary_min']}-{j['salary_max']}" if j.get("salary_min") else ""
        out.append(job("remoteok", j.get("id"), j.get("position"), j.get("company"), j.get("location"),
                       j.get("description"), j.get("url") or j.get("apply_url"), j.get("date"), sal))
    return out

def remotive(cfg):
    out, seen = [], set()
    for q in cfg["remotive_queries"]:
        for j in get("https://remotive.com/api/remote-jobs", params={"search": q}).json().get("jobs", []):
            if j["id"] in seen: continue
            seen.add(j["id"])
            out.append(job("remotive", j["id"], j["title"], j["company_name"], j.get("candidate_required_location"),
                           j.get("description"), j["url"], j.get("publication_date"), j.get("salary")))
    return out

def weworkremotely(cfg):
    out = []
    root = ET.fromstring(get("https://weworkremotely.com/remote-jobs.rss").content)
    for it in root.iter("item"):
        t = (it.findtext("title") or "")
        company, _, title = t.partition(": ")
        out.append(job("wwr", it.findtext("guid") or it.findtext("link"), title or t, company,
                       it.findtext("region") or "", it.findtext("description"), it.findtext("link"),
                       it.findtext("pubDate")))
    return out

def jobicy(cfg):
    out = []
    for j in get("https://jobicy.com/api/v2/remote-jobs", params={"count": 100}).json().get("jobs", []):
        out.append(job("jobicy", j["id"], j["jobTitle"], j.get("companyName"), j.get("jobGeo"),
                       j.get("jobDescription") or j.get("jobExcerpt"), j["url"], j.get("pubDate")))
    return out

def workingnomads(cfg):
    out = []
    for j in get("https://www.workingnomads.com/api/exposed_jobs/").json():
        out.append(job("nomads", j.get("url"), j.get("title"), j.get("company_name"), j.get("location"),
                       j.get("description"), j.get("url"), j.get("pub_date")))
    return out

def himalayas(cfg):
    out = []
    for j in get("https://himalayas.app/jobs/api", params={"limit": 100}).json().get("jobs", []):
        out.append(job("himalayas", j.get("guid") or j.get("applicationLink"), j.get("title"), j.get("companyName"),
                       j.get("locationRestrictions") or "Worldwide", j.get("description") or j.get("excerpt"),
                       j.get("applicationLink") or j.get("guid"), j.get("pubDate")))
    return out

def browser_sources(cfg):
    """For sites that block plain requests. Config item: {"name","url","card","title","link"}
    (CSS selectors). Needs: pip install playwright && playwright install chromium."""
    out = []
    if not cfg.get("browser_sources"): return out
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(user_agent=UA["User-Agent"], locale="en-US")
        for s in cfg["browser_sources"]:
            pg = ctx.new_page()
            pg.goto(s["url"], wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(3000)
            for c in pg.query_selector_all(s["card"])[:60]:
                t = c.query_selector(s["title"]); l = c.query_selector(s["link"])
                if t and l:
                    href = l.get_attribute("href") or ""
                    if href.startswith("/"): href = s["url"].split("/", 3)[0] + "//" + s["url"].split("/")[2] + href
                    out.append(job(s["name"], href, t.inner_text(), "", "", c.inner_text(), href))
            pg.close()
        b.close()
    return out

SOURCES = {"remoteok": remoteok, "remotive": remotive, "weworkremotely": weworkremotely,
           "jobicy": jobicy, "workingnomads": workingnomads, "himalayas": himalayas,
           "browser": browser_sources}
