<div align="center">

# Agent Task Verifier

**Trustless verification of autonomous-agent deliverables — pass/fail decided by GenLayer validator consensus, with cumulative on-chain agent reputation.**

![GenLayer](https://img.shields.io/badge/GenLayer-Intelligent%20Contract-6a4cff)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![Status](https://img.shields.io/badge/status-live%20on%20studionet-2ea44f)
![Tests](https://img.shields.io/badge/tests-9%20passed-2ea44f)

[Live Contract](https://explorer-studio.genlayer.com/address/0x7AdE9cF0CE4008CCA1493b3c5285E89D735E2a93) ·
[GenLayer Docs](https://docs.genlayer.com)

</div>

---

## Why

Autonomous agents deliver work over URLs, but someone has to judge *"does this deliverable meet the spec?"* AgentTaskVerifier removes the trusted arbiter: a creator states a task and an agent address, the agent submits a deliverable URL, and GenLayer validators reach consensus on `pass` / `fail` — feeding one cumulative, per-agent reputation record that survives across every task the agent takes.

## Live Deployment

| | |
|---|---|
| **Contract** | [AgentTaskVerifier](https://explorer-studio.genlayer.com/address/0x7AdE9cF0CE4008CCA1493b3c5285E89D735E2a93) |
| **Address** | `0x7AdE9cF0CE4008CCA1493b3c5285E89D735E2a93` |
| **Network** | GenLayer studionet (chain `61999`) |
| **Status** | ✅ deployed + audited on-chain |

## Highlights

- 🎯 **Spec-based verification** — validators judge the deliverable against the task specification, not against a link
- 🔍 **Evidence is fetched, not just linked** — the contract fetches the deliverable URL on-chain (`gl.nondet.web.get`, non-200 reverts) and embeds the bytes into the prompt (`--- BEGIN FETCHED CONTENT ---`)
- 🗳️ **Exact-decision consensus** — validators independently re-fetch + re-verify and must agree on the identical decision
- 📈 **Cumulative on-chain reputation** — one `AgentRecord` per agent address: pass `+5` (cap 100), fail `-10` (floor 0), `auto_passed` `+5`; verdicts from every task accumulate and creating a new task never resets the record
- ⏱️ **Bounded verification** — the creator has a verification window; after it, the agent claims `auto_passed`, so tasks never hang

## How It Works

```
create_task (creator: title + spec + agent address + deadline)
      │                            └─ initializes AgentRecord[agent] only if missing
      ▼
submit_deliverable (assigned agent, before task deadline)
      │
      ▼
verify_deliverable (creator — LLM consensus, within verification window)
      │                          │
      ├── pass ──────────────► status=verified ─┐
      └── fail ──────────────► status=rejected ─┤
      │                                         ├─► AgentRecord[agent] (cumulative):
      └── window passed ──► claim_timeout ──────┤    pass/auto: +5 (cap 100), passed+1
          (agent)  → status=auto_passed ────────┘    fail: -10 (floor 0)
                                                     total+1 always; never reset
```

`get_agent_reputation(agent_address)` reads that single record — not the newest task.

## Methods

| Role | Method | Guard |
|---|---|---|
| Creator | `create_task`, `verify_deliverable` | creator-only verification; status + deadline checks |
| Agent | `submit_deliverable`, `claim_verification_timeout` | assigned-agent only; open/submitted states + deadlines |
| Any | `get_task`, `get_all_tasks`, `get_agent_tasks`, `get_agent_reputation` | read-only |

## Security Model

- Role enforcement on every mutation (submit/timeout agent-only, verify creator-only)
- **Contract-side acquisition**: deliverable URL is fetched inside consensus; unreachable/non-200 URLs revert the verification
- **Prompt-injection hardening**: fetched content is fenced and marked as untrusted data
- Validators must match the leader's exact `decision` (`pass` / `fail`) after their own independent fetch + verification
- **One cumulative `AgentRecord` per agent address** (score / total / passed), updated by both verdict paths (`verify_deliverable` and `claim_verification_timeout`) through the same `_apply_outcome` helper; `create_task` only initializes a missing record and never resets an existing one; `get_agent_reputation` reads the record directly
- Each task's verdict is applied exactly once (status-flip guarded, replay-safe); reputation clamped 0–100; terminal task states never transition again
- Full input validation (title/spec/agent required, length caps, deadline checks)

## Test

```bash
gltest tests/ -q   # 9 passed
```

## Lint

```bash
genvm-lint check contracts/agent_task_verifier.py
```
