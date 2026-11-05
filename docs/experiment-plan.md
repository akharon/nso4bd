# Experiment Plan: Narrative Semantic Overlays for Bug Detection

**Status:** Archived pre-registration, revision 2, for the pilot reported in
`paper.md`. The pilot has since been run; deferred arms and limitations are
documented in `paper.md`.
**Implements:** the protocol planned for the pilot.
**Revision 2 changes:** see the Changelog at the end. Three of them are
blocking — the experiment as previously specified could not answer its own
question, for reasons found by reading the built apparatus rather than the
prose describing it.

---

## 1. Background and the claim being tested

Humans use mnemonic systems (major system, PAO, method of loci) to remember
arbitrary sequences by mapping them onto meaningful stories. The idea here is
adjacent but distinct: instead of using a narrative overlay to aid *recall*,
use it as a *consistency oracle* for code review.

Concretely: assign each variable in a piece of code a role in a small
ontology (e.g. "duck", "lion") together with rules constraining how those
roles may interact ("a duck cannot eat a lion"). Any operation that maps onto
a forbidden interaction is flagged as suspicious — allegedly without needing
to understand the real domain semantics of the code.

This imitates what units-of-measure systems already do (rejecting
`Meters + Seconds`), except the ontology is arbitrary and assigned post hoc
rather than declared and real.

### 1.1 The originating idea decomposes into four separable claims

The proposal as originally stated bundles four things. They are not equally
plausible and they are not tested by the same experiment, so the plan states
which of them it tests.

| # | Claim | Tested here? |
|---|---|---|
| C1 | A role overlay helps a model *remember* code | **No** — out of scope, see §2 |
| C2 | A role overlay helps a model *find bugs* | Yes — primary |
| C3 | The check is **context-free**: rules + assignments suffice, the code itself is not needed | Yes — new in rev. 2, §5, Treatment D |
| C4 | The ontology may be **arbitrary/non-real** without loss | Yes — §5, A vs. C vs. A-scrambled |

C3 is the sharpest and most falsifiable of the four, and it was untested in
revision 1: every condition showed the model the full source, so "you do not
need the context" was never actually put at risk. It is now the load-bearing
new arm.

C4 is what makes the idea interesting rather than a restatement of
dimensional analysis. If real-domain labels work as well as invented ones,
the proposal reduces to existing practice (§3).

## 2. Scope: what this experiment does not test

The original framing began with *memory* — that a narrative overlay would
make code easier to hold in mind. This plan tests only the oracle use, for
two reasons: an LLM in a single-turn review has the source in context and
does not need to recall it, so the memory claim has no natural analogue here;
and measuring it would require a different design entirely (present a long
file, distract, then require reconstruction or question-answering without
the source).

That design is viable and worth doing separately — a reconstruction-accuracy
comparison, overlay vs. no overlay, over files long enough to matter. It is
simply a different experiment, and folding it in would confound two
manipulations. Recorded here so that the narrowing is a decision rather than
an omission.

## 3. Prior work (verified)

Revision 1 had no related-work section, and `paper.md` §2 names its related
work descriptively without references. The following are real, checkable, and
change what counts as a novel result. URLs are given because unverified
citations are worse than absent ones.

**Roles of variables (Sajaniemi et al.).** The closest existing thing to this
proposal, and the most important omission from the current draft. A small
fixed taxonomy of variable roles (fixed value, stepper, most-recent holder,
gatherer, follower, walker, temporary, organiser, one-way flag, container)
covers the overwhelming majority of variable uses in ordinary programs, and
teaching it measurably improves *human* program comprehension in controlled
studies. Implications for this experiment: (a) the idea that role assignment
aids reasoning about code is established for humans, not novel; (b) there is
an off-the-shelf, empirically-grounded role taxonomy, which is a better
Treatment B than invented `SORT_A`/`SORT_B` labels, or at minimum an
additional arm; (c) the "does it have to be fictional" question (C4) has a
natural comparison point in a taxonomy that is neither fictional nor
domain-specific.
<https://saja.kapsi.fi/var_roles/literature.html>,
<https://www.ppig.org/files/2005-PPIG-17th-sajaniemi.pdf>

