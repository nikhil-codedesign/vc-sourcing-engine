# Free version: what changes in the guide

Only ONE thing in the original plan costs money: the Claude API (Day 0 steps 2-5, used on Days 5, 6, 7, 9, 10).
Everything else (GitHub, Actions on a public repo, Streamlit Cloud, archive.org, Crunchbase free view) is already free.

## Day 0: replace steps 2-5 with this (about 10 minutes, no card)

1. Go to aistudio.google.com and sign in with a Google account.
2. Click **Get API key** -> **Create API key**. Copy it.
3. In your repo: **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**.
   Name: `GEMINI_API_KEY`. Paste the key. **Add secret**.
4. Keep step 6 (Read and write permissions) and step 7 (Streamlit account) as they are.

Never paste the key into chat or into a file.

## Every later workflow

Wherever the guide says `ANTHROPIC_API_KEY`, the workflow uses `GEMINI_API_KEY` instead:

    env:
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

All AI calls go through `src/llm.py`, so the filter, extract and score scripts and their outputs
(`filter_report.csv`, `facts.csv`, `scores.csv`, etc.) stay exactly as the guide describes.

## Add this file on Day 3

`src/llm.py` (attached). It is only used from Day 5 onward, so adding it early is harmless.

## What is different in practice

- **Slower.** Free tiers limit calls per minute and per day. The script waits between calls (about 9 per minute).
  Filtering ~100 signals takes roughly 15 minutes of run time instead of 2. That's fine for a robot.
- **Daily cap.** If the daily free quota runs out, the run stops cleanly. Click Run again the next day and it continues.
  Limits change, so check yours at aistudio.google.com/rate-limit.
- **Privacy.** On the free tier, Google may use what you send to improve its products. This project only sends
  public GitHub/HN text, so that is fine. Never send anything private through it.
- **Quality.** Gemini's lighter free models are a bit different from Claude. Day 5's hand-labelling and agreement
  rate is the safeguard: it measures how well this exact model matches YOUR judgment. Report whatever number you get.
- **Model name.** Defaults to `gemini-3.1-flash-lite`. If a run says the model isn't found, add a repo variable
  `LLM_MODEL` with another free model from ai.google.dev/gemini-api/docs/pricing. No code change needed.
