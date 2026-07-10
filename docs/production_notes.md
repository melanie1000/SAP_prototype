# Production Notes

Context for an engineering team picking this up: what's actually running in the prototype,
what's simulated, and what would need to be built before this could touch real employee data
or drive a real redeployment decision. This is a decision-support prototype for the SAP FDPM
take-home exercise, not a spec for a shippable product — treat everything below as a starting
punch list, not a finished design.

## Current stack (as built)

- **Language/runtime:** Python 3.11, single-process.
- **UI:** Streamlit — one script (`app.py`), server-rendered, no separate frontend build.
  Session state lives in the Streamlit process; nothing survives a server restart except what's
  explicitly persisted (see below).

- **Data models:** Pydantic v2 (`src/models.py`) — `Employee`, `ProjectAssignment`,
  `OpenPosition`, `ProjectHistoryEntry`. Validation happens at load time only.

- **"EC" data:** static JSON files (`data/employees.json`, `project_assignments.json`,
  `open_positions.json`), generated once by `data/generate_mock_data.py` and then mutated
  in place by the app's write-back functions. No real SuccessFactors connection exists.

- **Rule persistence:** SQLite via stdlib `sqlite3` (`src/rule_store.py`, `rules.db`) — a
  single active rule, versioned by insert, no concurrency control.

- **LLM:** Anthropic API (`claude-sonnet-5`), used for exactly two things — translating a
  typed eligibility rule into a structured filter, and translating a one-shot retrieval
  query into a project name. The LLM never decides who's eligible; a deterministic scorer
  (`src/scorer.py`) always makes that call from the LLM's structured output.

- **Audit trail:** flat-file JSONL (`audit_log.jsonl`), append-only, one line per write-back
  or skill-tag correction. No tamper protection, no retention policy, no query interface.

- **Auth:** none. `APPROVER_NAME` is a hardcoded constant standing in for "whoever is logged
  in" — there is no login at all.

- **Secrets:** local `.env` file (`ANTHROPIC_API_KEY`), loaded via `python-dotenv`.

- **Tests:** 53 unit/integration tests (`pytest`), plus a 10-example hand-labeled golden set
  (`data/golden_set.json`) evaluated via `src/run_eval.py` (positive precision@3, negative
  exclusion rate). No load testing, no concurrency testing, no LLM-inversion regression suite
  beyond what's manually documented in the implementation plan.

- **Deployment:** none — runs locally via `./run_demo.sh` or `streamlit run app.py`.

## What the prototype validated (worth carrying forward as-is)

- **The architecture split**: LLM interprets, deterministic code decides. The rule
  interpreter (`src/rule_interpreter.py`) only ever produces a structured filter
  (`required_skills`, `available_within_days`, `exclude_if`/`unless`); `src/scorer.py` is
  the only thing that actually marks someone eligible or not, using plain field comparisons.
  This kept eligibility auditable and testable independent of LLM behavior, and is the right
  pattern to keep — don't let a future team fold the decision logic into a prompt.

- **Human-approval gate on every write**: nothing touches employee data without an explicit
  UI action (`apply_writeback`, `correct_skill_tag`), and both functions only log an audit
  entry for what actually changed — no fabricated log lines for no-ops or unmatched IDs. This
  guarantee (verified in tests) is worth preserving exactly, since it's the thing that makes
  "not an autonomous decision-maker" true rather than aspirational.

- **LLM output is genuinely unreliable in one specific, addressable way**: during build, the
  same exact rule text produced correct output, semantically inverted output (excluding the
  wrong group), and a raw JSON parse failure across three consecutive calls. This was fixed
  with explicit worked examples in the system prompt plus a bounded retry-on-malformed-JSON
  helper — but it's evidence, not a guarantee, that inversion-class bugs are gone. A
  production system needs ongoing monitoring for this failure class, not just the one-time
  fix that got it under control here (see "LLM reliability" below).

## What's mocked and needs real integration

- **Employee/position/assignment data** is static JSON, hand-generated with `random.seed(42)`
  for determinism. Production needs a real read path into SAP SuccessFactors EC — likely
  OData/API integration for employee master data, and the two fields flagged in the data
  model as custom MDF objects (`project_assignments`, `travel_preference`) would need to
  actually exist as provisioned custom objects/fields in a real EC tenant, with real data
  governance around who can edit them.

