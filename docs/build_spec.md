# Build Spec — Redeployment Decision-Support Agent
**For:** SAP FDPM take-home exercise
**Stack:** Claude Code's choice — not prescribed; only behavior is prescribed

> **Frozen pre-build artifact.** This is the plan as written *before* implementation, kept
> as-is for the design trail — it does not track what was actually built. For the as-built
> system, current eval results, and how to run it, see [README.md](../README.md). Where the
> two diverge (e.g. the non-goals list gained a 4th item — no staleness-checking on skill
> tags — discovered during the build), that's expected: this document records intent, the
> README records outcome.

---

## simplified thesis
> Joule answers a question. This agent remembers a judgment.
Full thesis: business users should derive insights from data without having to file data engineering tickets, and these users should be able to derive insights using natural language queries, not SQL and the like. This is the "contextual layer" that's currently a contested high ground for both large enterprise players, like SAP, and point solution providers, like Wisdom AI. 

We know SAP Joule is already providing natural-language retrieval, akin to asking Gemini or Copilot. However, this agent prototype demonstrates the layer Joule presumable doesn't support right now: a business user authoring **standing, editable eligibility rules** in natural language that are continuously re-applied across the workforce data as data changes — with every match traceable to the rule that produced it.

This agent prototyped here is a **redeployment decision-support agent — not an autonomous decision-maker."**
Governing principle: **trust but validate.** Nothing writes to an EC record without explicit human approval.

## Persona / scenario
- **(me--Melanie) demos the prototype as persona People Ops workforce planner at **Rook Dynamics** — a fictional company, not a real one.
- Test case: a critical project starts in **30 days**. I need **10 people** who are:
  1. Available to start within 30 days (not committed to another project past that window)
  2. Have **Rust** coding skills
  3. Are **not** rolling off an intensive-travel assignment — *unless* their profile indicates they don't mind year-round travel (a custom MDF field)

---

## Data model (mock SuccessFactors EC — deliberately imperfect)

### `employees` (maps to EmpJob / PerPerson-style EC entities)
| field | notes |
|---|---|
| `employee_id` | |
| `name` | |
| `current_title` | |
| `department` | |
| `skills` | free-text-ish, **inconsistent on purpose**: "Rust", "Rust programming", "RUST" as separate entries for different people |
| `project_history` | list of past project assignments |
| `tenure_months` | |
| `location` | |

### `project_assignments` (custom MDF object — flag this as custom in the README)
| field | notes |
|---|---|
| `employee_id` | |
| `project_name` | |
| `planned_end_date` | single explicit field, not inferred — documented simplification |
| `intensity_flag` | e.g. "high-travel", "standard" |

### Custom MDF fields to include (flag as custom, not OOTB)
| field | notes |
|---|---|
| `travel_preference` | e.g. "standard", "opted_into_year_round_travel" — most employees standard, a few opted in |

### Deliberate data-quality issues to inject (all three from the design conversation-- see design conversation MD file for details)
1. **Missing tags** — a few employees who clearly have Rust experience (per project history) but no skill tag entered
2. **Inconsistent tags** — "Rust" / "Rust programming" / "RUST" as separate string values for the same skill
3. **One stale tag** — a skill tag present but the employee hasn't touched that skill in any project for 18+ months

### `open_positions`
| field | notes |
|---|---|
| `position_id` | |
| `role_title` | |
| `required_skills` | |
| `urgency` / `target_start_date` | |

---

## Agent architecture — 3 layers + a sidecar

1. **Deterministic scorer** (plain code, no LLM)
   Matches employees to the open criteria on structured fields: skill overlap, availability window, travel-intensity conflict. This is the "forecasting is solved" layer — fully explainable; no black box.

2. **NL rule interpreter (Anthropic API call)**
   Takes a natural-language rule typed by the user (e.g. *"Don't count someone as available if their current project's intensity flag is high-travel, unless their travel preference is opted_into_year_round_travel"*) and translates it into an eligibility filter/adjustment applied **before** the deterministic scorer runs.

3. **Explanation layer**
   For every match (and every exclusion), a one-line natural-language reason traceable to which rule fired. No unexplained score.

