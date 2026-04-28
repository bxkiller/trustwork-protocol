# Trustwork-protocol
AI-powered freelance escrow with on-chain dispute resolution built on GenLayer Intelligent Contracts
# TrustWork Protocol 🤝⚖️

> **AI-Powered Freelance Escrow & Dispute Resolution on GenLayer**
>
> No lawyers. No middlemen. No Upwork fees. Just programmable trust.

[![Built on GenLayer](https://img.shields.io/badge/Built%20on-GenLayer-6C3CE1?style=flat-square)](https://genlayer.com)
[![Network](https://img.shields.io/badge/Network-Testnet%20Bradbury-blue?style=flat-square)](https://docs.genlayer.com)
[![Language](https://img.shields.io/badge/Language-Python%20%2F%20GenVM-yellow?style=flat-square)](https://docs.genlayer.com/developers/intelligent-contracts/introduction)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📖 Table of Contents

- [What is TrustWork?](#what-is-trustwork)
- [Why It Matters](#why-it-matters)
- [How It Works](#how-it-works)
- [Contract Architecture](#contract-architecture)
- [Getting Started](#getting-started)
- [Step-by-Step Tutorial](#step-by-step-tutorial)
- [Payment Logic](#payment-logic)
- [AI Verdict System](#ai-verdict-system)
- [Appeal Process](#appeal-process)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)

---

## What is TrustWork?

TrustWork Protocol is a decentralized escrow and dispute resolution platform built as a **GenLayer Intelligent Contract**. It solves the most fundamental problem in freelancing: *trust between strangers*.

Traditional platforms like Upwork or Fiverr solve trust by acting as a central authority — they hold the money, read the brief, evaluate the work, and decide who gets paid. TrustWork replaces that central authority with something better: **a committee of AI validators running on-chain**, coordinated by GenLayer's Optimistic Democracy consensus.

When a freelancer submits work, the contract automatically sends the job brief and the deliverable to the LLM validator network. The validators independently evaluate the submission, reach consensus, and execute payment — all on-chain, all transparent, all instant.

---

## Why It Matters

The global freelance market is worth **$400 billion+** and growing. Yet it still runs on centralized trust intermediaries who:

- Take 10–20% fees
- Have opaque dispute processes
- Can ban accounts arbitrarily
- Create bottlenecks at scale

TrustWork demonstrates that **GenLayer's Intelligent Contracts** can replace that entire trust layer with a few hundred lines of Python. This is exactly the kind of use case GenLayer was built for: subjective decisions, qualitative evaluation, and performance-based payments — all enforced on-chain without oracles or human moderators.

---

## How It Works

```
CLIENT                    CONTRACT                   FREELANCER
  │                          │                           │
  │── post_job() ──────────► │                           │
  │   (payment locked        │                           │
  │    in escrow)            │                           │
  │                          │ ◄──── accept_job() ───────│
  │                          │                           │
  │                          │ ◄──── submit_work() ──────│
  │                          │                           │
  │── evaluate_submission()─►│                           │
  │   (or freelancer calls)  │                           │
  │                          │                           │
  │                    ┌─────┴──────┐                    │
  │                    │ LLM Panel  │                    │
  │                    │ Evaluates  │                    │
  │                    │ Brief vs   │                    │
  │                    │ Delivery   │                    │
  │                    └─────┬──────┘                    │
  │                          │                           │
  │           ┌──────────────┼──────────────┐            │
  │           ▼              ▼              ▼            │
  │        APPROVED       PARTIAL       REJECTED         │
  │           │              │              │            │
  │      Full payout    Split by score   Full refund     │
  │      to freelancer  proportionally   to client       │
```

---

## Contract Architecture

### State Machine

Every job moves through a strict set of statuses:

```
OPEN → IN_PROGRESS → SUBMITTED → APPROVED
                              ↘ PARTIAL (DISPUTED) → APPROVED / REJECTED
                              ↘ REJECTED
     ↘ CANCELLED (from OPEN only)
```

### Data Model

Each job stores:

| Field | Type | Description |
|---|---|---|
| `job_id` | str | Auto-generated (e.g. "TW-42") |
| `client` | Address | Wallet that posted the job |
| `freelancer` | Address | Wallet that accepted |
| `brief` | str | Full job description (natural language) |
| `payment_wei` | u256 | Escrowed payment |
| `deadline` | u256 | Unix timestamp |
| `status` | str | Current state (see above) |
| `deliverable_url` | str | Submitted work link |
| `ai_verdict` | str | Full AI reasoning stored on-chain |
| `ai_score` | u256 | Quality score 0–100 |

### Public Methods

| Method | Who Calls | Description |
|---|---|---|
| `post_job()` | Client | Post job, lock payment in escrow |
| `cancel_job()` | Client | Cancel OPEN job, reclaim funds |
| `accept_job()` | Freelancer | Claim an open job |
| `submit_work()` | Freelancer | Submit deliverable |
| `evaluate_submission()` | Either | Trigger AI evaluation |
| `appeal_verdict()` | Either | Contest a verdict with reasoning |
| `get_job()` | Anyone | Read full job details |
| `get_ai_verdict()` | Anyone | Read on-chain AI reasoning |

---

## Getting Started

### Prerequisites

- A browser (no local setup needed for testing)
- A GenLayer wallet (testnet)
- Testnet tokens from the [GenLayer faucet](https://genlayer.com)

### Option A — GenLayer Studio (Recommended for beginners)

The fastest way to test this contract with zero setup:

1. Go to **[studio.genlayer.com](https://studio.genlayer.com)**
2. Click **"New Contract"** or paste the file directly into the editor
3. Copy the contents of `trustwork_protocol.py` into the editor
4. Click **Deploy** — the Studio handles everything

### Option B — GenLayer CLI

```bash
# Install the GenLayer CLI
npm install -g @genlayer/cli

# Initialise a project
genlayer init trustwork
cd trustwork

# Copy contract into contracts/
cp trustwork_protocol.py contracts/

# Start local network
genlayer up

# Deploy
genlayer deploy contracts/trustwork_protocol.py \
  --args '[200]'
# 200 = 2% platform fee in basis points
```

---

## Step-by-Step Tutorial

This tutorial walks through a complete job lifecycle — from posting to AI payment release.

### Step 1: Deploy the Contract

Deploy with a platform fee of `200` basis points (2%):

```python
# Constructor argument
platform_fee_bps = 200
```

In the Studio, click **Deploy**, enter `200` as the constructor argument.

---

### Step 2: Post a Job (Client)

Call `post_job()` with a value attached (the escrow payment):

```python
post_job(
    title    = "Build a landing page for my SaaS product",
    brief    = """
        I need a responsive one-page landing page for my SaaS tool.
        Requirements:
        - Hero section with headline and CTA button
        - Features section (3 cards)
        - Pricing table (2 tiers)
        - Footer with links
        Built in plain HTML/CSS/JS, no frameworks required.
        Mobile responsive. Delivered as a GitHub repo.
    """,
    deadline = 1780000000   # Unix timestamp (set to ~1 week from now)
)
# Send 0.1 ETH as msg.value
```

The contract returns a `job_id` like `"TW-1"`. The payment is now locked.

---

### Step 3: Accept the Job (Freelancer)

From a different wallet, call `accept_job()`:

```python
accept_job(job_id = "TW-1")
```

Status changes from `OPEN` → `IN_PROGRESS`.

---

### Step 4: Submit Work (Freelancer)

After completing the work, submit it:

```python
submit_work(
    job_id           = "TW-1",
    deliverable_url  = "https://github.com/yourname/saas-landing",
    deliverable_note = """
        Completed the landing page as specified. The repo includes:
        - index.html with hero, features, and pricing sections
        - style.css with full mobile responsiveness
        - All 3 feature cards and 2 pricing tiers implemented
        - Tested on Chrome, Firefox, and mobile viewport
    """
)
```

Status changes to `SUBMITTED`.

---

### Step 5: Trigger AI Evaluation

Either party calls this to invoke the LLM validator panel:

```python
evaluate_submission(job_id = "TW-1")
```

This is where GenLayer's magic happens. Behind the scenes:

1. A committee of validators (each running an LLM) receives the prompt
2. The **leader validator** proposes a verdict
3. Other validators independently evaluate and check if the verdict is structurally valid
4. Consensus is reached via **Optimistic Democracy**
5. The result is written on-chain and payment executes automatically

---

### Step 6: Read the Verdict

```python
get_ai_verdict(job_id = "TW-1")

# Example output:
# "APPROVED (score: 87/100) — The deliverable fully addresses the brief.
#  A GitHub repo was provided with all required sections implemented
#  and mobile responsiveness confirmed. | Missing: Nothing"
```

If `APPROVED`: freelancer receives full payment minus the 2% fee.

---

### Bonus: Test a PARTIAL verdict

Try submitting an incomplete deliverable intentionally:

```python
submit_work(
    job_id           = "TW-2",
    deliverable_url  = "https://github.com/yourname/incomplete-page",
    deliverable_note = "I built the hero section and features but ran out
                        of time for the pricing table."
)
```

Expected AI output: `PARTIAL` with a score around 55–65, triggering a proportional split (freelancer gets ~60%, client refunded ~40%).

---

## Payment Logic

### APPROVED — Full Payout

```
freelancer receives: payment - platform_fee
platform receives:   payment * fee_bps / 10000
```

### PARTIAL — Proportional Split

```
freelancer receives: (payment * ai_score / 100) - fee
client receives:     payment * (100 - ai_score) / 100
```

Example: 0.1 ETH escrowed, AI score = 65:
- Freelancer gets: `0.065 ETH - 2% fee = 0.0637 ETH`
- Client refunded: `0.035 ETH`

### REJECTED — Full Refund

```
client receives: full payment (no fee charged)
```

---

## AI Verdict System

The AI evaluation prompt is carefully engineered to:

1. **Provide full context** — the entire original brief + deliverable description
2. **Request structured JSON** — so the response is parseable and consistent
3. **Define a scoring rubric** — prevents arbitrary verdicts
4. **Store reasoning on-chain** — full transparency, verifiable forever

The validator function checks **structure not exact match**, because LLM outputs are non-deterministic across validators. This is how GenLayer's **Equivalence Principle** works in practice.

```python
def validator_fn(leader_result) -> bool:
    # We don't check if validators return identical text —
    # we check if they all agree on a valid structure.
    return (
        data.get("verdict") in ("APPROVED", "PARTIAL", "REJECTED")
        and 0 <= score <= 100
        and len(reasoning) > 10
    )
```

---

## Appeal Process

If either party disagrees with the verdict, they can appeal with a written reason:

```python
appeal_verdict(
    job_id        = "TW-1",
    appeal_reason = """
        The client marked the work as incomplete, but the pricing table
        was clearly included in the repo under /components/pricing.html.
        Please re-evaluate with attention to the full repo structure.
    """
)
```

On appeal, GenLayer automatically expands the validator committee for a larger consensus sample. The appeal reason is included in the new prompt, giving the AI fresh context to reconsider.

---

## Project Structure

```
trustwork-protocol/
├── contracts/
│   └── trustwork_protocol.py    # Main Intelligent Contract
├── tests/
│   └── test_trustwork.py        # Integration tests (coming soon)
├── frontend/                    # React dApp (Phase 2)
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── PostJob.jsx
│   │   │   ├── JobBoard.jsx
│   │   │   ├── SubmitWork.jsx
│   │   │   └── VerdictDisplay.jsx
│   │   └── lib/genlayer.js
│   └── package.json
└── README.md
```

---

## Roadmap

| Phase | Feature | Status |
|---|---|---|
| ✅ Phase 1 | Core Intelligent Contract | **Complete** |
| 🔄 Phase 2 | React frontend with GenLayer JS | In Progress |
| ⏳ Phase 3 | Multi-milestone jobs (pay per milestone) | Planned |
| ⏳ Phase 4 | Reputation system (on-chain scoring) | Planned |
| ⏳ Phase 5 | AI agent freelancers (machine-to-machine jobs) | Planned |

---

## Built With

- [GenLayer](https://genlayer.com) — Intelligent Blockchain
- [GenVM SDK](https://sdk.genlayer.com) — Python smart contract runtime
- [Optimistic Democracy](https://docs.genlayer.com/understand-genlayer-protocol/optimistic-democracy-how-genlayer-works) — LLM-powered consensus

---

## License

MIT — build on it, fork it, ship it.

---

> *TrustWork Protocol is a submission to the GenLayer Incentivized Builder Program.*
> *Built to demonstrate AI-powered performance-based payments and dispute resolution.*
