# northline-support-desk

Agent-run customer support with a human approval gate, for a fictional candle shop.

An AI agent reads incoming support emails, drafts a reply in the shop's brand
voice using a **local open-weight model** (no cloud API), and then **stops**.
Nothing is marked sent until a human reviews the draft and chooses
**approve / edit / reject**. Every decision is logged.

## What it does

```
emails/*.txt  ->  local model drafts reply  ->  human review
                                                      |
                                   approve / edit ----+----> sent/  + decisions.log
                                   reject    ----------------------> decisions.log
```

The whole point is the gate: the agent does the typing, the human owns the send.

## The 5 demo tickets

Fake customer emails for "Ember & Wick" (fictional shop, fictional order numbers,
`example.com` addresses): late order, wrong scent, damaged in shipping,
wholesale inquiry, refund request.

## Model

- **Qwen2.5-7B-Instruct**, Q4_K_M GGUF, run locally via
  [llama.cpp](https://github.com/ggml-org/llama.cpp) (`llama-server`,
  OpenAI-compatible endpoint). Runs fully offline on a single consumer GPU box.

## Run it

```bash
# 1. Serve the model (any machine; this repo just talks to the endpoint)
llama-server -m Qwen2.5-7B-Instruct-Q4_K_M.gguf --port 18091 -c 4096

# 2. Draft-only pass (writes drafts/, no review)
python3 desk.py draft

# 3. Full review loop: for each email, approve [a], edit [e], or reject [r]
python3 desk.py review
```

Environment overrides:

| var | default | meaning |
|---|---|---|
| `DESK_MODEL_URL` | `http://127.0.0.1:18091/v1/chat/completions` | any OpenAI-compatible endpoint |
| `DESK_MODEL_NAME` | `Qwen2.5-7B-Instruct-Q4_K_M (local llama.cpp)` | label used in logs |

## Honesty notes

- "Sending" is simulated: approved replies are written to `sent/`, no real mail
  leaves the machine.
- All customers, orders, and the shop are fictional.
- The brand-voice prompt forbids the model from inventing order numbers,
  dates, or policies; it must defer unknowns to the human.