- **Skills** are a free-text list on each employee record. The deliberately-injected data
  mess (missing tags, inconsistent spelling like "Rust"/"Rust programming"/"RUST", stale
  tags with no recent project work) was built to prove the *matching logic* handles messy
  data gracefully — it wasn't meant to be a permanent design. Production should integrate
  with a real skills/competency taxonomy (SAP's skills ontology or a third-party system) so
  skills are normalized IDs, not strings, which eliminates the inconsistent-spelling problem
  at the source instead of requiring a human to manually correct it person-by-person in a UI.

- **Write-back target**: the app writes directly to the mock JSON file. Production needs
  transactional writes to EC (or a staging/review queue in front of EC), with idempotency
  and conflict handling if two planners act on overlapping candidate pools concurrently —
  today's `redeployment_status` check only prevents double-booking within a single running
  process, not across concurrent sessions or restarts.

## Production readiness gaps

**Auth & access control**
- Replace `APPROVER_NAME` with real SSO/identity (e.g. SAP IAS, Okta) and capture the actual
  authenticated user on every write, not a constant.
- Role-based permissions: who can author/edit a standing rule vs. who can approve a
  write-back vs. who can view which employees' data. Today anyone with the URL can do all
  three.

**Data persistence & scale**
- SQLite rule-store sidecar → a real managed database with backup/replication; the current
  design has zero concurrency control (two planners saving a rule at once will silently
  clobber each other).
- The UI currently lists every candidate individually, fine for the ~100-person mock pool —
  a real workforce needs pagination/search/filtering, and the "single hardcoded position
  (P001)" scoping needs to become genuine multi-position support with cross-position
  allocation logic (today, a person eligible for two open roles is counted in both until one
  write-back removes them — explicitly called out as out of scope in the README).

**LLM reliability & governance**
- Structured logging of every LLM call (prompt, raw response, latency, cost) — not for
  debugging convenience, but because this LLM call determines who gets flagged eligible for
  a real employment action, and "why did the system exclude this person" needs to be
  answerable after the fact.
- A confidence/fallback path: when rule interpretation is ambiguous or fails validation, the
  prototype falls back to an empty filter silently degrading to "everyone matches" — that's
  fine for a demo, actively wrong for production, where an ambiguous rule should block on
  human clarification rather than silently doing something unintended.
- Prompt versioning and regression evaluation: the `exclude_if`/`unless` inversion bug found
  during build (same input, three different outputs across three calls) means prompt changes
  need to be evaluated against a golden set *before* rollout, not just spot-checked. That
  needs to become an automated CI gate, not the manual `src/run_eval.py` script it is today.
- The golden set itself is 10 hand-labeled examples — nowhere near enough to catch drift or
  edge cases in production. Needs to grow substantially and be maintained by someone with
  actual HR-domain judgment, ideally covering every `exclude_if`/`unless` field combination.

**Audit & compliance**
- JSONL append-only file → a durable, tamper-evident audit store with a defined retention
  policy and a real query/reporting interface (compliance teams will ask "show me every
  redeployment decision touching person X in the last year," and `grep`-ing a JSONL file
  isn't an answer).
- Using an LLM to help make employment-related decisions likely falls under automated
  employment decision tool regulations in some jurisdictions (e.g. NYC Local Law 144) —
  needs legal review before this touches real people, independent of how good the
  engineering is.
- Explainability: today's output is a one-line reason string per match/exclusion
  (`src/explain.py`). Compliance and EEOC/adverse-impact review will likely need more —
  demographic-blind rule design review, and monitoring for disparate impact across protected
  classes, neither of which this prototype attempts.

**Operational**
- Secrets: `.env` file → a real secrets manager (SAP BTP credential store, or cloud
  equivalent) with rotation.
- Containerization, CI/CD, and environment separation (dev/staging/prod) — none of which
  exist today; this runs from a local `venv`.
- Streamlit's session-state model doesn't scale horizontally without extra work (sticky
  sessions or moving state to a shared store) — worth deciding early whether Streamlit is
  the right UI layer for a multi-user production tool, or whether the deterministic
  scorer/rule-interpreter core should be extracted behind a proper API with a different
  frontend.

## Open questions for the eng team

- Who owns the skills taxonomy going forward — is normalizing skill tags at the source (EC
  integration) in scope for this team, or is messy skill data a permanent constraint the
  matching logic needs to keep handling gracefully?

- What's the actual approval workflow supposed to be — is single-person approval (today's
  design) sufficient, or does a real redeployment decision need two-person sign-off given
  its employment impact?
  
- Is Streamlit acceptable as the production UI layer, or is this prototype's real deliverable
  the scorer/rule-interpreter core, to be re-exposed behind a different frontend?