**Rule store sidecar** — rules persist between runs: this is the "persistence" half of my thesis, not just one-shot demo. A simple JSON/SQLite file is enough; doesn't need to be fancy.

---

## Demo flow — three parts, sequenced

**Part 1 — Project Falcon search (the Joule moment)**
Ask, in natural language: "Show me everyone who worked on Project Falcon." One-shot query — this is the retrieval baseline, the thing SAP likely ships today via Joule. 

**Part 2 — find and correct missing/inconsistent Rust tags**
Among the Falcon results, some employees are missing their Rust skill tag entirely, or have it spelled inconsistently ("Rust programming," "RUST"). Manually correct these records, save them back, and write out a report of the changes made — a human-in-the-loop correction, logged for accountability.

**Part 3 — full criteria search: availability + Rust + travel filter (the actual thesis)**
Framed narratively as staffing the upcoming Project Tiger. Run the standing eligibility rule — available within 30 days, Rust skills, not rolling off an intensive-travel assignment unless opted into year-round travel — against position P001. Feature one of the employees corrected in Part 2 as the single-case example, so the panel sees the same person go from excluded to eligible. Edit the rule live, re-run, show that person's ranking change. Then zoom out to the full scale view across all 10 slots. Surface a summary — matches found, "no confident match" count, and an estimated cost-avoidance figure using the SHRM baseline ($5,475 per hire) × the 3-5x external-hire-cost multiplier (sourced in the **Sources** section below).

## Human-in-the-loop (non-negotiable)
Chain: **surface → explain → human approves → agent writes back → agent reports.**
- Ranked matches and rule interpretation are always visible before any action.
- Nothing updates an EC record automatically.
- After explicit approval, the agent may batch-update a status field and produce a simple log/report of what it touched, when, and why. This doubles as an audit trail — useful in an HR/compliance context, and also closes the loop on the "so what?".

## Handling uncertainty — explicit eval criterion
- If no rule clearly covers a case, the agent says **"no confident match"** rather than forcing one.
- I have a tiny **golden set**: 5-10 hand-labeled correct matches. The agent will report a simple precision score and the test: does the agent's top-3 agree with the golden set. This directly answers the take-home's criterion: "how do you evaluate whether the system is working?".

## Explicit non-goals (stated in the README, but not built bc out-of-scope)
- No entity-resolution/normalization engine for the inconsistent skill tags — this is a deliberate scope boundary bc a production system would need a proper entity-resolution.
- No support for partial/simultaneous project allocation (e.g., 20% on Project A, 80% on Project B) — hard stop dates per assignment only, this is a deliberate scope decision for this prototype.
- No custom-field admin UI — the travel-preference field is presented as something a real HRIS admin would configure via MDF; this prototype doesn't build that configuration flow.

---

## Architecture diagram — 4 boxes
`Mock EC data → Deterministic scorer → NL rule interpreter (LLM call) → Explanation/output layer`, with the **rule store** as a small sidecar connected to the interpreter, persisting between runs.

---

## Build sequence (suggested order for Claude Code)
1. Mock data generation (employees, project assignments, open positions — inject the 3 imperfections deliberately)
2. Deterministic scorer (pure logic, testable in isolation before any LLM is involved)
3. Rule store (simplest persistence that works)
4. NL rule interpreter (Anthropic API call, translates rule text → filter logic)
5. Explanation layer (one-line reason per match/exclusion)
6. Golden set + precision eval
7. Human-approval write-back + audit log
8. Minimal UI surface — just enough to show the rule box, single-case view, and scale view live; polish is explicitly not what's being graded
9. README (problem framing, assumptions, architecture, tradeoffs — pull directly from the planning transcript in `design-process/`)

---

---

## Sources — for the README's problem-framing section
These back the "why this matters at Fortune 500 scale" claims used in this spec and in the walkthrough narrative. Included here in full, with attribution, so this document stands on its own for anyone — including a technical panelist — who wants to verify a claim without relying on outside context.

