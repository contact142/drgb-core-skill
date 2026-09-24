#!/usr/bin/env python3
"""Synchronize DRGB skill and append-only coordination state across explicit SSH nodes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

SKILL = "drgb-core"
VERSION = "drgb-core.v2.0"
SAFE_HOST = re.compile(r"^[A-Za-z0-9_.:@-]+$")
SAFE_REMOTE_PATH = re.compile(r"^/[A-Za-z0-9_./-]+$")
DEFAULT_SKILL = Path.home() / ".codex" / "skills" / SKILL
DEFAULT_JOURNAL = Path.home() / ".drgb" / "coordination" / "events.jsonl"
DEFAULT_SECOND_BRAIN = Path.home() / ".drgb" / "second-brain"
REMOTE_RUNTIME_ROOTS = (".codex/skills", ".claude/skills", ".agents/skills", ".hermes/skills")


def _run(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


def _validate(host: str, remote_home: str) -> None:
    if not SAFE_HOST.fullmatch(host):
        raise ValueError("invalid SSH host alias")
    if remote_home == "/" or not SAFE_REMOTE_PATH.fullmatch(remote_home):
        raise ValueError("invalid remote home")


def _ssh(host: str, remote_command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return _run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, remote_command],
        timeout=timeout,
    )


def _remote_paths(remote_home: str) -> dict[str, str]:
    skill = f"{remote_home}/.codex/skills/{SKILL}"
    return {
        "skill": skill,
        "probe": f"{skill}/scripts/ecosystem_probe.py",
        "journal_tool": f"{skill}/scripts/coordination_journal.py",
        "journal": f"{remote_home}/.drgb/coordination/events.jsonl",
        "second_brain": f"{remote_home}/.drgb/second-brain",
    }


def status(host: str, remote_home: str) -> dict[str, Any]:
    _validate(host, remote_home)
    paths = _remote_paths(remote_home)
    command = (
        f"python3 {shlex.quote(paths['probe'])} --home {shlex.quote(remote_home)}"
        if paths
        else "false"
    )
    completed = _ssh(host, command)
    if completed.returncode != 0:
        return {"host": host, "reachable": False, "error": "probe_failed"}
    try:
        manifest = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"host": host, "reachable": True, "error": "invalid_probe_output"}
    return {
        "host": host,
        "reachable": True,
        "remote_hostname": manifest.get("host", {}).get("hostname", "unknown"),
        "contract_version": manifest.get("contract_version", "unknown"),
        "runtime_sync": manifest.get("runtime_sync", {}),
        "memory": [item for item in manifest.get("memory", []) if item.get("exists")],
        "graphs": [item for item in manifest.get("graphs", []) if item.get("exists")],
    }


def sync_package(host: str, remote_home: str, local_skill: Path) -> dict[str, Any]:
    _validate(host, remote_home)
    if not (local_skill / "SKILL.md").exists():
        return {"host": host, "ok": False, "error": "local_skill_missing"}
    token = hashlib.sha256(f"{host}:{VERSION}".encode()).hexdigest()[:12]
    remote_temp = f"/tmp/drgb-core-{token}"
    uploaded = _run(
        [
            "rsync",
            "-az",
            "--exclude",
            "__pycache__",
            str(local_skill) + "/",
            f"{host}:{remote_temp}/",
        ],
        timeout=60,
    )
    if uploaded.returncode != 0:
        return {"host": host, "ok": False, "error": "package_upload_failed"}
    destinations = [f"{remote_home}/{root}/{SKILL}" for root in REMOTE_RUNTIME_ROOTS]
    parts = ["set -eu"]
    for destination in destinations:
        parts.append(f"mkdir -p {shlex.quote(destination)}")
        parts.append(
            f"rsync -a --exclude __pycache__ {shlex.quote(remote_temp + '/')} {shlex.quote(destination + '/')}"
        )
        parts.append(f"python3 {shlex.quote(destination + '/scripts/probe_drgb_core.py')} --self-test >/dev/null")
    parts.append(
        "python3 -c "
        + shlex.quote(
            "from pathlib import Path; import shutil; "
            f"shutil.rmtree(Path({remote_temp!r}), ignore_errors=True)"
        )
    )
    completed = _ssh(host, "; ".join(parts), timeout=90)
    return {"host": host, "ok": completed.returncode == 0, "error": "" if completed.returncode == 0 else "package_install_failed"}


def sync_journal(
    host: str,
    remote_home: str,
    local_journal: Path,
    local_second_brain: Path,
    local_tool: Path,
) -> dict[str, Any]:
    _validate(host, remote_home)
    paths = _remote_paths(remote_home)
    local_journal.parent.mkdir(parents=True, exist_ok=True)
    local_journal.touch(exist_ok=True)
    token = hashlib.sha256(f"{host}:{local_journal}".encode()).hexdigest()[:12]
    remote_temp = f"/tmp/drgb-events-{token}.jsonl"
    with tempfile.TemporaryDirectory() as temp_dir:
        remote_copy = Path(temp_dir) / "remote-events.jsonl"
        exists = _ssh(host, f"test -f {shlex.quote(paths['journal'])}")
        if exists.returncode == 0:
            pulled = _run(["scp", "-q", f"{host}:{paths['journal']}", str(remote_copy)], timeout=30)
            if pulled.returncode != 0:
                return {"host": host, "ok": False, "error": "journal_pull_failed"}
        else:
            remote_copy.write_text("", encoding="utf-8")
        merged_local = _run(
            [
                "python3",
                str(local_tool),
                "--journal",
                str(local_journal),
                "--second-brain",
                str(local_second_brain),
                "merge",
                "--source",
                str(remote_copy),
            ]
        )
        if merged_local.returncode != 0:
            return {"host": host, "ok": False, "error": "local_merge_failed"}
        pushed = _run(["scp", "-q", str(local_journal), f"{host}:{remote_temp}"], timeout=30)
        if pushed.returncode != 0:
            return {"host": host, "ok": False, "error": "journal_push_failed"}
        remote_command = "; ".join(
            [
                "set -eu",
                f"python3 {shlex.quote(paths['journal_tool'])} --journal {shlex.quote(paths['journal'])} "
                f"--second-brain {shlex.quote(paths['second_brain'])} merge --source {shlex.quote(remote_temp)}",
                "python3 -c "
                + shlex.quote(f"from pathlib import Path; Path({remote_temp!r}).unlink(missing_ok=True)"),
            ]
        )
        merged_remote = _ssh(host, remote_command, timeout=60)
        if merged_remote.returncode != 0:
            return {"host": host, "ok": False, "error": "remote_merge_failed"}
    return {"host": host, "ok": True, "error": ""}


def _self_test() -> int:
    _validate("safe-host", "/root")
    try:
        _validate("unsafe host", "/root")
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe host accepted")
    try:
        _validate("safe-host", "/")
    except ValueError:
        pass
    else:
        raise AssertionError("root path accepted")
    print(json.dumps({"ok": True, "check": "fleet_sync_safety", "contract_version": VERSION}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", action="append", default=[])
    parser.add_argument("--remote-home", default="/root")
    parser.add_argument("--local-skill", type=Path, default=DEFAULT_SKILL)
    parser.add_argument("--local-journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--local-second-brain", type=Path, default=DEFAULT_SECOND_BRAIN)
    parser.add_argument("--sync-package", action="store_true")
    parser.add_argument("--sync-journal", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    if not args.host:
        parser.error("provide at least one explicit --host")
    if (args.sync_package or args.sync_journal) and not args.apply:
        print(
            json.dumps(
                {
                    "ok": False,
                    "mode": "dry_run",
                    "hosts": args.host,
                    "planned": {
                        "sync_package": args.sync_package,
                        "sync_journal": args.sync_journal,
                    },
                    "reason": "add --apply to mutate explicit hosts",
                },
                indent=2,
            )
        )
        return 0
    results = []
    for host in args.host:
        host_result: dict[str, Any] = {"host": host}
        if args.sync_package:
            host_result["package"] = sync_package(host, args.remote_home, args.local_skill)
        if args.sync_journal:
            host_result["journal"] = sync_journal(
                host,
                args.remote_home,
                args.local_journal,
                args.local_second_brain,
                args.local_skill / "scripts" / "coordination_journal.py",
            )
        host_result["status"] = status(host, args.remote_home)
        results.append(host_result)
    ok = all(
        all(section.get("ok", True) for name, section in item.items() if name in {"package", "journal"})
        and item["status"].get("reachable")
        for item in results
    )
    print(json.dumps({"ok": ok, "contract_version": VERSION, "results": results}, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
