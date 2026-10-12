# Submission: Agent Task Verifier

## Category
Intelligent Contracts

## Contract Name
Agent Task Verifier

## Summary
A reusable GenLayer primitive for trustless verification of autonomous-agent deliverables. A creator states a task and an agent address; the agent submits a deliverable URL; GenLayer validators reach consensus on `pass` / `fail` against the written specification, and every verdict updates one cumulative on-chain reputation record for that agent.

## What Makes This Unique
- **Consensus-based verification**: LLM validators decide "does this deliverable meet the spec?" instead of a trusted arbiter
- **Fetched content is bound into the decision**: the contract fetches the deliverable URL on-chain and embeds the exact bytes into the prompt — validators judge what the contract retrieved, not a URL they re-fetch on their own
- **One cumulative reputation record per agent**: pass `+5` (cap 100), fail `-10` (floor 0), `auto_passed` `+5`; every verdict accumulates into a single `AgentRecord` keyed by agent address — new tasks never reset prior results
- **Bounded verification**: after the verification window the agent can claim `auto_passed` — no task can hang forever

## How Consensus Is Used
The contract uses `gl.vm.run_nondet_unsafe()` with a custom validator function. Each validator independently fetches the deliverable URL on-chain (`gl.nondet.web.get`, non-200 reverts) and the **contract-fetched content is embedded directly into the prompt** (`--- BEGIN FETCHED CONTENT ---`), fenced and marked as untrusted data (prompt-injection hardening). Consensus is reached when validators agree on the exact stored decision (`pass` / `fail`) after their own independent fetch and verification.

## Technical Details
- Python-based GenLayer Intelligent Contract
- Uses `gl.nondet.exec_prompt()` for LLM verification decisions
- Uses `gl.nondet.web.get()` for contract-side deliverable acquisition (non-200 reverts)
- Custom validators require exact decision agreement
- TreeMap storage for tasks, a per-agent task index, and one cumulative `AgentRecord` per agent; reputation clamped 0–100
- Integer-only domain (scores, deadlines as ISO strings)

## Use Case
Marketplaces and orchestrators where autonomous agents take on paid or scored tasks (data pipelines, content generation, code/doc delivery) and the requester needs a transparent, reproducible pass/fail gate plus a durable track record for each agent.

## Verification
- 9/9 direct-mode unit tests (validation, role guards, pass/fail paths, timeout claim, reputation math, prompt-binds-fetched-content regression test, cumulative-across-tasks, timeout-updates-record, no-reset-on-create)
- `genvm-lint check` + validation pass (8 methods: 4 view, 4 write)
- On-chain verified on studionet: pass → record 55/1/1 → second task for the same agent leaves the record at 55/1/1 (no reset to 50/0/0) → fail on task 2 → cumulative record 45/2/1 (prior results preserved) → replay verify leaves the record unchanged → timeout-claim guard reverts before the deadline (unit-tested with time warp)

## Live Deployment
Deployed on GenLayer studionet (chain `61999`):
[`0x7AdE9cF0CE4008CCA1493b3c5285E89D735E2a93`](https://explorer-studio.genlayer.com/address/0x7AdE9cF0CE4008CCA1493b3c5285E89D735E2a93)

## Source Code
See `contracts/agent_task_verifier.py`

## Steward Request Response
**Request**: provide matching source with reputation maintained per agent across tasks — previously every new task started counters at 50/0/0, verification updated only that task, and `get_agent_reputation` returned the newest task, losing prior results.

**Fix**: reputation moved out of `AgentTask` into a single `AgentRecord` per agent address (`agent_records` TreeMap). `create_task` only initializes a missing record and never resets an existing one; both `verify_deliverable` (pass/fail) and `claim_verification_timeout` (auto_passed) apply their outcome through the same `_apply_outcome` helper; `get_agent_reputation` reads the record directly instead of deriving from the newest task. Each task's verdict is applied exactly once (status-flip guarded). Verified with 9/9 unit tests (incl. cumulative and no-reset tests) and on-chain: 55/1/1 → no reset → 45/2/1 → replay unchanged.
