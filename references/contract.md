# DRGB ecosystem contract

## Identity

```json
{
  "skill": "drgb-core",
  "contract_version": "drgb-core.v2.0",
  "architecture": "Derek Keene proprietary Dual Reality Guardian Bridge",
  "generalized_core": "sgam.governor.governor.Governor",
  "authority": "deterministic_bounded_grants_only",
  "model_role": "reasoning_and_hypothesis_only"
}
```

The generalized DRGB core governs candidate reality versus live reality at
Action, Agent, Team, and System scales. A domain profile may compute additional
metrics, but it must not redefine the ecosystem contract or grant authority.

## Ecosystem evidence envelope

```json
{
  "schema_version": 2,
  "skill": "drgb-core",
  "contract_version": "drgb-core.v2.0",
  "observed_at": "UTC ISO-8601",
  "worker": {"runtime": "...", "model": "...", "session": "...", "host": "..."},
  "scope": {
    "scale": "action|agent|team|system",
    "task": "...",
    "systems": [],
    "nodes": [],
    "repos": [],
    "resources": []
  },
  "topology": {
    "ssh": {"source": "...", "observed": [], "reachable": []},
    "memory": {"sources": [], "freshness": "fresh|stale|mixed|unknown"},
    "graphs": {"indexes": [], "freshness": "fresh|stale|mixed|unknown"},
    "runtimes": {"skill_copies": [], "synchronized": false}
  },
  "candidate_reality": {
    "kind": "simulation|dry_run|preview|shadow|replay|test|checklist|hypothesis",
    "source": "...",
    "predicted_outcome": "...",
    "falsifier": "..."
  },
  "live_reality": {
    "source": "...",
    "state_before": "...",
    "state_after": "...",
    "fresh": false
  },
  "bridge": {
    "verdict": "approve|modify|defer|reject|escalate|data_unavailable|blocked",
    "policy_version": "...",
    "obligations": [],
    "grant_scope": [],
    "expires_at": null
  },
  "execution": {
    "authority": "reasoning_only|bounded_write|authenticated_gate",
    "idempotency_key": "...",
    "changed_resources": []
  },
  "verification": {
    "source": "...",
    "checks": [],
    "result": "pass|fail|not_run",
    "prediction_error": "..."
  },
  "learning": {
    "baseline": "...",
    "memory_updates": [],
    "graph_updates": [],
    "promotion_stage": "proposal|shadow|replay|paper|canary|bounded_live",
    "next_experiment": "..."
  },
  "uncertainty": []
}
```

Every material field must identify an authoritative source or say
`DATA_UNAVAILABLE`. Freshness is computed from source timestamps and configured
thresholds, not asserted by a model. A bridge verdict binds the exact payload,
policy version, evidence, scope, obligations, and expiry. It is not reusable
after any bound input changes.

## Prompt envelope

```text
DRGB_CORE_SKILL=drgb-core
DRGB_CONTRACT_VERSION=drgb-core.v2.0
DRGB_ARCHITECTURE=dual_reality_guardian_bridge
DRGB_GENERALIZED_CORE=sgam.governor.governor.Governor
DRGB_MODEL_ROLE=reasoning_hypothesis_critique_only
DRGB_COMPUTE_BOUNDARY=deterministic_system_computes;model_interprets
DRGB_AUTHORITY=bounded_grants_only;never_model_vote
DRGB_LOOP=discover>reconcile>claim>simulate>bridge>execute>verify>learn>propagate>continue
DRGB_ECOSYSTEM=ssh+agents+second_brain+graphs+subgraphs+services+domain_systems
```

Include only the task-relevant topology and evidence. Never inject credentials,
private account data, or unrelated memory merely to make a prompt complete.

## Fail-closed conditions

Block the affected path on missing or stale authoritative state, invalid or
expired grants, unresolved ownership, scope drift, failed verification,
irreversible ambiguity, security/identity failure, or material divergence.
Availability-oriented tasks may fail open only when an explicit risk policy says
so; security, identity, financial, and irreversible-action gates always fail
closed.

## Evolution contract

Use paired baselines and declared falsifiers. Separate evidence acquisition,
derived judgment, execution, verification, and promotion. Feed verified outcomes
to append-only coordination and owning memory/graph intake surfaces. Learned
changes remain proposals until replay/shadow/canary evidence and deterministic
promotion policy accept them. No agent, model, skill, graph, or memory store may
self-authorize expanded scope.
