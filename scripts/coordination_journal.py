#!/usr/bin/env python3
"""Append and inspect bounded DRGB ecosystem coordination events."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SKILL = "drgb-core"
VERSION = "drgb-core.v2.0"
STATE_ROOT = Path(os.environ.get("DRGB_STATE_DIR", str(Path.home() / ".drgb"))).expanduser()
DEFAULT_JOURNAL = STATE_ROOT / "coordination" / "events.jsonl"
DEFAULT_SECOND_BRAIN = STATE_ROOT / "second-brain"
EVENTS = {"claim", "heartbeat", "handoff", "blocked", "complete"}
AUTHORITIES = {"reasoning_only", "bounded_write", "authenticated_gate"}
RESULTS = {"pass", "fail", "not_run"}
VERDICTS = {"approve", "modify", "defer", "reject", "escalate", "data_unavailable", "blocked"}


def _append(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        with path.open("a", encoding="utf-8") as journal:
            journal.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
            journal.flush()
            os.fsync(journal.fileno())
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _read(path: Path, limit: int) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events[-limit:]


def _merge(path: Path, source: Path) -> list[dict]:
    """Merge event journals by event ID under the destination lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        existing = _read(path, 1_000_000)
        incoming = _read(source, 1_000_000)
        merged: dict[str, dict] = {}
        for event in (*existing, *incoming):
            key = str(event.get("event_id") or _event_id(event))
            merged[key] = event
        ordered = sorted(
            merged.values(),
            key=lambda event: (str(event.get("observed_at", "")), str(event.get("event_id", ""))),
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            for event in ordered:
                stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            temp_path = Path(stream.name)
        os.replace(temp_path, path)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return ordered


def _event_id(event: dict) -> str:
    payload = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
    return "drgb-" + hashlib.sha256(payload).hexdigest()[:20]


def _cell(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}:" + hashlib.sha256(value.encode()).hexdigest()[:20]


def _write_subgraph(events: list[dict], root: Path, generated_at: str) -> dict:
    """Write a portable provenance graph directly from coordination events."""
    nodes: dict[str, dict] = {}
    links: list[dict] = []
    seen_links: set[tuple[str, str, str]] = set()

    def add_node(node_id: str, **attrs: object) -> None:
        nodes.setdefault(node_id, {"id": node_id, **attrs})

    def add_link(source: str, target: str, relationship: str) -> None:
        key = (source, target, relationship)
        if key not in seen_links:
            seen_links.add(key)
            links.append({"source": source, "target": target, "relationship": relationship})

    for event in events:
        event_id = str(event.get("event_id") or _event_id(event))
        task = str(event.get("scope", {}).get("task") or "unknown")
        worker = event.get("worker", {})
        worker_label = ":".join(
            str(worker.get(key) or "unknown") for key in ("host", "runtime", "model")
        )
        task_id = _stable_id("task", task)
        worker_id = _stable_id("worker", worker_label)
        add_node(
            event_id,
            label=str(event.get("event") or "event"),
            kind="coordination_event",
            observed_at=str(event.get("observed_at") or ""),
            bridge_verdict=str(event.get("bridge", {}).get("verdict") or ""),
            provenance="coordination_journal",
        )
        add_node(task_id, label=task, kind="task", provenance="coordination_journal")
        add_node(worker_id, label=worker_label, kind="worker", provenance="coordination_journal")
        add_link(event_id, task_id, "BELONGS_TO")
        add_link(worker_id, event_id, "EMITTED")
        parent = str(event.get("parent_event_id") or "")
        if parent:
            add_node(parent, label="parent event", kind="coordination_event", provenance="coordination_journal")
            add_link(event_id, parent, "FOLLOWS")
        resources = event.get("scope", {}).get("resources", [])
        for resource in resources if isinstance(resources, list) else []:
            resource_label = str(resource)
            resource_id = _stable_id("resource", resource_label)
            add_node(resource_id, label=resource_label, kind="resource", provenance="coordination_journal")
            add_link(event_id, resource_id, "SCOPES")

    payload = {
        "schema_version": 1,
        "contract_version": VERSION,
        "generated_at": generated_at,
        "directed": True,
        "multigraph": False,
        "nodes": sorted(nodes.values(), key=lambda node: node["id"]),
        "links": sorted(links, key=lambda link: (link["source"], link["target"], link["relationship"])),
        "provenance": "deterministic_coordination_journal_projection",
        "authority": "evidence_only",
    }
    path = root / "drgb-subgraph.json"
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp, path)
    return payload


