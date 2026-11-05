# Narrative Semantic Overlays for Bug Detection

Research code and data for a pilot study of whether assigning semantic roles
to variables helps language models detect seeded bugs in code.

## Pilot at a glance

The completed pilot contains 15 seeded defects and 15 matched, bug-free
programs. Four prompting conditions were tested with three samples per file
and condition: 360 reviews using `deepseek-chat`.

The study found no significant detection improvement from narrative overlays
over a deliberation-matched control. Real-domain labels reduced false alarms
on the clean programs; fictional labels did not. The paper reports the
analysis, methods, and limitations in detail.

All reported detection rates use line matches, an upper bound because defect
characterization has not been independently adjudicated. The pilot uses one
model family and is not evidence that the findings generalize to other models.

## Repository contents

- [`docs/paper.md`](docs/paper.md) — paper and pilot findings
- [`docs/paper.pdf`](docs/paper.pdf) — PDF version of the paper
- [`docs/experiment-plan.md`](docs/experiment-plan.md) — archived pre-registration
- `corpus/` — correct and defect-seeded programs plus ground truth
- `prompts/` — the tested condition prompts and additional prompt variants
- `harness/` — corpus generation, model runner, scoring, blinding, and analysis
- `results/` — transcripts and machine-readable result files

The main results table is [`results/results.csv`](results/results.csv).
`results/transcripts.jsonl` contains the exact prompts and model responses.
`results/blinding_key.json` maps blinded records to their conditions.

## Reproduce or inspect

The corpus can be checked and regenerated with Python 3:

```bash
python3 harness/build_corpus.py
```

Inspect the planned run without making API calls:

```bash
python3 harness/run_pilot.py --dry-run
```

To run new model calls, install the provider SDK you use (`anthropic` or
`openai`), set its API key in the corresponding environment variable
(`ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, or `OPENAI_API_KEY`), then run:

```bash
python3 harness/run_pilot.py --model deepseek-chat
```

Model calls may incur provider charges. New prompts and responses are
appended to `results/transcripts.jsonl`; do not commit credentials or
private data. The existing outputs are the results of the completed pilot,
not a promise that a new run will reproduce identical model responses.

For local analysis of the published files:

```bash
python3 harness/blind.py
python3 harness/score.py
python3 harness/analyze.py --metric linematch
```

Use the line-match metric as an upper bound, not an adjudicated performance
measure. See the paper before interpreting or comparing results.

## Licensing

Software in `harness/` is licensed under the MIT License in [`LICENSE`](LICENSE).
The paper, corpus, prompts, and result data are licensed under CC BY 4.0 as
described in [`LICENSE-DATA`](LICENSE-DATA). Please cite and attribute the
materials when reusing them.
