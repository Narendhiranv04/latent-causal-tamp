# 0034 — P9-L3c-0: factor ontology, catalogue transformations under the deployed selector, query identity

**Actual result.** Gate: `runs/p9/l3c/L3C_0_GATE.json` → **PASS** (12/12). No new training; no teacher, IK, collision or planner call (instrumented: 0 calls into the 10 physical-checking modules).

**The remaining role sensitivity of `ABC9U_UNIQUE_V1` is a factor-instantiation effect, not a physical relation.**
- In the unique model, a scene–query relation and a higher-order hyperedge are instantiated **per listed parent candidate and slot role**. In validation root `p8_2026102504`, the single physical relation "scene bit × outcome of `o00>61`" exists as **16** scene–query pair instances (4 parent blocks × 4 scene bits), each with a different parent context `g_r` or role embedding.
- Promoting a modelled one-move omission to a standalone candidate decomposes exactly as follows:

  | added part | B-full | C-full |
  |---|---|---|
  | the query's unary | **0** | **0** |
  | new role-specific scene–query pairs alone | ≤ 0.044 | ≤ 0.301 |
  | new higher-order block alone | ≤ 0.029 | ≤ 0.012 |
  | omission links | 0 (none exist for a one-move query) | 0 |

**Other findings:**
- **Exact invariances hold for the unique model:** duplicate, permutation, renamed IDs and disconnected candidates all ≤ 1.4e-14 in priors, existing-label evidence and offline posteriors.
- **The full deployed selector never switches between pre-existing candidates** in those cases.
- **A conflicting ID fails closed** in the new wrapper. `unique_factor.instances` *alone* silently keeps the first block for a repeated ID string (fail-open, recorded; the frozen module is not modified).

Previous turn sync: `6aa4ba55a267e6dfaded8ba3a8e91369b6795443`. Contract `instruction-phase-md/0034_P9_L3c_2D_Model_Freeze_and_Evidence_Readiness_Contract.md` (`sha256:21ab02af…`).

## 1. Synchronization and plan (frozen before the audit)

- `HEAD` = `origin/main` = `6aa4ba5` (ancestry verified). The only tracked changes are the user's two pre-existing PDF deletions; 115 untracked user paths are untouched.
- `runs/p9/l3c/L3C_0_PLAN.json` (`sha256:6e95ec18…`) records:
  - 15 source hashes, the two dataset hashes and three L3b seed-0 checkpoint hashes (U-B-full, U-B-structured, U-C-full);
  - the L3b plan hash and the three P9-L3 gates (PASS);
  - 7 ontology roots (6 validation multi-repair + 1 empty-only) and 12 transformation roots (6 validation + 6 training roots with omission-only queries);
  - the transformation list.
- All 214 saved roots pass the canonical identity check (every z0 / zR / zO ID equals root + ordered (object, destination cell) moves).

## 2. Literal factor ontology of `ABC9U_UNIQUE_V1` (`runs/p9/l3c/l3c0/ontology.json`)

| family | network | variable scope | identity key in the unique model | conditioning | inside the outcome likelihood? |
|---|---|---|---|---|---|
| F3 scene unary | `scene` | one of z0, zS[I] | scene slot | c0 + edited poses, fixed q0 | yes, in P_S once |
| F3 structured pair | `pair_scene` | z0, zS[I] | (z0, I) | c0 | P_S once |
| F5 scene–scene pairs, scene HO | `cpl`, `ho_s` | zS pairs; all scene bits | slot pair; root | c0 | P_S once |
| F2 sequence unary (= F4 omission unary) | `order_s` + B prefix / C GRU | x_q | **physical query q** | q's own ordered ideal prefixes | E_Q, once per query |
| F4 zR–zO pair | `pair_omit` | x_r, x_(r∖t) | (parent r, t) | g_r | E_Q, once per (r, t) |
| F5 scene–query pair | `cpl` | scene bit a, x_q | **(parent r, slot role of q in r, a)** | g_r + role embedding | E_Q, once per parent and role |
| F5 zO–zO pair | `cpl` | x_(r∖s), x_(r∖t) | (parent r, s, t) | g_r | E_Q |
| F5 repair HO | `ho_q` / `ho_u` | all scene bits + x of r's slots | **parent r** (listed candidates only) | g_r | E_Q |
| F1 static unary / pair | `unary`, `pairh` | none | endpoint configuration (deduplicated) | endpoint xy | no: static BCE |
| travel J | `cost` | none | candidate r | g_r | no: log-Huber J |

