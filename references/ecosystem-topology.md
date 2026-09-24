# DRGB ecosystem topology

## Discovery order

1. Read active coordination claims and global agent policy.
2. Read repository guidance and query codebase-memory or an existing Graphify graph.
3. Read SGAM fleet and memory-source configuration when present.
4. Inventory local agent runtime skill directories and versions.
5. Inventory second-brain paths and graph/subgraph artifacts without reading secrets.
6. Enumerate explicit SSH aliases. Probe only aliases explicitly selected for the task.
7. Query authoritative services or external systems only when needed and authorized.

## Evidence classes

- `AUTHORITATIVE_LIVE`: authenticated current system-of-record or runtime state.
- `AUTHORITATIVE_SOURCE`: checked source plus revision/worktree state.
- `DEPLOYED_SNAPSHOT`: deployed files without source revision provenance.
- `COORDINATION_EVENT`: append-only claim or handoff; ownership evidence only.
- `MEMORY_SOURCE`: second-brain content with source, timestamp, and update mechanism.
- `GRAPH_EXTRACTED`: graph node/edge deterministically extracted from a source.
- `GRAPH_INFERRED`: graph relationship inferred from sources; requires verification.
- `MODEL_HYPOTHESIS`: unverified interpretation; never authority.
- `DATA_UNAVAILABLE`: source missing, stale, unreachable, or not authorized.

## SSH and node rules

- Derive nodes from explicit SSH `Host` aliases or an owning fleet inventory.
- Never scan address ranges, scrape keys, print credentials, or infer permission from reachability.
- Default to `BatchMode=yes`, a short connection timeout, and a read-only identity probe.
- Record alias, resolved host label when safely available, reachability, observed-at time, and error class without secret-bearing stderr.
- Remote writes, service changes, deployments, and sync jobs require the target system's normal gate and a rollback path.

## Second-brain rules

- Inventory path, kind, scope, owning update mechanism, latest source timestamp, and stale marker.
- Treat shared brain, local memories, team notes, project memory, and event journals as distinct provenance classes.
- Use the owner's sync or intake mechanism. Do not directly merge contradictory memories or overwrite compiled context.
- Promote only verified outcomes; retain links to claims, source artifacts, revisions, and falsifiers.

## Graph and subgraph rules

- Prefer codebase-memory MCP for indexed code and Graphify for persistent cross-document graphs.
- Track graph root, manifest, graph artifact, node/edge counts when cheap, last modified time, and `.needs_update` or equivalent stale markers.
- Query first; refresh only through the existing planner or explicit update workflow.
- Never claim that a graph is current solely because `graph.json` exists.
- Treat `~/.drgb/second-brain/drgb-subgraph.json` as the portable deterministic coordination projection. Regenerate it after every journal record or merge; it remains evidence-only.
- Preserve `EXTRACTED`, `INFERRED`, and `AMBIGUOUS` provenance and verify inferred edges before consequential use.
- Publish task-scoped evidence as references or events; do not create disconnected shadow knowledge stores.

## Synchronization proof

For skill/runtime propagation, require the same contract version, relative file
manifest or an explicit canonical-runtime bridge, file checksums, self-test
result, and observed-at time at each runtime. Merge append-only coordination
journals by event ID; never replace a node's independent events wholesale.
For memory/graph synchronization, require the owning sync result plus source and
destination freshness. If any component cannot be verified, report partial
synchronization and name the missing proof.
