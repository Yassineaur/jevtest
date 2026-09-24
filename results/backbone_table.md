# Backbone pilot (T4 recipe, CEM v1, seed 0)

Rule pre-registered in MVP_PLAN.md: choose on TRAIN-HOLDOUT F1; dev and latency reported only.

| Backbone | Params | LR | holdout F1 | dev F1 | dev span F1 | top-1 hit | p50 ms (idle) | para/s bs32 |
|---|---|---|---|---|---|---|---|---|
| microsoft/deberta-v3-base | 184M | 2e-5 | 0.508 | 0.405 | 0.392 | 0.583 | 18.4 | 1264 |
| microsoft/deberta-v3-base **(chosen per backbone)** | 184M | 4e-5 | 0.524 | 0.394 | 0.359 | 0.577 | 18.5 | 1280 |
| answerdotai/ModernBERT-base | 149M | 3e-5 | 0.493 | 0.337 | 0.330 | 0.548 | - | - |
| answerdotai/ModernBERT-base **(chosen per backbone)** | 149M | 6e-5 | 0.496 | 0.348 | 0.357 | 0.537 | - | - |
| microsoft/deberta-v3-large | 434M | 1e-5 | 0.507 | 0.405 | 0.400 | 0.590 | 34.9 | 695 |
| microsoft/deberta-v3-large **(chosen per backbone)** | 434M | 2e-5 | 0.524 | 0.372 | 0.363 | 0.539 | 34.8 | 704 |

Selected by the rule: **microsoft/deberta-v3-base at lr 4e-5** (holdout 0.524).
