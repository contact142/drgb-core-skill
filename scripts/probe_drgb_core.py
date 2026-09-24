#!/usr/bin/env python3
"""Validate the portable DRGB ecosystem contract without external mutation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SKILL = "drgb-core"
VERSION = "drgb-core.v2.0"
GENERALIZED_CORE = "sgam.governor.governor.Governor"
SCALES = {"action", "agent", "team", "system"}
VERDICTS = {"approve", "modify", "defer", "reject", "escalate", "data_unavailable", "blocked"}
AUTHORITIES = {"reasoning_only", "bounded_write", "authenticated_gate"}
RESULTS = {"pass", "fail", "not_run"}
FORBIDDEN_MODEL_KEYS = {
    "action",
    "decision",
    "execute_now",
    "live_authority",
    "mutation_allowed",
    "order_payload",
    "provider",
    "target_price",
    "withdrawal",
}
REQUIRED_FIELDS = {
    "schema_version",
    "skill",
    "contract_version",
    "observed_at",
    "worker",
    "scope",
    "topology",
    "candidate_reality",
    "live_reality",
    "bridge",
    "execution",
    "verification",
    "learning",
    "uncertainty",
}


def context() -> dict[str, Any]:
    return {
        "skill": SKILL,
        "contract_version": VERSION,
        "architecture": "dual_reality_guardian_bridge",
        "generalized_core": GENERALIZED_CORE,
        "model_role": "reasoning_hypothesis_critique_only",
        "compute_boundary": "deterministic_system_computes;model_interprets",
        "authority": "bounded_grants_only;never_model_vote",
        "loop": [
            "discover",
            "reconcile",
            "claim",
            "simulate",
            "bridge",
            "execute",
            "verify",
            "learn",
            "propagate",
            "continue",
        ],
        "ecosystem": [
            "ssh",
            "agents",
            "second_brain",
            "graphs",
            "subgraphs",
            "services",
            "domain_systems",
        ],
        "fail_closed": [
            "missing_identity",
            "stale_authoritative_state",
            "unresolved_ownership",
            "invalid_or_expired_grant",
            "irreversible_ambiguity",
            "material_divergence",
        ],
    }


def _parse_timestamp(value: Any) -> bool:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _walk_forbidden(value: Any, path: tuple[str, ...] = ()) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_MODEL_KEYS:
                found.append(".".join((*path, str(key))))
            found.extend(_walk_forbidden(child, (*path, str(key))))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_forbidden(child, (*path, str(index))))
    return found


def validate_envelope(value: Any) -> tuple[list[str], list[str]]:
    if not isinstance(value, dict):
        return ["root:not_object"], ["invalid_envelope"]
    errors = [f"missing:{key}" for key in sorted(REQUIRED_FIELDS - value.keys())]
    blocks: list[str] = []
    if value.get("schema_version") != 2:
        errors.append("schema_version:expected_2")
    if value.get("skill") != SKILL:
        errors.append(f"skill:expected_{SKILL}")
    if value.get("contract_version") != VERSION:
        errors.append(f"contract_version:expected_{VERSION}")
    if not _parse_timestamp(value.get("observed_at")):
        errors.append("observed_at:timezone_iso8601_required")

    worker = value.get("worker")
    if not isinstance(worker, dict) or not all(worker.get(key) for key in ("runtime", "host")):
        errors.append("worker:runtime_and_host_required")

    scope = value.get("scope")
    if not isinstance(scope, dict) or scope.get("scale") not in SCALES:
        errors.append("scope.scale:invalid")

    candidate = value.get("candidate_reality")
    if not isinstance(candidate, dict) or not candidate.get("predicted_outcome"):
        errors.append("candidate_reality.predicted_outcome:required")
    if not isinstance(candidate, dict) or not candidate.get("falsifier"):
        errors.append("candidate_reality.falsifier:required")

    live = value.get("live_reality")
    if not isinstance(live, dict):
        errors.append("live_reality:not_object")
    elif live.get("fresh") is not True:
        blocks.append("missing_or_stale_live_reality")

    bridge = value.get("bridge")
    verdict = bridge.get("verdict") if isinstance(bridge, dict) else None
    if verdict not in VERDICTS:
        errors.append("bridge.verdict:invalid")
    elif verdict in {"reject", "defer", "escalate", "data_unavailable", "blocked"}:
        blocks.append(f"bridge_{verdict}")

    execution = value.get("execution")
    authority = execution.get("authority") if isinstance(execution, dict) else None
    if authority not in AUTHORITIES:
        errors.append("execution.authority:invalid")
    elif authority != "reasoning_only" and verdict not in {"approve", "modify"}:
        errors.append("execution.authority:requires_approving_bridge")

    verification = value.get("verification")
    result = verification.get("result") if isinstance(verification, dict) else None
    if result not in RESULTS:
        errors.append("verification.result:invalid")
    elif result == "fail":
        blocks.append("verification_failed")
    elif result == "not_run" and authority != "reasoning_only":
        blocks.append("verification_not_run")

    topology = value.get("topology")
    runtimes = topology.get("runtimes") if isinstance(topology, dict) else None
    if isinstance(runtimes, dict) and runtimes.get("synchronized") is not True:
        blocks.append("runtime_sync_unverified")

    if errors:
        blocks.append("invalid_envelope")
    return sorted(set(errors)), sorted(set(blocks))


def _sample_envelope() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "skill": SKILL,
        "contract_version": VERSION,
        "observed_at": "2026-08-07T12:00:00Z",
        "worker": {"runtime": "test", "model": "fixture", "session": "fixture", "host": "test"},
        "scope": {"scale": "system", "task": "fixture", "systems": [], "nodes": [], "repos": [], "resources": []},
        "topology": {
            "ssh": {"source": "fixture", "observed": [], "reachable": []},
            "memory": {"sources": [], "freshness": "fresh"},
            "graphs": {"indexes": [], "freshness": "fresh"},
            "runtimes": {"skill_copies": [], "synchronized": True},
        },
        "candidate_reality": {
            "kind": "test",
            "source": "fixture",
            "predicted_outcome": "validation passes",
            "falsifier": "any validation error",
        },
        "live_reality": {"source": "fixture", "state_before": "old", "state_after": "new", "fresh": True},
        "bridge": {"verdict": "approve", "policy_version": VERSION, "obligations": [], "grant_scope": [], "expires_at": None},
        "execution": {"authority": "reasoning_only", "idempotency_key": "fixture", "changed_resources": []},
        "verification": {"source": "self-test", "checks": ["schema"], "result": "pass", "prediction_error": "none"},
        "learning": {"baseline": "v1.1", "memory_updates": [], "graph_updates": [], "promotion_stage": "proposal", "next_experiment": "none"},
        "uncertainty": [],
    }


def self_test() -> dict[str, Any]:
    assert context()["generalized_core"] == GENERALIZED_CORE
    assert validate_envelope(_sample_envelope()) == ([], [])
    stale = _sample_envelope()
    stale["live_reality"]["fresh"] = False
    assert "missing_or_stale_live_reality" in validate_envelope(stale)[1]
    assert _walk_forbidden({"summary": "hypothesis", "execute_now": True}) == ["execute_now"]
    return {
        "ok": True,
        "skill": SKILL,
        "contract_version": VERSION,
        "checks": [
            "ecosystem_identity",
            "candidate_live_boundary",
            "bounded_authority",
            "evidence_envelope",
            "model_output_rejection",
            "fail_closed_policy",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--emit-context", action="store_true")
    parser.add_argument("--validate-json", type=Path)
    parser.add_argument("--validate-model-json", type=Path)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.emit_context:
        print(json.dumps(context(), indent=2, sort_keys=True))
        return 0
    if args.validate_json:
        value = json.loads(args.validate_json.read_text(encoding="utf-8"))
        errors, blocks = validate_envelope(value)
        print(json.dumps({"ok": not errors and not blocks, "errors": errors, "blocks": blocks}, sort_keys=True))
        return 0 if not errors and not blocks else 1
    if args.validate_model_json:
        value = json.loads(args.validate_model_json.read_text(encoding="utf-8"))
        forbidden = _walk_forbidden(value)
        print(json.dumps({"ok": not forbidden, "forbidden_paths": forbidden}, sort_keys=True))
        return 0 if not forbidden else 1
    parser.error("choose --self-test, --emit-context, --validate-json, or --validate-model-json")
    return 2


if __name__ == "__main__":
    sys.exit(main())
