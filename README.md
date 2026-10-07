<div align="center">

# Agent Task Verifier

**Trustless verification of autonomous-agent deliverables — pass/fail decided by GenLayer validator consensus, with on-chain agent reputation.**

![GenLayer](https://img.shields.io/badge/GenLayer-Intelligent%20Contract-6a4cff)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![Status](https://img.shields.io/badge/status-live%20on%20studionet-2ea44f)
![Tests](https://img.shields.io/badge/tests-7%20passed-2ea44f)

[Live Contract](https://explorer-studio.genlayer.com/address/0xe82B5604E954CDb979AC4d286276aac3aacfb59c) ·
[GenLayer Docs](https://docs.genlayer.com)

</div>

---

## Why

Autonomous agents deliver work over URLs, but someone has to judge *"does this deliverable meet the spec?"* AgentTaskVerifier removes the trusted arbiter: a creator states a task and an agent address, the agent submits a deliverable URL, and GenLayer validators reach consensus on `pass` / `fail` — feeding a persistent per-agent reputation score.

## Live Deployment

| | |
|---|---|
| **Contract** | [AgentTaskVerifier](https://explorer-studio.genlayer.com/address/0xe82B5604E954CDb979AC4d286276aac3aacfb59c) |
| **Address** | `0xe82B5604E954CDb979AC4d286276aac3aacfb59c` |
| **Network** | GenLayer studionet (chain `61999`) |
| **Status** | ✅ deployed + audited on-chain |

## Highlights

- 🤖 **Spec-based verification** — validators judge the deliverable against the task specification, not against a link
- 🔍 **Evidence is fetched, not just linked** — the contract fetches the deliverable URL on-chain (`gl.nondet.web.get`, non-200 reverts) and embedded the bytes into the prompt (`--- BEGIN FETCHED CONTENT ---`)
- 🗳️ **Exact-decision consensus** — validators independently re-fetch + re-verify and must agree on the identical decision
- 📈 **On-chain reputation** — pass `+5` (cap 100), fail `-10` (floor 0), persistent per agent across tasks
- ⏱️ **Bounded verification** — the creator has a verification window; after it, the agent claims `auto_passed`, so tasks never hang

## How It Works

```
create_task (creator: title + spec + agent address + deadline)
      │
      ▼
submit_deliverable (assigned agent, before task deadline)
      │
      ▼
verify_deliverable (creator — LLM consensus, within verification window)
      │                          │
      ├── pass ──────────────► status=verified, reputation +5
      └── fail ──────────────► status=failed,  reputation -10
      │
      └── verification window passed ──► claim_verification_timeout (agent)
                                          → status=auto_passed, reputation +5
```

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
- Reputation transitions are monotone and clamped (0–100); terminal task states never transition again
- Full input validation (title/spec/agent required, length caps, deadline checks)

## Test

```bash
gltest tests/ -q   # 7 passed
```

## Lint

```bash
genvm-lint check contracts/agent_task_verifier.py
```
