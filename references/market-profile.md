# Prometheus market DRGB profile

This is a domain profile, not the ecosystem core.

The verified deployment implementation uses
`prometheus.drgb.bridge.GuardianBridge` at
`prometheus/src/prometheus/drgb/bridge.py`. It compares `RealityStreamA` market
state with `RealityStreamB` strategy consensus and may blend observational
`RealityStreamC`. It emits convergence, divergence, tension, and
`SAFE|CAUTION|DANGER|OPPORTUNITY` using runtime-configured thresholds.

For market R&D, preserve exact source paths, timestamps, symbol/account scope,
thresholds, costs, baseline strategy, and falsifier. Use causal splits and
after-cost attribution. `OPPORTUNITY` is evidence, not permission. Missing,
stale, `DANGER`, configured high tension, or an invalid execution grant blocks a
DRGB-enabled live path.

The previously observed V5 reader can return neutral multipliers for `NO_DATA`.
Treat that as advisory availability behavior only. Until the execution boundary
independently rejects `NO_DATA`, stale data, `DANGER`, and high tension, report
the live DRGB-enabled path as `BLOCKED`.
