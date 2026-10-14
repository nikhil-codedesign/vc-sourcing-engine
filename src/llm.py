"""Shared helper for every step that needs an AI model (filter, extract, score).

Uses Google's Gemini API free tier (key from Google AI Studio, no card needed).
All other scripts call ask_json() only, so the model or provider can be swapped
here in one place without touching the rest of the pipeline.
"""
import json
import os
import time

import requests

API_KEY = os.environ.get("GEMINI_API_KEY", "")
# Override without editing code: set a repo variable/secret named LLM_MODEL.
# Check the current free models at https://ai.google.dev/gemini-api/docs/pricing
MODEL = os.environ.get("LLM_MODEL", "gemini-3.1-flash-lite")
MIN_SECONDS_BETWEEN_CALLS = float(os.environ.get("LLM_MIN_SECONDS", "6.5"))  # ~9 calls/min
MAX_RETRIES = 6

_last_call = 0.0


class QuotaExhausted(RuntimeError):
    """Daily free quota is used up. Re-run the workflow tomorrow; progress is kept."""


def ask_json(prompt, system=None):
    """Send a prompt, return the model's answer parsed as JSON (dict or list)."""
    global _last_call
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it under repo Settings > Secrets > Actions.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    for attempt in range(1, MAX_RETRIES + 1):
        wait = MIN_SECONDS_BETWEEN_CALLS - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()

        resp = requests.post(url, json=body, headers={"x-goog-api-key": API_KEY}, timeout=90)

        if resp.status_code == 200:
            try:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"  ! unreadable answer (attempt {attempt}): {e}")
                continue

        if resp.status_code == 429:
            detail = resp.text.lower()
            if "perday" in detail.replace(" ", "").replace("_", "") or "daily" in detail:
                raise QuotaExhausted("Daily free limit reached. Run again tomorrow.")
            time.sleep(min(60, 10 * attempt))
            continue

        if resp.status_code in (500, 502, 503, 504):
            time.sleep(min(60, 5 * attempt))
            continue

        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:300]}")

    raise RuntimeError("Gave up after repeated failures.")
