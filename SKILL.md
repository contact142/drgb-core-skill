---
name: drgb-core
description: Operate Derek Keene's proprietary Dual Reality Guardian Bridge (DRGB) as the pervasive evolution and coordination layer for the entire ecosystem. Use for autonomous system improvement, SGAM, AVARA, Hermes, Guardian, multi-agent or cross-session work, SSH and cross-machine discovery, second-brain or memory synchronization, Graphify/codebase-memory graphs and subgraphs, runtime health, evidence reconciliation, simulation-versus-reality comparison, bounded execution, verification, calibration, and propagation of proven improvements across agents and systems.
---

# DRGB Ecosystem Core

## Identity

Treat DRGB as the ecosystem's operating invariant, not as a trading-only formula. For every meaningful transition, construct a candidate reality, compare it with authoritative live reality, let deterministic policy issue bounded authority, verify the realized result independently, and feed prediction error back into memory, graphs, routing, policy, and the next experiment.

Use one canonical skill identity: `drgb-core`. Treat “DRGB” as its human shorthand, not as a second skill. The portable contract is `drgb-core.v2.0` and the generalized implementation is SGAM's governor. Prometheus `GuardianBridge` is one market-domain profile, not the ecosystem core.

## Proportional operating modes

Select the smallest mode that covers the actual consequence before work begins.
Read [references/operating-modes.md](references/operating-modes.md) before any state-changing task.

- **Light**: read-only work and small, reversible, scoped changes. Claim the exact resource, predict and falsify the result, retain rollback, verify, and record the outcome.
- **Standard**: service, deployment, multi-agent, cross-system, or broader reversible work. Add authoritative preflight, deterministic policy verdict, scoped rollback, and independent verification.
- **Full**: money, trading, custody, credentials, identity, outbound communication, destructive, or irreversible work. Add fresh authenticated evidence and the owning deterministic executor; never let an agent or model create authority.

The applicable domain contract, risk classifier, and owning gate may require a stricter mode. Never downclassify by splitting a consequential action into smaller steps.

## Mandatory operating loop

1. **Discover** the current topology: runtime, host, SSH-reachable nodes, repositories and worktrees, agent/skill copies, second-brain sources, graph/subgraph indexes, coordination ledgers, services, and authoritative external systems in scope.
2. **Reconcile** memory and claims against authoritative state. Memory, graphs, prompts, model claims, and handoffs are evidence; they are never automatically live truth.
3. **Claim** the smallest non-overlapping resource scope in the shared journal before cross-agent or cross-session mutation.
4. **Construct candidate reality** with a dry run, simulation, replay, test, preview, checklist, shadow lane, or explicit predicted outcome and falsifier.
5. **Bridge** candidate and live reality using deterministic policy. Models may generate hypotheses and critiques but may not grant themselves authority.
6. **Execute** one bounded, reversible increment already authorized by the user's request and the target system's gate.
7. **Verify** actual state independently, compute or describe prediction error, and stop or compensate on material divergence.
8. **Learn** by publishing provenance-labeled evidence to the coordination journal and the appropriate second-brain or graph intake. Propose policy, prompt, routing, or code improvements; never self-promote them past deterministic gates.
9. **Propagate** a verified contract or skill update to discovered runtimes, then compare checksums/self-tests. Do not claim synchronization from copying alone.
10. **Continue** with the next safe, unblocked increment when the user requests ongoing autonomous progress.

Read [references/ecosystem-topology.md](references/ecosystem-topology.md) before ecosystem discovery or synchronization. Read [references/coordination-loop.md](references/coordination-loop.md) for shared ownership and event rules. Read [references/contract.md](references/contract.md) for machine-readable envelopes. Read [references/market-profile.md](references/market-profile.md) only for Prometheus/AVARA market DRGB.

## Pervasive integration

Lock DRGB into the ecosystem through contracts and evidence surfaces, not indiscriminate edits:

- **Agent plane:** install the same package in each discovered Codex, Claude, Hermes, and compatible agent runtime; add a concise global policy pointing to the canonical skill.
- **Node plane:** use SSH aliases or fleet configuration for explicit nodes. Probe read-only by default; require normal authorization for remote mutation or deployment.
- **Memory plane:** inventory second-brain sources, freshness, provenance, and update mechanisms. Write only through the owning intake or append-only handoff surface.
- **Knowledge plane:** maintain the dependency-free coordination subgraph from journal events; query codebase-memory/Graphify for richer code and semantic relationships, track graph roots and stale markers, refresh through existing planners, and preserve EXTRACTED/INFERRED/AMBIGUOUS provenance.
- **Coordination plane:** publish claims, heartbeats, handoffs, blocks, and completion events with exact scope and verification.
- **Evolution plane:** maintain paired baselines, falsifiers, held-out or replay evidence, rollback paths, and promotion stages. Improvements may be proposed autonomously; authority expansion may not.

Use [scripts/ecosystem_probe.py](scripts/ecosystem_probe.py) for a read-only topology manifest. It never opens SSH connections unless explicit `--ssh-host` values are supplied. Use [scripts/coordination_journal.py](scripts/coordination_journal.py) for the append-only shared journal, node-local Second Brain, and deterministic `drgb-subgraph.json`. Use [scripts/probe_drgb_core.py](scripts/probe_drgb_core.py) to validate installation and evidence envelopes.

Use [scripts/fleet_sync.py](scripts/fleet_sync.py) to inspect explicit SSH nodes
and, only with `--apply`, synchronize the canonical package and merge journals
without dropping node-local events. Run it without mutation flags first. A
successful merge regenerates each node's local Second Brain; its graph refresh
still follows the owning Graphify/SGAM refresh workflow.

## Authority boundary

Autonomous evolution means continuously discovering gaps, selecting safe work, implementing bounded changes, testing, recording outcomes, and proposing the next improvement. It does not mean ambient permission.

Never infer authority to send messages, publish content, change billing, expose credentials, deploy, trade, move funds, impersonate users, alter production accounts, or broaden agent permissions. Use the authenticated and deterministic gate belonging to that system. Fail closed on missing identity, stale evidence, unresolved ownership, invalid grants, irreversible ambiguity, or material candidate/live divergence.

## Required handoff

Report skill/version, observed-at time, worker/runtime, topology scope, authoritative sources, candidate reality, bridge verdict, granted authority, realized outcome, prediction error, evidence class and freshness, baseline, falsifier, graph/memory updates, propagation status, checks, blockers, next safe action, and remaining uncertainty. Use `DATA_UNAVAILABLE` or `BLOCKED` instead of inventing state.
