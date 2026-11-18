import json, os, sys, shutil, tempfile, importlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def test_send(monkeypatch, tmp_path, capsys):
    sys.path.insert(0, ROOT); import send_mail
    importlib.reload(send_mail)
    monkeypatch.setattr(send_mail, "HERE", str(tmp_path))
    dd = tmp_path / "state" / "drafts"; dd.mkdir(parents=True)
    (dd / "abc1.pdf").write_bytes(b"%PDF-1.4 x")
    (dd / "abc1.json").write_text(json.dumps({"to": "hr@gmail.com", "subject": "S", "body": "Hello", "pdf": "state/drafts/abc1.pdf", "title": "T", "company": "C"}))
    box = []
    class FakeSMTP:
        def __init__(s, *a, **k): pass
        def __enter__(s): return s
        def __exit__(s, *a): pass
        def login(s, u, p): box.append(("login", u))
        def send_message(s, m): box.append(("msg", m["To"], len(list(m.iter_attachments()))))
    monkeypatch.setattr(send_mail.smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setenv("GMAIL_USER", "me@gmail.com"); monkeypatch.setenv("GMAIL_APP_PASSWORD", "x")
    monkeypatch.setattr(sys, "argv", ["x", "--job-id", "abc1"])
    send_mail.main(); send_mail.main()   # second call must NOT send again
    assert [b for b in box if b[0] == "msg"] == [("msg", "hr@gmail.com", 1)]