def _write_second_brain(events: list[dict], root: Path, journal: Path) -> None:
    """Materialize deterministic swarm memory without granting authority."""
    root.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    latest_by_task: dict[str, dict] = {}
    workers: set[str] = set()
    for event in events:
        task = str(event.get("scope", {}).get("task") or "unknown")
        latest_by_task[task] = event
        worker = event.get("worker", {})
        workers.add(f"{worker.get('runtime', 'unknown')}:{worker.get('model', 'unknown')}")

    lines = [
        "# DRGB Swarm Second Brain",
        "",
        f"Generated: {generated_at}",
        f"Contract: {VERSION}",
        f"Authoritative coordination journal: {journal}",
        "",
        "## Architecture",
        "",
        "DRGB is the governing architecture. SGAM is the domain-neutral swarm control plane built inside DRGB. The Second Brain is the provenance-preserving evidence and memory layer. Each worker, task, team, domain, and system is a bounded DRGB cell. Neither SGAM, memory, graphs, nor model consensus grants live authority.",
        "",
        "## Swarm status",
        "",
        f"- Events: {len(events)}",
        f"- Tasks: {len(latest_by_task)}",
        f"- Workers: {', '.join(sorted(workers)) or 'none'}",
        "",
        "| Observed | Worker | Scale | State | Task | Bridge | Verification | Next safe action |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for task, event in list(latest_by_task.items())[-100:]:
        worker = event.get("worker", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(event.get("observed_at")),
                    _cell(f"{worker.get('runtime', 'unknown')}:{worker.get('model', 'unknown')}"),
                    _cell(event.get("scope", {}).get("scale")),
                    _cell(event.get("event")),
                    _cell(task),
                    _cell(event.get("bridge", {}).get("verdict")),
                    _cell(event.get("verification", {}).get("result")),
                    _cell(event.get("next_safe_action")),
                ]
            )
            + " |"
        )

    context_path = root / "DRGB_SWARM_CONTEXT.md"
    context_temp = context_path.with_suffix(".md.tmp")
    context_temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(context_temp, context_path)

    subgraph = _write_subgraph(events, root, generated_at)

    journal_bytes = journal.read_bytes() if journal.exists() else b""
    manifest = {
        "schema_version": 1,
        "contract_version": VERSION,
        "generated_at": generated_at,
        "journal": str(journal),
        "journal_sha256": hashlib.sha256(journal_bytes).hexdigest(),
        "events": len(events),
        "tasks": len(latest_by_task),
        "workers": sorted(workers),
        "subgraph": "drgb-subgraph.json",
        "subgraph_nodes": len(subgraph["nodes"]),
        "subgraph_edges": len(subgraph["links"]),
        "authority": "memory_evidence_only",
    }
    manifest_path = root / "manifest.json"
    manifest_temp = manifest_path.with_suffix(".json.tmp")
    manifest_temp.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(manifest_temp, manifest_path)

    graph_root = root / "graphify-out"
    if (graph_root / "graph.json").exists():
        (graph_root / "needs_update").write_text(generated_at + "\n", encoding="utf-8")


