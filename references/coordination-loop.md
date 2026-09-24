# DRGB coordination and evolution loop

This protocol connects agents, sessions, hosts, memories, and graphs. It does
not grant trading, deployment, messaging, credential, billing, or account
authority.

## Shared surfaces

- Coordination journal: append-only claims, heartbeats, handoffs, blocks, and completions.
- Authoritative state: repository/worktree, service/database/API, signed-in session, or domain system of record.
- Second brain: provenance-preserving memory sources and their owning sync/intake mechanisms.
- Knowledge graphs: codebase-memory, Graphify graphs, unified graphs, and task-specific subgraphs with freshness markers.
- Fleet topology: explicit SSH aliases, SGAM node inventories, runtime locations, and service health sources.

## Nested swarm architecture

Treat the ecosystem as a hierarchy of nested DRGB cells. DRGB is the governing
architecture. SGAM is the domain-neutral swarm control plane built inside DRGB.
The Second Brain is the shared provenance-preserving evidence and memory layer.
Each worker, task, team, domain, and system boundary has its own candidate
reality, realized reality, ownership, evidence, verification, and handoff.

The swarm evolves only from verified outcome feedback. Coordination events
atomically refresh the runtime user's `~/.drgb/second-brain` (or the
`second-brain` directory under an explicit `DRGB_STATE_DIR`); the next cycle
retrieves relevant evidence, compares predicted with actual outcomes, and may
propose improvements through replay, shadow, canary, and promotion gates. SGAM,
memory, graphs, and models may improve the system, but none may silently expand
its own authority.

## Cycle

1. **Discover** — record UTC time, runtime/host, SSH and fleet nodes in scope,
   repositories, dirty state, agent skill versions, memory sources, graphs and
   stale markers, active journal claims, runtime health, and authoritative domain
   state.
2. **Reconcile** — compare the request with commits, diffs, ledgers, memory,
   graph evidence, runtime events, and acknowledged handoffs. Prefer
   authoritative state over derived memory; preserve contradictions.
3. **Claim** — publish the smallest non-overlapping scope with exact resources.
   Treat unexplained dirty or untracked work as owned.
4. **Simulate** — state the expected result and falsifier; use dry run, preview,
   shadow, replay, tests, or a bounded checklist appropriate to risk.
5. **Bridge** — let deterministic policy bind evidence, payload, scope,
   obligations, expiry, and authority. Models may critique but not vote authority.
6. **Execute** — apply one reversible increment. Refresh authoritative state
   immediately before consequential writes.
7. **Verify** — independently observe the actual result and prediction error.
   Stop, compensate, or escalate on material divergence.
8. **Learn** — append a handoff, atomically refresh the DRGB Second Brain, and
   route verified knowledge through the owning memory or graph intake. Mark
   affected subgraphs stale or refresh through their existing planner; never
   hand-edit generated graph artifacts.
9. **Propagate** — synchronize verified skill/contract changes to discovered
   runtimes, run self-tests, and compare manifests. Copying without verification
   is not synchronization.
10. **Continue** — choose the next safe unblocked increment; do not duplicate an
    active claim.

## Collision and autonomy rules

- Never stage, revert, rewrite, commit, or delete another worker's unexplained changes.
- Prefer separate worktrees or disjoint file/resource ownership.
- Use append-only events, file locks, atomic writes, and idempotency keys.
- A stale heartbeat does not transfer ownership automatically; reconcile artifacts first.
- Resolve model disagreement with provenance and deterministic tests, never voting.
- Autonomous evolution may inspect, test, propose, and make bounded reversible changes within the user's request. It may not expand its own authority.
- Mark unsupported synchronization `DATA_UNAVAILABLE` and unresolved overlap `BLOCKED`.

## Handoff minimum

Include event ID, parent/correlation ID when available, skill/version, observed-at
time, worker/runtime/host, topology scope, base state, candidate outcome,
falsifier, bridge verdict and obligations, authority, changed resources,
verification and prediction error, memory/graph propagation, remaining
uncertainty, blocker, and next safe action.
