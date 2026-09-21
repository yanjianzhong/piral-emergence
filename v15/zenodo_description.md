# spiral-emergence: negative-control ledger pipeline

Companion code and data archive for the manuscript:

> **"A negative-control ledger for multi-stage numerical pipelines — demonstrated on Ising/MERA"**

This repository implements a negative-control discipline for validating multi-stage numerical pipelines. The method is demonstrated on a seven-layer computational stack built around a critical Ising chain and MERA (Multiscale Entanglement Renormalization Ansatz) tensor networks.

## What is included

- **`spiral_model_v15.py`** — Main pipeline script (Python 3). Constructs the seven-layer stack, runs all diagnostic checks, and writes audit tables.
- **`spiral_v15.tex` / `spiral_v15.bib`** — LaTeX source and bibliography of the manuscript.
- **`spiral_metric_v15_NEG_CTRL_TABLE`** — Full negative-control ledger (plain text / CSV), listing all 12 controls with layer, type, reachability status, and pass/fail outcome.
- **Runtime registry and completeness guard** — Scripts that cross-check the ledger against the live set of guards cited in the pipeline, detecting phantom references and missing layers.
- **Audit tables** — Per-layer diagnostic output, including the 20 diagnostic items (17 designed-to-fail exclusions) used in the coverage analysis.

## Key results reproduced by this code

| Layer | Negative control | Outcome |
|-------|-----------------|---------|
| L1 | Repulsion (5 controls) | All 5 reachable; 1 passed, 4 failed as designed |
| L2 | Two-path (5 controls) | All 5 reachable; 1 passed, 4 failed as designed |
| L3 | Null model (1 control) | Reachable; passed |
| L4 | Two-path (1 control) | Reachable; passed |
| L5 | Two-path (1 control) | Reachable; failed (geometry readout invariant under state) |
| L6 | Upper bound (1 control) | Reachable; passed |
| L7 | *(no control; layer empty)* | — |

Three negative results are reported as first-class findings: an inverted completeness criterion (Sec. 5.1), a fully wired but non-flowing bridge between L4 and L5 (Sec. 5.2), and a geometry readout that is an analytic property of wiring rather than an emergent feature (Sec. 5.3).

## Scope and limitations

The authors **do not** claim that:
- The seven-layer framework under study is an established physical theory.
- Any holographic bridge between layers 4 and 5 is demonstrated.
- The geometry readout in layer 5 carries physical meaning beyond the tensor-network wiring.

The contribution is methodological: a falsifiable discipline for negative controls in numerical pipelines, demonstrated on a concrete (and deliberately textbook-level) physics substrate.

## Repository history

This repository was renamed from `piral-emergence` to `spiral-emergence` to correct a spelling error. Earlier Zenodo snapshots under the old name are preserved at the legacy DOI and redirected automatically.

- **Current source:** https://github.com/yanjianzhong/spiral-emergence
- **Archived versions:** Zenodo concept DOI (see right panel)

## Requirements

- Python 3.8+
- NumPy, SciPy
- No external physics libraries required (MERA operations are implemented natively)