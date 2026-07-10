# Redeployment Decision-Support Agent

A prototype for the SAP FDPM take-home exercise: a People Ops planner authors standing,
editable eligibility rules in natural language, continuously re-applied across workforce
data, with every match traceable to the rule that produced it. Not an autonomous
decision-maker — nothing writes to an EC record without explicit human approval.

Design background and the full planning conversation: [docs/planning_transcript.md](docs/planning_transcript.md).

## Problem framing

- **32% of U.S. hiring managers eliminated a role primarily due to AI and later rehired
  for the same or similar position.** Robert Half data reported by CNBC: "Employers who
  laid off workers citing AI are already starting to regret it," CNBC, July 2026.
  https://www.cnbc.com/2026/07/01/employers-who-laid-off-workers-for-ai-are-reversing-their-decisions.html
- **Ford rehired/promoted more than 350 experienced engineers** after automated
  quality-control systems missed issues veteran engineers could catch. Same CNBC report
  above; also covered in TechSpot, "More companies are rehiring workers they replaced with
  AI after automation fails to deliver," July 2026.
  https://www.techspot.com/news/112960-more-companies-rehiring-workers-they-replaced-ai-after.html
- **Commonwealth Bank of Australia laid off 40+ customer service staff, replaced them with
  an AI voice bot, then reversed the cuts** after the bot couldn't handle real customer
  volume/complexity. Same CNBC/TechSpot coverage above.
- **Gartner forecasts that by 2027, half of companies that attributed headcount cuts to AI
  will rehire staff for similar work,** often under a different title. Cited in IBTimes UK,
  "AI Layoffs Backfire as 32% of Bosses Rehire Roles They Thought Robots Could Do," July
  2026. https://www.ibtimes.co.uk/ai-layoffs-reversed-companies-rehire-staff-1806357
- **About 5.3% of laid-off employees are eventually rehired by the same organization** — a
  rate that's held steady for years, not a new AI-era phenomenon. Visier analysis of 2.4
  million employees across 142 organizations: "The True Cost of Layoff Boomerangs,"
  Visier, 2026. https://www.visier.com/blog/true-cost-layoff-boomerangs/ — also covered
  independently in Fast Company, "Why companies hire back people they just laid off," Dec
  2025. https://www.fastcompany.com/91447602/why-companies-hire-back-people-they-just-laid-off
  - The Visier researcher's framing, as characterized in the Fast Company piece: rehiring
    after layoffs reflects a failure of workforce planning and long-term strategic
    thinking, not just an AI story.
- **3-5x cost multiplier (external hire vs. internal redeployment):** originates with **the
  Josh Bersin Company (2023)** — external hiring costs 3-5x more than internal placement
  once sourcing, interviewing, onboarding, and ramp-up are factored in. Cited secondhand in
  "Internal Mobility: How to Fill Roles With Existing Talent," Pin, 2026.
  https://www.pin.com/blog/internal-mobility-hiring/ This is a secondary citation of
  Bersin's original research rather than the primary study itself. The multiplier
  originates with Josh Bersin Company, not McKinsey; McKinsey's contribution to this
  problem framing is the strategic-tradeoff argument cited separately below.
- **McKinsey's framing** — leaders should weigh the time/cost tradeoff of internal
  redeployment vs. external hiring, and that strategic workforce planning enables more
  rapid redeployment, moving organizations away from traditional hire-fire cycles toward
  sustainable through-cycle capacity management. "The critical role of strategic workforce
  planning in the age of AI," McKinsey & Company.
  https://www.mckinsey.com/capabilities/people-and-organizational-performance/our-insights/the-critical-role-of-strategic-workforce-planning-in-the-age-of-ai
- **External-hire cost-per-hire baseline: $5,475 (non-executive).** SHRM 2025 Benchmarking
  Report, non-executive cost-per-hire benchmark. The cost-avoidance calculation is: baseline
  cost per hire ($5,475, SHRM 2025) × multiplier (3-5x, Josh Bersin Company 2023, cited
  separately above) × number of avoided external hires. Note: the commonly-cited $4,700
  figure is from an older SHRM benchmarking cycle and is now outdated — not used here.

