# Deterministic vs. Probabilistic — Component Breakdown

**Source:** derived from `build_spec.md`'s architecture section (3 layers + sidecar).
**Purpose:** a quick reference for anyone (technical panelist included) who wants to see, at a glance, which parts of this agent are plain code and which parts involve an LLM call — and why the boundary between them is where it is.

---

## Deterministic (plain code, no LLM)

- **Scorer** — matches employees to criteria on structured fields: skill overlap, availability window, travel-intensity conflict. The spec calls this "the 'forecasting is solved' layer — fully explainable; no black box."
- **Rule store** — a JSON/SQLite sidecar that persists rules between runs. Pure data storage, no inference.
- **Golden-set eval** — precision scoring against 5–10 hand-labeled matches is arithmetic, not a model call.
- **Write-back / audit log** — batch-updating a status field and logging what/when/why after human approval is mechanical, not generative.
- **Data model + injected imperfections** — the mock data itself, including the deliberately inconsistent skill tags, is fixed fixture data, not model output.

## Probabilistic (Anthropic API call involved)

- **NL rule interpreter** — the one clearly probabilistic component. Takes a natural-language rule (e.g. "don't count someone as available if their current project's intensity flag is high-travel, unless their travel preference is opted_into_year_round_travel") and translates it into structured filter logic. This is the only place an LLM call sits *upstream* of a decision.
- **Explanation layer** — generates the one-line natural-language reason per match/exclusion. The spec constrains this so the output stays traceable ("no unexplained score") — the *content* it explains is deterministic, but the *phrasing* is generated.
- **Part 1's natural-language query** ("Show me everyone who worked on Project Falcon") — the retrieval-style ask goes through an LLM to become a query.

## The load-bearing boundary

The spec's core design bet is that probabilistic interpretation only ever produces a *filter/rule*, never a *match decision* directly — the filter is applied **before** the deterministic scorer runs. The scorer that actually decides who's eligible is 100% deterministic downstream of that.

That's what lets two things hold:
- the "no confident match" fallback, and
- the full-explainability claim.

The LLM has no path to silently override or fuzz a match; it can only mistranslate the rule it's handed, which is a narrower and more auditable failure mode.

## Soft spot worth flagging

Part 2's manual correction of missing/inconsistent Rust tags is human-in-the-loop, not agent-generated — so those corrections are neither deterministic-code nor LLM-probabilistic, they're just human edits the agent logs.
