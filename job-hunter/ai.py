"""Tiny Groq helper. Returns parsed JSON or None. Never raises."""
import json, os, re, requests

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

def ask_json(system, user, max_tokens=1800):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"}, timeout=60,
            json={"model": MODEL, "temperature": 0.3, "max_tokens": max_tokens,
                  "response_format": {"type": "json_object"},
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0)) if m else None
    except Exception as e:
        print("AI error:", e)
        return None