**Source quality note:** Pin and similarly-positioned industry blogs are vendor content
with a commercial interest in how the internal-mobility problem is framed. CNBC/Robert
Half, Visier, and McKinsey are independent or primary-research sources and carry more
evidentiary weight.

## Architecture

Mock EC data → Deterministic scorer → NL rule interpreter (Anthropic API call) →
Explanation/output layer, with a SQLite rule-store sidecar persisting rules between runs.

- **Deterministic scorer** (`src/scorer.py`): pure logic, no LLM. Exact-string skill
  matching and availability-window checks on structured fields.
- **NL rule interpreter** (`src/rule_interpreter.py`): Anthropic API call translating a
  typed rule into a structured JSON eligibility filter, applied before the scorer runs.
  Also supports a separate one-shot NL retrieval query mode (project-history lookup) that
  never persists to the rule store.
- **Explanation layer** (`src/explain.py`): one-line reason per match/exclusion.
- **Rule store** (`src/rule_store.py`): SQLite sidecar, versioned, active rule persists
  between runs.
- **Write-back** (`src/writeback.py`): human-approved writes only — `apply_writeback` for
  redeployment status, `correct_skill_tag` for manual data-quality corrections — both
  append to an audit log and never fabricate a log entry for a no-op or unmatched ID.

## Data model

Mock SuccessFactors EC data, deliberately imperfect. `project_assignments` and the
`travel_preference` field are flagged as custom MDF objects/fields, not out-of-the-box EC.
Three deliberate data-quality issues are injected into ~100 mock employees (see
`data/generate_mock_data.py`): missing skill tags, inconsistent tag spelling ("Rust" /
"Rust programming" / "RUST"), and one stale tag (skill unused 18+ months).

## Demo flow