- **32% of U.S. hiring managers eliminated a role primarily due to AI and later rehired for the same or similar position.** Robert Half data reported by CNBC: "Employers who laid off workers citing AI are already starting to regret it," CNBC, July 2026. https://www.cnbc.com/2026/07/01/employers-who-laid-off-workers-for-ai-are-reversing-their-decisions.html
- **Ford rehired/promoted more than 350 experienced engineers** after automated quality-control systems missed issues veteran engineers could catch. Same CNBC report above; also covered in TechSpot, "More companies are rehiring workers they replaced with AI after automation fails to deliver," July 2026. https://www.techspot.com/news/112960-more-companies-rehiring-workers-they-replaced-ai-after.html
- **Commonwealth Bank of Australia laid off 40+ customer service staff, replaced them with an AI voice bot, then reversed the cuts** after the bot couldn't handle real customer volume/complexity. Same CNBC/TechSpot coverage above.
- **Gartner forecasts that by 2027, half of companies that attributed headcount cuts to AI will rehire staff for similar work,** often under a different title. Cited in IBTimes UK, "AI Layoffs Backfire as 32% of Bosses Rehire Roles They Thought Robots Could Do," July 2026. https://www.ibtimes.co.uk/ai-layoffs-reversed-companies-rehire-staff-1806357
- **About 5.3% of laid-off employees are eventually rehired by the same organization** — a rate that's held steady for years, not a new AI-era phenomenon. Visier analysis of 2.4 million employees across 142 organizations: "The True Cost of Layoff Boomerangs," Visier, 2026. https://www.visier.com/blog/true-cost-layoff-boomerangs/ — also covered independently in Fast Company, "Why companies hire back people they just laid off," Dec 2025. https://www.fastcompany.com/91447602/why-companies-hire-back-people-they-just-laid-off
  - The Visier researcher's framing is the strongest single line for the README's problem statement — paraphrased, not quoted verbatim here to respect source wording, but characterized in the Fast Company piece as: rehiring after layoffs reflects a failure of workforce planning and long-term strategic thinking, not just an AI story.
- **3-5x cost multiplier (external hire vs. internal redeployment):** originates with **the Josh Bersin Company (2023)** — external hiring costs 3-5x more than internal placement once sourcing, interviewing, onboarding, and ramp-up are factored in. Cited secondhand in "Internal Mobility: How to Fill Roles With Existing Talent," Pin, 2026. https://www.pin.com/blog/internal-mobility-hiring/ This is a secondary citation of Bersin's original research rather than the primary study itself. The multiplier originates with Josh Bersin Company, not McKinsey; McKinsey's contribution to this problem framing is the strategic-tradeoff argument cited separately below.
- **McKinsey's framing** — leaders should weigh the time/cost tradeoff of internal redeployment vs. external hiring, and that strategic workforce planning enables more rapid redeployment, moving organizations away from traditional hire-fire cycles toward sustainable through-cycle capacity management. "The critical role of strategic workforce planning in the age of AI," McKinsey & Company. https://www.mckinsey.com/capabilities/people-and-organizational-performance/our-insights/the-critical-role-of-strategic-workforce-planning-in-the-age-of-ai
- **External-hire cost-per-hire baseline: $5,475 (non-executive).** SHRM 2025 Benchmarking Report, non-executive cost-per-hire benchmark. This is a newly-added dollar baseline — this spec previously had only the 3-5x multiplier above with no absolute figure to apply it to. The cost-avoidance calculation is: baseline cost per hire ($5,475, SHRM 2025) × multiplier (3-5x, Josh Bersin Company 2023, cited separately above) × number of avoided external hires. Note: the commonly-cited $4,700 figure is from an older SHRM benchmarking cycle and is now outdated — do not use it.

**Source quality note:** Pin and similarly-positioned industry blogs are vendor content with a commercial interest in how the internal-mobility problem is framed. CNBC/Robert Half, Visier, and McKinsey are independent or primary-research sources and carry more evidentiary weight.

---

## Prompt handed to Claude Code
```
Build a working prototype of a redeployment decision-support agent per the build_spec.md. Follow the build sequence in order — get the deterministic scorer working and tested on mock data before wiring in the Anthropic API call for rule interpretation.
Keep the UI minimal: a rule input, a single-case view, and a scale view are enough — do not spend time on visual polish. Flag any point where you deviate from the spec so I can confirm before you continue. Ensure super powers framework is applied, per all projects we build.
```
