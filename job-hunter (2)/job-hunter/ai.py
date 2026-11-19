"""Tiny Groq helper. Returns parsed JSON or None. Never raises.
Tries several models in order, so a retired model name (404) does not kill the CV."""
import json, os, re, requests

MODELS = [m for m in [os.environ.get("GROQ_MODEL"), "openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"] if m]

def ask_json(system, user, max_tokens=1800):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print("AI: GROQ_API_KEY is empty")
        return None
    for model in MODELS:
        body = {"model": model, "temperature": 0.3, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if "gpt-oss" in model:              # reasoning models: thinking tokens count, so leave room
            body["max_tokens"] = max_tokens + 3000
            body["reasoning_effort"] = "low"
        else:
            body["max_tokens"] = max_tokens
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {key}"}, timeout=90, json=body)
            if r.status_code in (400, 404):
                print(f"AI: model {model} gave {r.status_code}: {r.text[:160]} -> trying next")
                continue
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"] or ""
            m = re.search(r"\{.*\}", txt, re.S)
            if m:
                print("AI: used", model)
                return json.loads(m.group(0))
            print(f"AI: {model} returned no JSON -> trying next")
        except Exception as e:
            print(f"AI error with {model}:", e)
    return None