**Factor instances on the 7 ontology roots (B-full):**

| root | sequence queries | F2 / F4 unaries | F4 zR–zO | F5 scene–query | F5 zO–zO | F5 repair HO | F3 / F5 in P_S | F1 endpoints | J |
|---|---|---|---|---|---|---|---|---|---|
| p8_2026102504 | 10 | 10 | 13 | 92 | 8 | 10 | 4 + 3 + 3 + 1 | 10 | 10 |
| p8_2026102510 | 5 | 5 | 4 | 36 | 2 | 5 | 4 + 3 + 3 + 1 | 5 | 5 |
| p8_2026102516 | 5 | 5 | 4 | 36 | 2 | 5 | same | 5 | 5 |
| p8_2026102522 | 6 | 6 | 6 | 48 | 3 | 6 | same | 6 | 6 |
| p8_2026102528 | 5 | 5 | 4 | 36 | 2 | 5 | same | 5 | 5 |
| p8_2026102534 | 5 | 5 | 4 | 36 | 2 | 5 | same | 5 | 5 |
| p8_2026102504_ref (empty-only) | 0 | 0 | 0 | 0 | 0 | 0 | 1 (z0 unary) + ho_s | 1 | 0 |

**Per-query multiplicity over all 214 roots** (`multiplicity_unique.json`):
- unary: exactly 1;
- blocks containing q as zO: 1–6;
- scene–query pair instances as zO: 4–24;
- higher-order scopes: 1–7 (523 queries in one, 20 in seven).

The F2 unary is physically keyed; the F5 relational instances are keyed by *listing*.

**When should two descriptions count as one factor?**
- A relation between two outcomes (or an outcome and a scene bit) is one physical relation **iff** its variable scope and the physical identities of those variables are the same. The listing context (which parent mentioned the query, in which role) is not physics.
- A zR–zO link (r, r∖t) is physically keyed already: it is determined by r and t.
- A higher-order hyperedge over (scene, r and its omissions) is a property of r. It should exist whenever r and those omissions are modelled, not only when r is listed as a candidate.
- The keyed competitor (report 0035) applies exactly this rule.

## 3. Catalogue transformations — frozen L3b seed-0 weights, labels never in priors, full deployed selector

