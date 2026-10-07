# Submission: Agent Task Verifier

## Category
Intelligent Contracts

## Contract Name
Agent Task Verifier

## Summary
A reusable GenLayer primitive for trustless verification of autonomous-agent deliverables. A creator states a task and an agent address; the agent submits a deliverable URL; GenLayer validators reach consensus on `pass` / `fail` against the written specification, and each verdict updates a persistent on-chain reputation score for the agent.

## What Makes This Unique
- **Consensus-based verification**: LLM validators decide "does this deliverable meet the spec?" instead of a trusted arbiter
- **Fetched content is bound into the decision**: the contract fetches the deliverable URL on-chain and embeds the exact bytes into the prompt — validators judge what the contract retrieved, not a URL they re-fetch on their own
- **Persistent on-chain agent reputation**: pass `+5` (cap 100), fail `-10` (floor 0), carried across tasks
- **Bounded verification**: after the verification window the agent can claim `auto_passed` — no task can hang forever

## How Consensus Is Used
The contract uses `gl.vm.run_nondet_unsafe()` with a custom validator function. Each validator independently fetches the deliverable URL on-chain (`gl.nondet.web.get`, non-200 reverts) and the **contract-fetched content is embedded directly into the prompt** (`--- BEGIN FETCHED CONTENT ---`), fenced and marked as untrusted data (prompt-injection hardening). Consensus is reached when validators agree on the exact stored decision (`pass` / `fail`) after their own independent fetch and verification.

## Technical Details
- Python-based GenLayer Intelligent Contract
- Uses `gl.nondet.exec_prompt()` for LLM verification decisions
- Uses `gl.nondet.web.get()` for contract-side deliverable acquisition (non-200 reverts)
- Custom validators require exact decision agreement
- TreeMap storage for tasks + per-agent task index; reputation clamped 0–100
- Integer-only domain (scores, deadlines as ISO strings)

## Use Case
Marketplaces and orchestrators where autonomous agents take on paid or scored tasks (data pipelines, content generation, code/doc delivery) and the requester needs a transparent, reproducible pass/fail gate plus a track record for each agent.

## Verification
- 7/7 direct-mode unit tests (validation, role guards, pass/fail paths, timeout claim, reputation math, prompt-binds-fetched-content regression test)
- `genvm-lint check` + validation pass (8 methods: 4 view, 4 write)
- On-chain verified on studionet: task creation (agent address correct) → deliverable submitted → verification (`pass`, reasoning cites the contract-fetched content) → reputation 55 → agent task index → timeout-claim guard (reverts before the deadline, state unchanged)

## Live Deployment
Deployed on GenLayer studionet (chain `61999`):
[`0xe82B5604E954CDb979AC4d286276aac3aacfb59c`](https://explorer-studio.genlayer.com/address/0xe82B5604E954CDb979AC4d286276aac3aacfb59c)

## Source Code
See `contracts/agent_task_verifier.py`
