"""End-to-end check through the Django endpoints with a real PDF. Usage: LLM_PROVIDER=gemini python e2e_check.py"""
import json
import os
import sys

import django

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
django.setup()
from django.test import Client
from django.test.utils import setup_test_environment

setup_test_environment()
c = Client()

with open("samples/handbook.pdf", "rb") as f:
    r = c.post("/api/upload", {"files": f})
print("upload:", r.status_code, r.json())

questions = [
    ("How many days of annual leave do employees get?", "24"),
    ("How much is reimbursed for home internet?", "50"),
    ("What is the CEO's salary?", "don't know"),
]
failed = 0
for q, expect in questions:
    r = c.post("/api/ask", data=json.dumps({"question": q}), content_type="application/json")
    lines = [json.loads(b) for b in b"".join(r.streaming_content).decode().splitlines() if b]
    sources = lines[0]["sources"]
    text = "".join(l.get("token", "") for l in lines[1:])
    ok = expect.lower() in text.lower()
    failed += not ok
    print(f"\nQ: {q}\nA: {text.strip()}\n   top source: p.{sources[0]['page']} (sim {sources[0]['score']})  -> {'PASS' if ok else 'FAIL'}")
sys.exit(1 if failed else 0)