def _event(args: argparse.Namespace) -> dict:
    event = {
        "schema_version": 2,
        "skill": SKILL,
        "contract_version": VERSION,
        "event": args.event,
        "correlation_id": args.correlation_id,
        "parent_event_id": args.parent_event_id,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "worker": {
            "runtime": args.runtime,
            "model": args.model,
            "session": args.session,
            "host": args.host or socket.gethostname(),
        },
        "scope": {
            "scale": args.scale,
            "task": args.task,
            "repo": args.repo,
            "worktree": args.worktree,
            "resources": args.path,
        },
        "base_state": {"branch": args.branch, "commit": args.base_commit},
        "candidate_reality": {
            "kind": args.candidate_kind,
            "predicted_outcome": args.predicted_outcome,
            "falsifier": args.falsifier,
        },
        "bridge": {"verdict": args.bridge_verdict, "obligations": args.obligation},
        "result_state": {"commit": args.result_commit, "changed_resources": args.changed_path},
        "verification": {
            "checks": args.check,
            "result": args.verification_result,
            "prediction_error": args.prediction_error,
        },
        "learning": {"memory_updates": args.memory_update, "graph_updates": args.graph_update},
        "authority": args.authority,
        "uncertainty": args.uncertainty,
        "next_safe_action": args.next_safe_action,
    }
    event["event_id"] = _event_id(event)
    return event


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "events.jsonl"
        sample = {
            "schema_version": 2,
            "skill": SKILL,
            "contract_version": VERSION,
            "event": "claim",
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        sample["event_id"] = _event_id(sample)
        _append(path, sample)
        assert _read(path, 1) == [sample]
        assert sample["event_id"].startswith("drgb-")
        source = Path(temp_dir) / "incoming.jsonl"
        _append(source, sample)
        second = dict(sample)
        second["observed_at"] = datetime.now(timezone.utc).isoformat()
        second["event"] = "complete"
        second["event_id"] = _event_id(second)
        _append(source, second)
        assert len(_merge(path, source)) == 2
        second_brain = Path(temp_dir) / "second-brain"
        _write_second_brain(_read(path, 10), second_brain, path)
        context = (second_brain / "DRGB_SWARM_CONTEXT.md").read_text(encoding="utf-8")
        assert "SGAM is the domain-neutral swarm control plane" in context
        manifest = json.loads((second_brain / "manifest.json").read_text(encoding="utf-8"))
        subgraph = json.loads((second_brain / "drgb-subgraph.json").read_text(encoding="utf-8"))
        assert manifest["events"] == 2
        assert manifest["subgraph_nodes"] == len(subgraph["nodes"])
        assert len(subgraph["links"]) >= 4
    print(json.dumps({"ok": True, "checks": ["coordination_journal", "journal_merge", "second_brain_sync", "coordination_subgraph"], "contract_version": VERSION}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--second-brain", type=Path, default=DEFAULT_SECOND_BRAIN)
    parser.add_argument("--self-test", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    record = subparsers.add_parser("record")
    record.add_argument("--event", required=True, choices=sorted(EVENTS))
    record.add_argument("--correlation-id", default="")
    record.add_argument("--parent-event-id", default="")
    record.add_argument("--runtime", default="codex")
    record.add_argument("--model", default="unknown")
    record.add_argument("--session", default="unknown")
    record.add_argument("--host", default="")
    record.add_argument("--scale", choices=("action", "agent", "team", "system"), default="action")
    record.add_argument("--task", required=True)
    record.add_argument("--repo", default="")
    record.add_argument("--worktree", default="")
    record.add_argument("--path", action="append", default=[])
    record.add_argument("--branch", default="")
    record.add_argument("--base-commit", default="")
    record.add_argument("--candidate-kind", default="")
    record.add_argument("--predicted-outcome", default="")
    record.add_argument("--falsifier", default="")
    record.add_argument("--bridge-verdict", choices=sorted(VERDICTS), default="data_unavailable")
    record.add_argument("--obligation", action="append", default=[])
    record.add_argument("--result-commit", default="")
    record.add_argument("--changed-path", action="append", default=[])
    record.add_argument("--check", action="append", default=[])
    record.add_argument("--verification-result", choices=sorted(RESULTS), default="not_run")
    record.add_argument("--prediction-error", default="")
    record.add_argument("--memory-update", action="append", default=[])
    record.add_argument("--graph-update", action="append", default=[])
    record.add_argument("--authority", choices=sorted(AUTHORITIES), default="reasoning_only")
    record.add_argument("--uncertainty", action="append", default=[])
    record.add_argument("--next-safe-action", default="")

    status = subparsers.add_parser("status")
    status.add_argument("--limit", type=int, default=20)
    merge = subparsers.add_parser("merge")
    merge.add_argument("--source", type=Path, required=True)
    subparsers.add_parser("sync")

    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    if args.command == "record":
        event = _event(args)
        _append(args.journal, event)
        _write_second_brain(_read(args.journal, 100000), args.second_brain, args.journal)
        print(json.dumps(event, indent=2, sort_keys=True))
        return 0
    if args.command == "status":
        print(json.dumps(_read(args.journal, args.limit), indent=2, sort_keys=True))
        return 0
    if args.command == "merge":
        events = _merge(args.journal, args.source)
        _write_second_brain(events, args.second_brain, args.journal)
        print(json.dumps({"events": len(events), "journal": str(args.journal)}, sort_keys=True))
        return 0
    if args.command == "sync":
        events = _read(args.journal, 100000)
        _write_second_brain(events, args.second_brain, args.journal)
        print(json.dumps({"events": len(events), "second_brain": str(args.second_brain)}, sort_keys=True))
        return 0
    parser.error("choose record, status, merge, or sync, or use --self-test")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
