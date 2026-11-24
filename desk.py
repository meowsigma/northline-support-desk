#!/usr/bin/env python3
"""Ember & Wick support desk: agent-drafted replies with a human approval gate.

Pipeline per email:
  1. A fake customer email arrives (emails/ directory).
  2. A LOCAL open-weight model (llama.cpp llama-server, OpenAI-compatible API)
     drafts a reply in the shop's brand voice.
  3. A human reviews the draft: [a]pprove, [e]dit then approve, or [r]eject.
  4. Nothing counts as sent until a human approved it. "Send" is simulated
     (writes to sent/), and every decision lands in decisions.log.

No cloud APIs. The model runs on the same machine, see README.
"""
import json, os, sys, time, urllib.request, datetime, textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))
EMAILS_DIR = os.path.join(ROOT, "emails")
DRAFTS_DIR = os.path.join(ROOT, "drafts")
SENT_DIR = os.path.join(ROOT, "sent")
LOG = os.path.join(ROOT, "decisions.log")

MODEL_URL = os.environ.get("DESK_MODEL_URL", "http://127.0.0.1:18091/v1/chat/completions")
MODEL_NAME = os.environ.get("DESK_MODEL_NAME", "Qwen2.5-7B-Instruct-Q4_K_M (local llama.cpp)")

SYSTEM_PROMPT = textwrap.dedent("""\
    You are Sam, the support agent for Ember & Wick, a small online candle shop
    (hand-poured soy candles). Brand voice: warm, plain-spoken, human. Short
    paragraphs. Never invent order numbers, dates, or policies you were not told;
    if a detail is unknown, say a human on the team will confirm it. Sign as "Sam @ Ember & Wick".
    Write only the email reply body, no subject line, no markdown.
    """)


def draft_reply(email_text: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "temperature": 0.7,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Customer email:\n\n" + email_text},
        ],
    }
    req = urllib.request.Request(
        MODEL_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"].strip()


def log_decision(fname: str, action: str, draft: str, note: str = ""):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": ts, "email": fname, "action": action,
                            "model": MODEL_NAME, "note": note,
                            "chars": len(draft)}) + "\n")


def load_emails():
    names = sorted(n for n in os.listdir(EMAILS_DIR) if n.endswith(".txt"))
    return [(n, open(os.path.join(EMAILS_DIR, n)).read()) for n in names]


def interactive_review(fname, email, draft):
    print("\n" + "=" * 72)
    print(f"INCOMING  [{fname}]")
    print("-" * 72)
    print(email.strip())
    print("-" * 72)
    print("MODEL DRAFT")
    print("-" * 72)
    print(draft)
    print("-" * 72)
    while True:
        choice = input("[a]pprove & send  [e]dit then send  [r]eject  > ").strip().lower()
        if choice in ("a", "approve"):
            return "approved", draft
        if choice in ("e", "edit"):
            print("Type your edited reply, then a lone '.' on a new line:")
            lines = []
            while True:
                ln = input()
                if ln.strip() == ".":
                    break
                lines.append(ln)
            return "edited", "\n".join(lines).strip()
        if choice in ("r", "reject"):
            note = input("Why rejected (optional) > ")
            return "rejected", note


def simulate_send(fname, body):
    os.makedirs(SENT_DIR, exist_ok=True)
    path = os.path.join(SENT_DIR, fname.replace(".txt", ".sent.txt"))
    with open(path, "w") as f:
        f.write(body)
    return path


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "review"
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    emails = load_emails()
    if not emails:
        print("No emails in emails/ - nothing to do."); return
    for fname, email in emails:
        print(f"\n>>> drafting reply for {fname} ...")
        t0 = time.time()
        draft = draft_reply(email)
        print(f"    drafted in {time.time()-t0:.1f}s by {MODEL_NAME}")
        with open(os.path.join(DRAFTS_DIR, fname), "w") as f:
            f.write(draft)
        if mode == "draft":
            log_decision(fname, "drafted", draft)
            continue
        action, body = interactive_review(fname, email, draft)
        if action in ("approved", "edited"):
            path = simulate_send(fname, body)
            log_decision(fname, action + "->sent", body)
            print(f"    simulated send -> {path}")
        else:
            log_decision(fname, "rejected", draft, note=body)
            print("    rejected, not sent.")
    print("\nDone. Decisions logged in decisions.log")


if __name__ == "__main__":
    main()