**Unit-inconsistency detection without annotations (Phys, Phriky-units,
SA4U).** Static analysers that infer physical units *from variable names* and
propagate them by dimensional analysis, with no developer annotations. Phys
assigns units to ~75% of variables at a reported ~82% true-positive rate, and
found inconsistencies in 11% of 213 open-source systems (>900k LOC) at ~87%
TP. This is essentially Treatment C implemented as static analysis, and it
predates the LLM framing. Two consequences: the plan needs a **non-LLM
baseline** (§9) — currently absent — and any claim of practical value must be
argued against tools that already work.
<https://conf.researchr.org/details/issta-2017/issta-2017-research/18/>,
<https://arxiv.org/pdf/2210.09136>

**LLM type inference for untyped Python (TypyBench and related).** Directly
relevant negative evidence: LLMs produce decent type *similarity* but show
significant type *consistency* errors across a codebase. Since the overlay's
entire mechanism is self-consistency of a self-authored labelling, documented
inconsistency in exactly that operation is a specific reason to expect H1 to
fail, and a reason to measure overlay stability (§7.2) rather than assume it.
<https://arxiv.org/pdf/2507.22086>, <https://arxiv.org/pdf/2508.00422>

**Structured intermediate representations as a prompting strategy.**
Abstraction-of-Thought and related work show that inducing an intermediate
structured representation before answering improves results on reasoning
tasks generally. This is the principal alternative explanation for any
positive result: the overlay is such a representation, and the benefit may
come from having one at all rather than from its content. §5 is built around
separating these. <https://arxiv.org/pdf/2308.10620>

