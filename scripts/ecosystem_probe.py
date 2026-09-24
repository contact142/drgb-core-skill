#!/usr/bin/env python3
"""Read-only DRGB ecosystem discovery for runtimes, memory, graphs, and SSH aliases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL = "drgb-core"
VERSION = "drgb-core.v2.0"
SAFE_SSH_HOST = re.compile(r"^[A-Za-z0-9_.:@-]+$")
RUNTIME_SKILL_ROOTS = (
    ".codex/skills",
    ".claude/skills",
    ".agents/skills",
    ".hermes/skills",
)
MEMORY_CANDIDATES = (
    ".drgb/coordination/events.jsonl",
    ".drgb/second-brain",
    ".hermes-shared",
    ".hermes/memories",
    ".hermes/team-brain",
    ".hermes/incoming-from-vps-hermes",
    ".hermes-memory-corpus",
    "graphify-fleet-brain",
)
GRAPH_CANDIDATES = (
    ".drgb/second-brain/drgb-subgraph.json",
    ".hermes-memory-corpus/graphify-out/graph.json",
    ".hermes/graphify-out/graph.json",
    ".hermes/graphify/unified-graph.json",
    "graphify-fleet-brain/graph.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_record(path: Path, kind: str, fresh_hours: float = 24.0) -> dict[str, Any]:
    record: dict[str, Any] = {"kind": kind, "path": str(path), "exists": path.exists()}
    if not path.exists():
        record["freshness"] = "unknown"
        return record
    stat = path.stat()
    observed_timestamp = stat.st_mtime
    freshness_basis = "filesystem_mtime"
    manifest_path = path / "manifest.json" if path.is_dir() else None
    if manifest_path and manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            generated_at = datetime.fromisoformat(str(manifest.get("generated_at", "")).replace("Z", "+00:00"))
            if generated_at.tzinfo is not None:
                observed_timestamp = generated_at.timestamp()
                freshness_basis = "manifest.generated_at"
                record["manifest_contract_version"] = manifest.get("contract_version", "unknown")
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    record.update(
        {
            "type": "directory" if path.is_dir() else "file",
            "modified_at": datetime.fromtimestamp(observed_timestamp, timezone.utc).isoformat(),
            "size_bytes": stat.st_size,
        }
    )
    stale_markers = []
    marker_roots = [path] if path.is_dir() else [path.parent]
    for root in marker_roots:
        for name in (".needs_update", "needs_update", ".stale"):
            marker = root / name
            if marker.exists():
                stale_markers.append(str(marker))
    record["stale_markers"] = stale_markers
    age_hours = max(0.0, (datetime.now(timezone.utc).timestamp() - observed_timestamp) / 3600.0)
    record["age_hours"] = round(age_hours, 3)
    record["freshness_basis"] = freshness_basis
    record["freshness"] = "stale" if stale_markers or age_hours > fresh_hours else "fresh"
    if kind == "graph_or_subgraph" and path.is_file() and path.suffix == ".json" and stat.st_size <= 20_000_000:
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
            record["node_count"] = len(graph.get("nodes", []))
            record["edge_count"] = len(graph.get("links", graph.get("edges", [])))
        except (OSError, json.JSONDecodeError):
            record["graph_shape"] = "unreadable"
    return record


def _skill_manifest(skill_dir: Path, fresh_hours: float = 24.0) -> dict[str, Any]:
    record = _path_record(skill_dir, "agent_skill", fresh_hours)
    if not skill_dir.is_dir():
        return record
    files = []
    for path in sorted(skill_dir.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            files.append(
                {
                    "path": str(path.relative_to(skill_dir)),
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    detected_version = "unknown"
    canonical_target = ""
    probe_path = skill_dir / "scripts" / "probe_drgb_core.py"
    if probe_path.exists():
        match = re.search(
            r'^VERSION\s*=\s*["\']([^"\']+)["\']',
            probe_path.read_text(encoding="utf-8", errors="replace"),
            re.MULTILINE,
        )
        if match:
            detected_version = match.group(1)
    if detected_version == "unknown":
        for candidate in (skill_dir / "SKILL.md", skill_dir / "references" / "contract.md", probe_path):
            if not candidate.exists():
                continue
            match = re.search(r"drgb-core\.v\d+(?:\.\d+)*", candidate.read_text(encoding="utf-8", errors="replace"))
            if match:
                detected_version = match.group(0)
                break
    skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    target_match = re.search(r"(/[A-Za-z0-9_.@/ -]+/\.codex/skills/drgb-core)(?:/SKILL\.md)?", skill_text)
    if target_match:
        canonical_target = target_match.group(1)
    record["contract_version"] = detected_version
    record["canonical_target"] = canonical_target
    record["files"] = files
    record["manifest_sha256"] = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return record


def _ssh_aliases(config_path: Path) -> list[str]:
    if not config_path.exists():
        return []
    aliases: set[str] = set()
    for raw_line in config_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts and parts[0].lower() == "host":
            for alias in parts[1:]:
                if not any(char in alias for char in "*?!") and SAFE_SSH_HOST.fullmatch(alias):
                    aliases.add(alias)
    return sorted(aliases)


def _probe_ssh(alias: str, timeout_seconds: int) -> dict[str, Any]:
    if not SAFE_SSH_HOST.fullmatch(alias):
        return {"alias": alias, "reachable": False, "error": "invalid_alias"}
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={timeout_seconds}",
        alias,
        "printf '%s' \"${HOSTNAME:-unknown}\"",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds + 2)
    except (OSError, subprocess.TimeoutExpired):
        return {"alias": alias, "reachable": False, "error": "connection_failed"}
    if completed.returncode != 0:
        return {"alias": alias, "reachable": False, "error": "connection_failed"}
    return {"alias": alias, "reachable": True, "remote_host": completed.stdout.strip()[:128]}


def _configured_memory_paths(config: Path) -> list[Path]:
    """Extract path scalars from SGAM memory YAML without requiring PyYAML."""
    if not config.exists():
        return []
    paths: list[Path] = []
    for raw_line in config.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^\s+path:\s*(.+?)\s*$", raw_line)
        if not match:
            continue
        value = match.group(1).strip().strip("'\"")
        if value and not value.startswith(("http://", "https://")):
            paths.append(Path(os.path.expandvars(value)).expanduser())
    return paths


def build_manifest(
    home: Path,
    projects: list[Path],
    ssh_hosts: list[str],
    timeout: int,
    fresh_hours: float = 24.0,
) -> dict[str, Any]:
    runtime_records = [_skill_manifest(home / root / SKILL, fresh_hours) for root in RUNTIME_SKILL_ROOTS]
    present_runtimes = [record for record in runtime_records if record.get("exists")]
    runtime_versions = sorted({record.get("contract_version", "unknown") for record in present_runtimes})
    runtime_manifests = sorted({record.get("manifest_sha256", "") for record in present_runtimes})
    canonical = next(
        (record for record in present_runtimes if "/.codex/skills/" in record.get("path", "")),
        present_runtimes[0] if present_runtimes else None,
    )
    canonical_path = canonical.get("path", "") if canonical else ""
    canonical_manifest = canonical.get("manifest_sha256", "") if canonical else ""
    synchronized_copies = [
        record
        for record in present_runtimes
        if record.get("contract_version") == VERSION
        and (
            record.get("manifest_sha256") == canonical_manifest
            or record.get("canonical_target") == canonical_path
        )
    ]
    memory_paths = {home / value for value in MEMORY_CANDIDATES}
    graph_paths = {home / value for value in GRAPH_CANDIDATES}
    for project in projects:
        memory_paths.update(_configured_memory_paths(project / "config" / "memory_sources.yaml"))
        graph_paths.update(
            {
                project / "graphify-out" / "graph.json",
                project / ".codebase-memory" / "graph.db.zst",
            }
        )
    for memory_path in memory_paths:
        graph_paths.add(
            memory_path / "graph.json"
            if memory_path.name == "graphify-out"
            else memory_path / "graphify-out" / "graph.json"
        )
    aliases = _ssh_aliases(home / ".ssh" / "config")
    requested = sorted(set(ssh_hosts))
    return {
        "schema_version": 2,
        "skill": SKILL,
        "contract_version": VERSION,
        "observed_at": _utc_now(),
        "host": {"hostname": socket.gethostname(), "home": str(home)},
        "runtimes": runtime_records,
        "runtime_sync": {
            "synchronized": bool(present_runtimes) and len(synchronized_copies) == len(present_runtimes),
            "sync_mode": "canonical_or_identical_manifest",
            "canonical_path": canonical_path,
            "synchronized_copies": len(synchronized_copies),
            "present_copies": len(present_runtimes),
            "versions": runtime_versions,
            "manifests": runtime_manifests,
        },
        "memory": [_path_record(path, "memory_source", fresh_hours) for path in sorted(memory_paths)],
        "graphs": [_path_record(path, "graph_or_subgraph", fresh_hours) for path in sorted(graph_paths)],
        "ssh": {
            "config": str(home / ".ssh" / "config"),
            "aliases": aliases,
            "probed": [_probe_ssh(alias, timeout) for alias in requested],
            "probe_policy": "explicit_hosts_only",
        },
        "projects": [str(path) for path in projects],
        "authority": "read_only_discovery",
    }


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        temp_path = Path(stream.name)
    temp_path.replace(path)


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        home = Path(temp_dir)
        skill = home / ".codex" / "skills" / SKILL
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("test", encoding="utf-8")
        ssh = home / ".ssh"
        ssh.mkdir()
        (ssh / "config").write_text("Host safe-alias\nHost *.invalid\n", encoding="utf-8")
        manifest = build_manifest(home, [], [], 1)
        assert manifest["ssh"]["aliases"] == ["safe-alias"]
        assert manifest["runtimes"][0]["files"][0]["path"] == "SKILL.md"
        assert manifest["runtime_sync"]["synchronized"] is False
        assert manifest["ssh"]["probed"] == []
    print(json.dumps({"ok": True, "check": "ecosystem_probe", "contract_version": VERSION}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--project", type=Path, action="append", default=[])
    parser.add_argument("--ssh-host", action="append", default=[])
    parser.add_argument("--ssh-timeout", type=int, default=5)
    parser.add_argument("--fresh-hours", type=float, default=24.0)
    parser.add_argument("--write-manifest", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    manifest = build_manifest(
        args.home.expanduser(), args.project, args.ssh_host, args.ssh_timeout, args.fresh_hours
    )
    if args.write_manifest:
        _atomic_write(args.write_manifest.expanduser(), manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