1. **One-shot lookup** — ask a natural-language question about project history (e.g. "show
   me everyone who worked on Project Falcon"). This is read-only and never touches the
   persisted rule store.
2. **Flag and correct** — the lookup surfaces people with missing or inconsistently-spelled
   skill tags; a human can approve a one-tag correction, logged to the audit trail.
3. **Re-run the persisted rule** — the standing eligibility rule box re-applies live, and
   corrected people now flow through as skill-eligible, without any code changes.

## Evaluation

A hand-labeled golden set of 5-10 known-correct matches (`data/golden_set.json`) is
designed to be labeled independently by the exercise author — not derived from the
agent's own output — and used to compute a precision score: does the agent's top-3
ranked candidates per position agree with the golden set.

**Status at time of writing: not yet run.** The golden set requires manual hand-labeling
by a human, independent of this agent, which is still pending. The mock data and
deterministic scorer this evaluation will run against are already built and tested. Once
`data/golden_set.json` is populated, the evaluation harness can be added to compute and
report the precision score.

## Assumptions and tradeoffs

The scale view's cost-avoidance estimate uses a $5,475 non-executive cost-per-hire baseline
(SHRM 2025 Benchmarking Report) multiplied by the cited 3-5x external-hire-cost multiplier.
This baseline is an across-industry, across-role-type average — a specialized technical hire
(Rust engineer) likely costs more once longer sourcing/vetting time is factored in. Treat the
resulting figure as a conservative baseline, not a precise estimate for this specific role type.

The scale view's per-position eligible counts are not deduplicated across positions — a
person eligible for two roles is counted in both until a write-back approval removes them
from the candidate pool. Simultaneous/partial allocation across roles is out of scope for
this prototype.

## Non-goals (explicit scope boundaries)

- No entity-resolution/normalization engine for inconsistent skill tags — corrections are
  manual, one person at a time, human-approved.
- No support for partial/simultaneous project allocation — hard stop dates only.
- No custom-field admin UI for configuring MDF fields like `travel_preference`.
- No staleness checking on skill tags: some employees have a `Rust` tag despite no Rust
  project work in 18+ months, and the deterministic scorer treats them as skill-eligible
  regardless. A production system would need to validate skill tags against recency of use,
  not just presence.

## Running it

1. `pip install -r requirements.txt` (or use the project's `venv/`: `./venv/bin/pip install -r requirements.txt`)
2. Copy `.env.example` to `.env` and add your `ANTHROPIC_API_KEY`.
3. `python data/generate_mock_data.py`
4. `streamlit run app.py`

## Sources

- **32% of U.S. hiring managers eliminated a role primarily due to AI and later rehired for
  the same or similar position.** Robert Half data reported by CNBC: "Employers who laid
  off workers citing AI are already starting to regret it," CNBC, July 2026.
  https://www.cnbc.com/2026/07/01/employers-who-laid-off-workers-for-ai-are-reversing-their-decisions.html
- **Ford rehired/promoted more than 350 experienced engineers** after automated
  quality-control systems missed issues veteran engineers could catch. Same CNBC report
  above; also covered in TechSpot, "More companies are rehiring workers they replaced with
  AI after automation fails to deliver," July 2026.
  https://www.techspot.com/news/112960-more-companies-rehiring-workers-they-replaced-ai-after.html
- **Commonwealth Bank of Australia laid off 40+ customer service staff, replaced them with
  an AI voice bot, then reversed the cuts** after the bot couldn't handle real customer
  volume/complexity. Same CNBC/TechSpot coverage above.
- **Gartner forecasts that by 2027, half of companies that attributed headcount cuts to AI
  will rehire staff for similar work,** often under a different title. Cited in IBTimes UK,
  "AI Layoffs Backfire as 32% of Bosses Rehire Roles They Thought Robots Could Do," July
  2026. https://www.ibtimes.co.uk/ai-layoffs-reversed-companies-rehire-staff-1806357
- **About 5.3% of laid-off employees are eventually rehired by the same organization** — a
  rate that's held steady for years, not a new AI-era phenomenon. Visier analysis of 2.4
  million employees across 142 organizations: "The True Cost of Layoff Boomerangs,"
  Visier, 2026. https://www.visier.com/blog/true-cost-layoff-boomerangs/ — also covered
  independently in Fast Company, "Why companies hire back people they just laid off," Dec
  2025. https://www.fastcompany.com/91447602/why-companies-hire-back-people-they-just-laid-off
  - The Visier researcher's framing is the strongest single line for the README's problem
    statement — paraphrased, not quoted verbatim here to respect source wording, but
    characterized in the Fast Company piece as: rehiring after layoffs reflects a failure
    of workforce planning and long-term strategic thinking, not just an AI story.
- **3-5x cost multiplier (external hire vs. internal redeployment):** originates with **the
  Josh Bersin Company (2023)** — external hiring costs 3-5x more than internal placement
  once sourcing, interviewing, onboarding, and ramp-up are factored in. Cited secondhand in
  "Internal Mobility: How to Fill Roles With Existing Talent," Pin, 2026.
  https://www.pin.com/blog/internal-mobility-hiring/ This is a secondary citation of
  Bersin's original research rather than the primary study itself. The multiplier
  originates with Josh Bersin Company, not McKinsey; McKinsey's contribution to this
  problem framing is the strategic-tradeoff argument cited separately below.
- **McKinsey's framing** — leaders should weigh the time/cost tradeoff of internal
  redeployment vs. external hiring, and that strategic workforce planning enables more
  rapid redeployment, moving organizations away from traditional hire-fire cycles toward
  sustainable through-cycle capacity management. "The critical role of strategic workforce
  planning in the age of AI," McKinsey & Company.
  https://www.mckinsey.com/capabilities/people-and-organizational-performance/our-insights/the-critical-role-of-strategic-workforce-planning-in-the-age-of-ai
- **External-hire cost-per-hire baseline: $5,475 (non-executive).** SHRM 2025 Benchmarking
  Report, non-executive cost-per-hire benchmark. This is a newly-added dollar baseline —
  this spec previously had only the 3-5x multiplier above with no absolute figure to apply
  it to. The cost-avoidance calculation is: baseline cost per hire ($5,475, SHRM 2025) ×
  multiplier (3-5x, Josh Bersin Company 2023, cited separately above) × number of avoided
  external hires. Note: the commonly-cited $4,700 figure is from an older SHRM benchmarking
  cycle and is now outdated — do not use it.

**Source quality note:** Pin and similarly-positioned industry blogs are vendor content
with a commercial interest in how the internal-mobility problem is framed. CNBC/Robert
Half, Visier, and McKinsey are independent or primary-research sources and carry more
evidentiary weight.