**Selector.** Root-prior admission `sigmoid(logit p / τ) ≥ threshold` (τ and threshold from each checkpoint's L3b **validation** record), then `(moves, predicted J, analytic C_d, energy = E_static + T·softplus(−logit p), id)`. On all 12 validation roots it reproduces `p8_select.funnel`'s choice for B-full (τ 0.53, threshold 0.85), B-structured (τ 0.25, 0.5) and C-full (τ 0.25, 0.5).

**Columns:** "posterior" is offline (conditioned on every saved label of the root), never a selection input. Synthetic candidates are unlabelled hypotheticals: no physical label is created or presumed.

| arm | case | expected | roots | max prior change | max change of existing-label log-evidence | max offline posterior change | selection switches among existing candidates | selection picks the new candidate |
|---|---|---|---|---|---|---|---|---|
| B-full | permutation | invariant | 12 | 7e-15 | 4e-15 | 7e-15 | 0 | 0 |
| B-full | exact duplicate | invariant | 12 | 0 | 0 | 0 | 0 | 0 |
| B-full | disconnected candidate | invariant | 12 | 4e-15 | 4e-15 | 7e-15 | 0 | 2 |
| B-full | renamed IDs | invariant | 12 | 2e-15 | 4e-15 | 1e-18 | 0 | 0 |
| B-full | **alias promotion (one-move)** | allowed (new role-specific factors) | 6 | **0.038** | 0.034 | 0.085 | 0 | 0 |
| B-full | — unary only | decomposition | 6 | 1e-15 | — | — | 0 | 0 |
| B-full | — + scene–query pairs only | decomposition | 6 | 0.044 | 0.060 | 0.155 | 0 | 0 |
| B-full | — + higher-order only | decomposition | 6 | 0.029 | 0.076 | 0.182 | 0 | 0 |
| B-full | — + omission links only | decomposition | 6 | 1e-15 | — | — | 0 | 0 |
| B-full | genuinely related new candidate | allowed | 11 | 0.244 | 0.467 | 0.196 | 2 | 1 |
| B-structured | duplicate / permutation / disconnected / renamed | invariant | 12 each | ≤ 4e-15 | ≤ 4e-15 | ≤ 4e-15 | 0 | 1 (disconnected) |
| B-structured | alias promotion, one-move | invariant | 3 | 0 | 0 | 0 | 0 | 1 |
| B-structured | alias promotion, multi-move (new omission links) | allowed | 3 | 1e-6 | 1e-6 | 6e-17 | 0 | 0 |
| B-structured | related new candidate | allowed | 11 | 0.165 | 0.269 | 0.065 | 1 | 1 |
| C-full | duplicate / permutation / disconnected / renamed | invariant | 12 each | ≤ 1.3e-14 | ≤ 7e-15 | ≤ 1.3e-14 | 0 | 0 |
| C-full | **alias promotion (one-move)** | allowed | 6 | **0.298** | 0.069 | 0.065 | 0 | 0 |
| C-full | — + scene–query pairs only | decomposition | 6 | 0.301 | 0.063 | 0.071 | 0 | 0 |
| C-full | — + higher-order only | decomposition | 6 | 0.012 | 0.003 | 0.001 | 0 | 0 |
| C-full | related new candidate | allowed | 11 | 0.050 | 0.082 | 0.054 | 0 | 2 |

**Reading:**
- Adding a candidate can make the selector choose *that new option*: 4 cases, all unlabelled hypotheticals with unknown outcome. That is not an invariance violation, because every pre-existing candidate's probability, J, C_d and energy are unchanged.
- My first gate run counted *any* changed choice as a violation (`FAIL`). The criterion was corrected to "no switch among pre-existing candidates" and is recorded in the gate file.
- The earlier P9-L3 "choice change" figures came from a simplified probability-first proxy. They are superseded by this deployed-selector test.

**Identity:**
- In the conflicting-ID case, a copy of a candidate whose first destination is shifted by one cell keeps the same ID. `p9_l3c.check_identity` raises `IdentityError` (3/3 roots) before any deduplication, as does the keyed builder.
- The frozen `unique_factor.instances` silently keeps the first block. This is a latent fail-open path for corrupted catalogues; all saved data pass the canonical check, so no P9 result is affected.

**Label isolation:** scrambling every label and status leaves the priors bit-identical (max change 0.0).

## 4. Gate and accounting

- **Gate checks (all PASS):**
  - plan frozen before the audit;
  - sources unchanged since the plan;
  - checkpoints verified;
  - P9-L3 gates pass;
  - canonical identity on all roots;
  - conflicting ID fails closed;
  - unique invariances exact, including selection;
  - scene prior never moves;
  - deployed selector equals the P8 funnel;
  - prior label isolation;
  - 0 physical-module calls;
  - ontology written.
- **Code:** `p9_l3c.py` (audit module, 388 logical lines including the L3c-1 artifact and gate functions). It is above the 300-line guideline because the ledger, identity wrapper, decomposition, ontology, deployed selector, transformations and both L3c gates share one plan; training lives separately in `p9_l3d.py`. `tests/test_p9_l3c.py` (17 tests).
- **Compute:** L3c-0 used 37 CPU-s, including one gate re-evaluation after the criterion correction. All of it is in the ledger `runs/p9/l3c/guards/`.
