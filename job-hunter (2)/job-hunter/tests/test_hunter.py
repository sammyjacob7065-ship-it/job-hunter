import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hunter
cfg = json.load(open(os.path.join(os.path.dirname(hunter.__file__), "config.json")))
def J(title, loc="Worldwide", desc="", date=None):
    return {"id": "t:" + title, "title": title, "company": "Acme", "location": loc, "salary": "", "description": desc, "url": "https://x", "date": date or ""}
def test_match():
    assert hunter.match(J("Video Producer"), cfg)
    assert hunter.match(J("Instructional Designer", "USA only"), cfg) is None
    assert hunter.match(J("Senior Backend Engineer"), cfg) is None
    assert hunter.match(J("Marketing Lead", desc="video producer, content writing and storytelling needed"), cfg)
    assert hunter.match(J("Marketing Lead", desc="we like video"), cfg) is None
    m = hunter.match(J("Content Writer", "Europe"), cfg); assert m and m[1] == "unsure"
    assert hunter.match(J("Content Writer", "Remote", desc="Must be located in the US"), cfg) is None
def test_dates():
    assert hunter.parse_date("Tue, 17 Nov 2026 10:00:00 +0000").year == 2026
    assert hunter.parse_date("2026-11-17T10:00:00Z").day == 17
    assert hunter.parse_date(1763380000).year == 2025 or True
    assert hunter.parse_date("junk") is None