**Practitioner tooling.** LLM-driven dimensional-annotation tooling already
exists in shipped form (e.g. Trail of Bits' dimensional-analysis skill),
which is further evidence that Treatment C is the incumbent to beat rather
than a control that can be assumed weak.

**Assessment.** The specific combination — an *arbitrary, self-authored,
fictional* ontology used as a consistency oracle by an LLM — does not appear
to have been studied. The surrounding claims largely have been. The novel,
publishable question is therefore C3 and C4 (does arbitrariness cost
anything, and is the check really context-free), not C2 on its own.

## 4. Hypotheses

**H1 (detection).** Prompting a model to build and check a role-based
semantic overlay before reviewing code increases F1 on seeded swap,
wrong-variable, and unit-mismatch defects **relative to a deliberation-
matched control** (Control+, §5), not merely relative to an answer-
immediately control.

**H2 (class specificity).** Any such effect is concentrated in defect classes
where the operands are distinguishable by role, and is absent in off-by-one
and missing-check defects.

**H3 (context-freeness, new).** A checker that sees *only* the role
assignments, the rule set, and a symbolic operation trace — never the source
— detects the role-distinguishable defects at a rate meaningfully above
chance.

**H4 (arbitrariness, new).** Fictional and opaque ontologies (A, B) perform
comparably to real-domain labelling (C), and both outperform a *scrambled*
ontology whose role assignments are internally inconsistent (A-scrambled).

**Null hypotheses.** No measurable difference against Control+; or the
overlay is net-negative, its arbitrary ontology producing more false
positives on correct code than the true positives it gains.

**Cost is not part of H1.** Revision 1 stated H1 as an improvement "at
comparable or lower token cost." That conjunct makes H1 nearly certain to
fail for the wrong reason: the treatments are *instructed* to emit three
steps of reasoning and the control is instructed to emit none, so treatments
must cost several times more by construction. Cost is now reported as a
separate dimension (§7) and evaluated against Control+, which is
deliberation-matched.

## 5. Conditions

Revision 1 had four conditions and could not separate "structured
relabelling" from "any deliberation at all," because **the control condition
forbids reasoning**: `prompts/control.txt` ends with "Do not include any
other prose, preamble, or summary," while every treatment instructs three
steps of written-out analysis before the report. `harness/run_pilot.py` makes
plain single-turn calls with no extended-thinking budget, so this is not a
cosmetic difference — the control genuinely receives far less test-time
computation than the treatments. Any observed advantage would be attributable
to that alone. This is the blocking defect of revision 1.

Conditions, as a ladder of comparisons, each rung isolating one factor:

| Condition | Description | Isolates |
|---|---|---|
| **Control** | "Review this code for bugs." Report only. | Floor |
| **Control+** *(new)* | Same task, but instructed to work through the code carefully and write out its reasoning before reporting. **No** roles, labels, or ontology. | Deliberation, without relabelling |
| **Treatment A** | Fictional bestiary + informal narrative rules | Fiction |
| **Treatment A-scrambled** *(new, optional)* | Identical to A, but role assignments are deliberately permuted so the ontology is internally incoherent | Whether *coherence* of the overlay matters, or only its presence |
| **Treatment B** | Opaque sorts (`SORT_A`…) + explicit permitted-operation table | Structure without meaning |
| **Treatment C** | Real domain roles (units, entity types) + real compatibility rules | Real semantics — the incumbent (§3) |
| **Treatment D** *(new)* | Two-stage, decoupled — see §5.1 | **Context-freeness (H3)** |

The comparisons that matter, in order:

1. **Control vs. Control+** — does any deliberation help? Establishes the
   real baseline. If the gap here is large, every revision-1 result would
   have been this effect wearing a costume.
2. **Control+ vs. {A, B, C}** — does *relabelling* add anything beyond
   deliberation? This is H1 proper.
3. **{A, B} vs. C** — does arbitrariness cost anything? This is the paper's
   motivating question (C4/H4). If C wins, the fictional framing is
   decoration and §3's prior work already covers the useful case.
4. **A vs. A-scrambled** — does the overlay have to be *coherent*, or is any
   labelling ritual sufficient? A null here would be the most deflationary
   possible result and is cheap to obtain.
5. **Treatment D vs. all** — is the check genuinely context-free (H3)?

### 5.1 Treatment D — the decoupled arm (tests the strongest claim)

The originating idea claims that to find the bug "you do not need to know the
code context at all but just rules and assignments." That is directly
testable and has not been tested.

- **Stage 1 (builder).** A model sees the source and emits *only*: the role
  assignment table, the rule set, and a symbolic trace of every operation
  with identifiers replaced by role tokens and annotated with line numbers
  (e.g. `L33: DUCK * RIVER -> ?`). It emits **no** flags and **no** source.
- **Stage 2 (checker).** A *fresh* instance — no history, and preferably a
  smaller/cheaper model — sees only the Stage 1 artefact. It never sees the
  code. It reports `FLAG line=N` for every operation forbidden by the rules.

Stage 1 must be prevented from smuggling the answer through: the emitted
trace is validated to contain no identifiers from the source, no literals,
and no natural-language commentary beyond the rule set. Instances failing
validation are logged and excluded, and the exclusion rate is itself
reported.

Why this is the highest-value arm:

- If Stage 2 finds the defects, the strong claim is vindicated in a way no
  other condition can show, and it yields a genuinely useful artefact: an
  expensive model builds the overlay once, a cheap model re-checks it
  continuously.
- If Stage 2 collapses, the overlay is a reasoning scaffold, not an oracle —
  which is a clean, publishable negative result and directly contradicts the
  original intuition.

Either outcome is informative, which is not true of every arm here.

### 5.2 Prompt-wording sensitivity

All prompts were authored in one pass by one model, and results may reflect
their specific wording. Write **two paraphrases per condition**, differing in
surface wording but not structure, and assign them alternately across files.
Treat paraphrase as a random factor; if it moves the outcome more than the
condition does, the experiment is measuring prompt luck and must say so.

## 6. Corpus

### 6.1 What currently exists

15 hand-authored bug-free files (25–40 lines) with generated seeded twins in
`corpus/`, ground truth in `corpus/ground_truth.json`, built reproducibly by
`harness/build_corpus.py`. Hand-authored rather than drawn from Defects4J or
BugsInPy, to avoid the memorisation threat.

**Note a documentation inconsistency to fix:** revision 1 §Materials step 1
recommended starting from Defects4J/BugsInPy, and revision 1 targeted ~60
buggy files (12 per class). What was actually built is 15 files (3 per
class), hand-authored — i.e. the *pilot* corpus, following the opposite
sourcing decision. This plan now treats 15 files as the pilot corpus and 60
as the full-grid corpus, and hand-authoring as settled.

### 6.2 Blocking defect: bug class is confounded with domain

Revision 1 §Materials step 4 requires classes to be balanced across domains,
and `paper.md` §3.1 asserts they are rotated. **In the built corpus they are
not.** From `corpus/ground_truth.json`:

| Class | Domains of its 3 files |
|---|---|
| swapped_operands | numeric, numeric, id |
| wrong_variable | id, numeric, numeric |
| unit_type_mismatch | numeric, control_flow, control_flow |
| off_by_one | numeric, control_flow, control_flow |
| missing_check | id, control_flow, control_flow |

The three classes where H2 predicts an effect draw 7 of 9 files from
numeric/ID domains. The two classes where H2 predicts a null draw 4 of 6 from
the control-flow domain. H2's predicted pattern is therefore **exactly
aligned with domain**, and a confirmation would be uninterpretable: an
apparent class effect and a pure domain effect predict identical data. Note
also that two of the three `unit_type_mismatch` files are tagged
`control_flow` domain, which is odd on its face.

**Fix (required before the run).** At 3 files per class and 3 domains, a
complete cross-balance is exactly achievable: one file per (class, domain)
cell, 15 cells, 15 files. This requires re-authoring roughly six files. Until
that holds, H2 is not testable and per-class results must not be reported as
evidence for it.

### 6.3 Required: mutations must be proven behaviour-changing

`paper.md` §3.3 records that one planned mutation — swapping the operands of
`abs(destination - origin)` — was behaviour-preserving and was caught by
inspection. `excluded_mutations` in the ground truth is currently empty and
nothing checks this automatically. A behaviour-preserving "defect" is
undetectable in principle and depresses recall equally across conditions,
adding noise to every comparison.

Add to `build_corpus.py`: for each pair, execute the correct and buggy
versions over randomised inputs and require **at least one observable
divergence**. Abort the build if none is found, and record any exclusion in
`excluded_mutations` with its reason. This generalises the lesson instead of
relying on an author noticing.

### 6.4 Corpus provenance caveat

The corpus was authored by a model from the same family as the models under
evaluation. Model-written code may be unusually legible to that family, and
its naming conventions may align with the evaluator's priors — plausibly
inflating the treatments, which depend on inferring roles *from names* (the
same mechanism Phys exploits, §3). Mitigate by including at least one
evaluated model from a different family, or record it as a limitation.

## 7. Procedure

### 7.1 Execution

Each (file, condition, sample) is an independent single-turn request with no
conversation carryover, so an overlay built for one file cannot leak into the
next. Source is presented with line numbers prepended, identically under
every condition.

### 7.2 Required: repeated sampling (k ≥ 3)

Revision 1 sampled each instance once. This is the second blocking defect.
The shakedown's Finding 3 and `paper.md` §5.2 both establish that the
overlay's discriminating power depends entirely on where the model draws its
sort boundaries, and §7 concedes that this variance is unmeasured. With k=1
it is impossible to distinguish "the treatment does not work" from "the
treatment works when the ontology lands well, and it lands well half the
time" — and that distinction is the practical question.

Run **k = 3 samples minimum per (file, condition)** at temperature 1.0.
Report per-instance detection *rate*, not a boolean, and report
between-sample variance as a headline number alongside the means. Also report
best-of-3 and unanimous-3, which correspond to two real usage patterns
(sample until something is flagged; trust only consistent flags).

This triples the pilot to ~450 calls on 25–40 line files — a few dollars.
The variance estimate is worth more than the saving.

### 7.3 Required: guard against silent truncation

`run_pilot.py` sets `MAX_TOKENS = 4096` and records `stop_reason`, but
**nothing ever checks it**. Every treatment places its report *last*, after
the `=== REPORT ===` marker, so a truncated response loses precisely the
scoreable part. `blind.py` then extracts zero flags and `score.py` records a
clean miss. Because treatments emit long sort tables and the control emits
almost nothing, this artefact acts **only on the treatments** — the exact
opposite direction to the control confound in §5, so the two do not cancel;
they just make the result uninterpretable in both directions.

Fix: raise the cap, assert `stop_reason != "max_tokens"` during scoring, and
count truncated instances separately rather than as false negatives.

## 8. Measures

- **Precision, recall, F1** over seeded defects. Note the definition already
  implemented in `analyze.py`: precision is computed over buggy files only,
  with clean-file flags reported separately as FP-rate. Keep this, and state
  it explicitly rather than leaving it to be inferred.
- **False-positive rate on bug-free twins** — both files-flagged and
  flags-per-file.
- **Flags per file** (new): a shotgun reviewer buys recall cheaply. Report
  the distribution, and pre-register that a condition whose mean flag count
  is more than double the control's is reported as such prominently.
- **Token cost**, input and output, per review.
- **Ordinal position of the first true positive.**
- **Overlay stability** (new): across the k samples, do repeated runs produce
  the same role assignments? Report agreement, motivated by the type-
  consistency findings in §3.

### 8.1 Line tolerance

Revision 1 used ±2 lines, implemented as `LINE_TOLERANCE = 2` in `score.py`.
On a 25–40 line file a ±2 window is a 5-line span — roughly a sixth of the
file per flag. Make the **primary criterion ±1**, and report ±2 as a
sensitivity analysis. Pre-register both so the choice cannot be made after
seeing which one favours the hypothesis.

## 9. Baselines beyond the control conditions

Add a **non-LLM baseline** for the unit-mismatch class: run an existing
unit-inconsistency analyser (§3), or cite its published rates, over the same
files. Without this there is no way to tell whether any of these conditions
is worth running in place of a static analyser that costs nothing per
invocation. This is a small addition that substantially changes what the
results can claim.

## 10. Scoring and adjudication

A flag is a true positive if it names the correct line (±1 primary) **and**
correctly characterises the defect. Line proximity is mechanical;
characterisation is adjudicated by a judge blind to condition.

**Adjudication rule, fixed in advance** (already encoded in `score.py`, now
recorded here too): a flag landing on the correct line but describing a
*different* problem — "right line, wrong reason" — or too vague to evaluate,
is scored **wrong**.

**Blinding, and its limits.** `blind.py` reduces each transcript to its FLAG
lines, removing the overlay reasoning. But it keeps flag *descriptions*
verbatim, and those descriptions may themselves carry condition-revealing
vocabulary ("the duck is eating the lion here", "ILL-SORTED under my table").
Blinding is therefore incomplete as implemented. Two additions:

1. A vocabulary scrub over descriptions before adjudication.
2. **A manipulation check** (new): have an independent model attempt to guess
   the condition from the blinded flags alone. If it exceeds chance by a
   meaningful margin, blinding has failed and must be reported as failed
   rather than assumed to have worked.

**Inter-rater reliability** (new): double-adjudicate a random 20% subsample
with a second, independent adjudicator and report Cohen's κ. Pre-register a
floor of κ ≥ 0.7; below it, sharpen the rubric and re-adjudicate. Revision 1
and `paper.md` §7 both concede no reliability estimate is available; at this
cost there is no reason to leave that standing.

## 11. Analysis

The primary pre-registered outcome is **overall F1, Control+ versus each
treatment** (not Control versus each treatment — see §5). Paired per-file
outcomes are tested with an exact two-sided McNemar test, Holm-Bonferroni
corrected across treatments, as implemented in `analyze.py`. Per-class
breakdowns are secondary and exploratory, and are uninterpretable until §6.2
is fixed.

With k ≥ 3 samples the per-file outcome must be defined before analysis.
Pre-register **majority-of-3** as the primary definition, with best-of-3 and
unanimous-3 reported as sensitivity analyses.

## 12. Pilot and pre-registered decision rules

**Pilot:** 15 seeded files + 15 bug-free twins, conditions Control,
Control+, A, C, k = 3, one model. That is 30 × 4 × 3 = 360 calls. Add
Treatment D and A-scrambled if budget allows.

The pilot is a **variance and effect-size estimator, not a hypothesis test.**
With 15 paired observations an exact McNemar test needs roughly 9–10
discordant pairs in one direction to reach p < 0.05. A non-significant pilot
is the expected outcome and would not refute anything.

Revision 1 said to escalate "if pilot effect sizes justify it," which is
unfalsifiable after the fact. Numeric rules, fixed in advance:

- **Escalate to the full grid** if the best treatment beats **Control+** by
  ΔF1 ≥ 0.10, *and* its clean-file FP-rate is ≤ 1.5× Control+'s.
- **Abandon or redesign** if the best treatment is within ΔF1 ≤ 0.02 of
  Control+, or its clean-file FP-rate is ≥ 2× Control+'s.
- **Between those** — report the pilot as inconclusive and, before spending
  more, use the measured variance (§7.2) to compute the corpus size an
  adequately powered run would actually require.
- **Report regardless of outcome.** A null is a result; §3 makes it a
  moderately interesting one.

**Full grid:** 60 buggy + 60 correct files, 6 conditions, k = 3, ≥ 2 models
(at least one from a different family, §6.4). Name concrete model IDs in the
writeup for reproducibility; `run_pilot.py` currently defaults to
`claude-sonnet-5`.

Pilot data must never be silently substituted for full-grid data.

## 13. Threats to validity

- **Deliberation confound (was fatal, now controlled).** Any structured
  pre-analysis may help simply by forcing a second reading. Control+ is the
  control for this. Treatment C alone was not sufficient, because C is *also*
  a relabelling pass — the revision-1 design could distinguish fiction from
  real semantics, but not relabelling from mere thinking.
- **Ontology-choice variance.** The overlay's power depends on where the
  model draws sort boundaries, and it chooses them itself. Addressed by k ≥ 3
  and the stability measure (§7.2, §8), not eliminated.
- **False positives on correct code.** Identified during pre-run review:
  bug-free files legitimately hold two units at once — degrees
  and radians, Fahrenheit and Celsius — and a checker faithfully applying its
  own table should flag them. 10 of 15 clean files carry unit-bearing
  identifiers. Elevated treatment FP-rates are therefore a **predicted**
  outcome and must be reported as predicted, not as a discovery.
- **Class/domain confound.** §6.2. Blocking for H2 until fixed.
- **Truncation artefact.** §7.3. Biases against treatments; opposite in sign
  to the control confound, so the two do not cancel.
- **Blinding leakage through flag descriptions.** §10, with a manipulation
  check to detect it.
- **Corpus provenance and self-authorship.** §6.4.
- **Prompt-wording sensitivity.** §5.2.
- **Single defect per file.** Real files carry several interacting defects;
  precision measured against one planted defect is optimistic.
- **Model familiarity with mnemonic literature.** A model with strong priors
  about the method of loci may pattern-match to it rather than perform the
  check. Not fully controllable; noted.
- **Multiplicity.** More conditions in revision 2 means more comparisons.
  Holm-Bonferroni across treatments; the five comparisons in §5 are ordered
  by importance in advance, and only comparison 2 is the primary outcome.

## 14. Deliverables

1. Raw transcripts for every (file, condition, model, sample).
2. Scored results table: file, bug_class, domain, condition, model, sample,
   true_positive, false_positives, total_flags, tokens, first_flag_position,
   stop_reason.
3. Summary statistics, variance across samples, and significance tests.
4. The manipulation-check result and Cohen's κ.
5. A results writeup feeding `paper.md`; completed pilot results are now
   reported there.

## 15. Execution notes

- Run with fresh context per instance; never carry history between files.
- Log every prompt and response verbatim; metrics must be recomputable from
  raw data.
- Check `stop_reason` on every record before scoring (§7.3).
- The adjudicator must not read `results/blinding_key.json`.

## Changelog — revision 1 → 2

**Blocking (the experiment could not answer its question without these):**

1. **Control+ added.** The control prompt forbids prose; the treatments
   mandate three reasoning steps. The revision-1 comparison was
   deliberation vs. no deliberation, not overlay vs. no overlay. (§5)
2. **Class/domain confound documented and corpus rebalance required.** H2's
   predicted pattern is currently indistinguishable from a domain effect.
   (§6.2)
3. **Repeated sampling k ≥ 3 required.** The dominant variance term — which
   ontology the model happens to draw — was unmeasured at k=1. (§7.2)

**Substantive additions:**

4. Treatment D, the decoupled two-stage arm — the only test of the original
   "you don't need the code context" claim. (§5.1)
5. A-scrambled arm: does the overlay need to be *coherent*? (§5)
6. Verified prior work, including the roles-of-variables literature and
   annotation-free unit checkers that already do Treatment C's job. (§3)
7. Non-LLM baseline required. (§9)
8. Truncation guard — a silent, treatment-only false-negative source. (§7.3)
9. Blinding manipulation check and inter-rater reliability with a
   pre-registered κ floor. (§10)
10. Numeric escalate/abandon thresholds replacing "if effect sizes justify
    it." (§12)
11. Line tolerance tightened to ±1 primary, ±2 sensitivity. (§8.1)
12. Mutations must be proven behaviour-changing automatically. (§6.3)
13. Cost removed from H1 as a conjunct; reported separately. (§4)
14. Scope statement: the memory half of the original idea is explicitly out
    of scope, with a sketch of how it would be tested. (§2)
15. Corpus-size and sourcing inconsistency with the built artefacts
    reconciled. (§6.1)
