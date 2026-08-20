# llm-guideline-moderation

Reproduction code and dataset assets for the guideline refinement workflow in *Refining and Reusing Annotation Guidelines for LLM Annotation*.

This repository is a focused release of the **guideline refinement** component from a larger unified framework that originally combined **guideline generation**, **guideline refinement**, and **evaluation**. For the paper artifact, that broader system was split apart and reorganized so readers can rerun the refinement workflow with shared datasets, schemas, and guideline files without depending on the full original application.

## What This Repo Gives You

- the original guideline texts used for refinement experiments
- train and valid PubAnnotation datasets for BC5CDR, BioRED, and NCBI Disease
- ?published experiment specs for paper-style runs?
- a modular iterative refinement runner
- a directory annotator for producing valid-set predictions with the final refined guideline
- PubAnnotation-ready JSON outputs that can be uploaded to your own project for comparison

This repository does **not** guarantee bit-for-bit reproduction of the paper outputs. LLM behavior changes across providers, model versions, and time. The goal here is **workflow reproducibility**, **shared inputs**, and **transparent comparison**.

## Workflow At A Glance

```text
train subset sample
  -> initial annotation
  -> strict-match F1 against gold
  -> discrepancy analysis
  -> moderation principle
  -> guideline refinement
  -> re-annotation and re-evaluation
  -> stop at F1 >= 0.9 or no improvement
  -> final refined guideline
  -> valid set annotation
  -> upload predictions to PubAnnotation
  -> compare against the public evaluation project
```

## Repository Defaults

- paper-style refinement subset: `sample_size = 10`
- shared sampled subset across compared models
- fixed random seed recorded in each spec
- prompt evidence cap: `n_examples = 5`
- stopping rule: strict-match `F1 >= 0.9` or no further improvement

## Repository Layout

- `data/datasets/`
  train pools for refinement sampling and valid sets for final annotation
- `data/guidelines/`
  dataset guideline text files
- `data/schemas/`
  entity label lists
- `experiments/`
  published experiment specs
- `scripts/run_iterative_refinement.py`
  train-subset refinement runner
- `scripts/annotate_pubannotation_dir.py`
  valid-set annotation runner
- `docs/pubannotation_usage.md`
  detailed upload and comparison guide

## Included Datasets

| Dataset | Train pool | Valid set | Entity schema | Evaluation project |
| --- | --- | --- | --- | --- |
| BC5CDR | included | included | `data/schemas/bc5cdr_entities.schema.json` | [bc5cdr-valid](https://pubannotation.org/projects/bc5cdr-valid) |
| BioRED | included | included | `data/schemas/biored_entities.schema.json` | [biored-valid](https://pubannotation.org/projects/biored-valid) |
| NCBI Disease | included | included | `data/schemas/ncbi_entities.schema.json` | [ncbi-valid](https://pubannotation.org/projects/ncbi-valid) |

## Published Specs

Use these when you want the paper-style configuration:

- `experiments/bc5cdr_valid_round1.spec.json`
- `experiments/biored_valid_round1.spec.json`
- `experiments/ncbi_disease_valid_round1.spec.json`

Each spec records:

- dataset name and split
- evaluation reference
- guideline and schema paths
- train source directory
- sampling method, subset size, and seed
- provider and model defaults
- iterative settings such as `threshold_f1` and `n_examples`

## Quick Start

### 1. Choose a Provider

Supported providers:

- `openai`
- `gemini`
- `deepseek`

Set the API key required for the provider you want to use.

### 2. Run Iterative Refinement

Example:

```bash
python scripts/run_iterative_refinement.py --spec experiments/bc5cdr_valid_round1.spec.json --provider <provider> --model <model_name>
```

That run produces:

- `outputs/<experiment_id>_iterative/final/final_guidelines.txt`
- `outputs/<experiment_id>_iterative/final/iterative_refinement_run.json`

### 3. Annotate the Valid Set

```bash
python scripts/annotate_pubannotation_dir.py --input-dir data/datasets/bc5cdr/valid --guidelines outputs/<experiment_id>_iterative/final/final_guidelines.txt --entities data/schemas/bc5cdr_entities.schema.json --output-dir outputs/bc5cdr_valid_annotations --provider <provider> --model <model_name>
```

That output directory contains one PubAnnotation JSON file per document and is ready to upload.

## PubAnnotation: What It Is Doing Here

PubAnnotation is used here as the **comparison surface**, not as the main execution environment.

This repository handles:

- train subset sampling
- iterative guideline refinement
- valid-set annotation
- export of PubAnnotation-format JSON

PubAnnotation is where you:

- create your own project
- upload the generated prediction files
- open the corresponding public evaluation project
- compare the same `sourcedb/sourceid` documents across projects

The key point is that the repo gives you the **inputs and code** for rerunning refinement, while PubAnnotation gives you the **visual and project-based evaluation surface**.

## PubAnnotation Comparison Flow

1. Run a published spec to obtain a final refined guideline.
2. Annotate the valid set with that guideline.
3. Create your own PubAnnotation project for the same dataset.
4. Upload the generated JSON files.
5. Open the public evaluation project for the same dataset.
6. Compare matching `sourcedb/sourceid` entries document by document.

Detailed instructions are in [docs/pubannotation_usage.md](docs/pubannotation_usage.md).

## Published Result Variants

For transparency and manual inspection, the PubAnnotation space used with this project includes result variants produced with different annotation settings and models.

The released comparison setup uses the following project naming scheme:

`{dataset}-valid-{model}-{reasoning}-{condition}`

- `dataset`: `bc5cdr`, `ncbi`, `biored`
- `model`: `gpt`, `gemini`, `deepseek`
- `reasoning`: `nr` (non-reasoning) or `r` (reasoning)
- `condition`: `ng` (no guideline), `g` (guideline), or `m` (moderated)
- note: `nr` runs do not have the `m` condition

That means each model contributes five published result variants:

- `nr-ng`
- `nr-g`
- `r-ng`
- `r-g`
- `r-m`

If you open any of the PubAnnotation project links below and scroll down to the **Evaluations** section, you can inspect the evaluation values corresponding to the results reported in the paper tables.

You can also inspect the underlying documents directly:

1. open one of the project links below
2. scroll to the **Documents** section
3. open the document list for the source database
4. inspect columns such as `source DB`, `source ID`, `text`, `size`, and `# Ann.`
5. click a specific document to open its detailed view

Inside the detailed document page, the recommended view is **Annotations -> TextAE**. TextAE provides the clearest visual display of entity spans and labels, and is the easiest way to inspect annotation behavior document by document.

### BC5CDR

| Model | NR-NG | NR-G | R-NG | R-G | R-M |
| --- | --- | --- | --- | --- | --- |
| GPT | [bc5cdr-valid-gpt-nr-ng](https://pubannotation.org/projects/bc5cdr-valid-gpt-nr-ng) | [bc5cdr-valid-gpt-nr-g](https://pubannotation.org/projects/bc5cdr-valid-gpt-nr-g) | [bc5cdr-valid-gpt-r-ng](https://pubannotation.org/projects/bc5cdr-valid-gpt-r-ng) | [bc5cdr-valid-gpt-r-g](https://pubannotation.org/projects/bc5cdr-valid-gpt-r-g) | [bc5cdr-valid-gpt-r-m](https://pubannotation.org/projects/bc5cdr-valid-gpt-r-m) |
| Gemini | [bc5cdr-valid-gemini-nr-ng](https://pubannotation.org/projects/bc5cdr-valid-gemini-nr-ng) | [bc5cdr-valid-gemini-nr-g](https://pubannotation.org/projects/bc5cdr-valid-gemini-nr-g) | [bc5cdr-valid-gemini-r-ng](https://pubannotation.org/projects/bc5cdr-valid-gemini-r-ng) | [bc5cdr-valid-gemini-r-g](https://pubannotation.org/projects/bc5cdr-valid-gemini-r-g) | [bc5cdr-valid-gemini-r-m](https://pubannotation.org/projects/bc5cdr-valid-gemini-r-m) |
| DeepSeek | [bc5cdr-valid-deepseek-nr-ng](https://pubannotation.org/projects/bc5cdr-valid-deepseek-nr-ng) | [bc5cdr-valid-deepseek-nr-g](https://pubannotation.org/projects/bc5cdr-valid-deepseek-nr-g) | [bc5cdr-valid-deepseek-r-ng](https://pubannotation.org/projects/bc5cdr-valid-deepseek-r-ng) | [bc5cdr-valid-deepseek-r-g](https://pubannotation.org/projects/bc5cdr-valid-deepseek-r-g) | [bc5cdr-valid-deepseek-r-m](https://pubannotation.org/projects/bc5cdr-valid-deepseek-r-m) |

### NCBI Disease

| Model | NR-NG | NR-G | R-NG | R-G | R-M |
| --- | --- | --- | --- | --- | --- |
| GPT | [ncbi-valid-gpt-nr-ng](https://pubannotation.org/projects/ncbi-valid-gpt-nr-ng) | [ncbi-valid-gpt-nr-g](https://pubannotation.org/projects/ncbi-valid-gpt-nr-g) | [ncbi-valid-gpt-r-ng](https://pubannotation.org/projects/ncbi-valid-gpt-r-ng) | [ncbi-valid-gpt-r-g](https://pubannotation.org/projects/ncbi-valid-gpt-r-g) | [ncbi-valid-gpt-r-m](https://pubannotation.org/projects/ncbi-valid-gpt-r-m) |
| Gemini | [ncbi-valid-gemini-nr-ng](https://pubannotation.org/projects/ncbi-valid-gemini-nr-ng) | [ncbi-valid-gemini-nr-g](https://pubannotation.org/projects/ncbi-valid-gemini-nr-g) | [ncbi-valid-gemini-r-ng](https://pubannotation.org/projects/ncbi-valid-gemini-r-ng) | [ncbi-valid-gemini-r-g](https://pubannotation.org/projects/ncbi-valid-gemini-r-g) | [ncbi-valid-gemini-r-m](https://pubannotation.org/projects/ncbi-valid-gemini-r-m) |
| DeepSeek | [ncbi-valid-deepseek-nr-ng](https://pubannotation.org/projects/ncbi-valid-deepseek-nr-ng) | [ncbi-valid-deepseek-nr-g](https://pubannotation.org/projects/ncbi-valid-deepseek-nr-g) | [ncbi-valid-deepseek-r-ng](https://pubannotation.org/projects/ncbi-valid-deepseek-r-ng) | [ncbi-valid-deepseek-r-g](https://pubannotation.org/projects/ncbi-valid-deepseek-r-g) | [ncbi-valid-deepseek-r-m](https://pubannotation.org/projects/ncbi-valid-deepseek-r-m) |

### BioRED

| Model | NR-NG | NR-G | R-NG | R-G | R-M |
| --- | --- | --- | --- | --- | --- |
| GPT | [biored-valid-gpt-nr-ng](https://pubannotation.org/projects/biored-valid-gpt-nr-ng) | [biored-valid-gpt-nr-g](https://pubannotation.org/projects/biored-valid-gpt-nr-g) | [biored-valid-gpt-r-ng](https://pubannotation.org/projects/biored-valid-gpt-r-ng) | [biored-valid-gpt-r-g](https://pubannotation.org/projects/biored-valid-gpt-r-g) | [biored-valid-gpt-r-m](https://pubannotation.org/projects/biored-valid-gpt-r-m) |
| Gemini | [biored-valid-gemini-nr-ng](https://pubannotation.org/projects/biored-valid-gemini-nr-ng) | [biored-valid-gemini-nr-g](https://pubannotation.org/projects/biored-valid-gemini-nr-g) | [biored-valid-gemini-r-ng](https://pubannotation.org/projects/biored-valid-gemini-r-ng) | [biored-valid-gemini-r-g](https://pubannotation.org/projects/biored-valid-gemini-r-g) | [biored-valid-gemini-r-m](https://pubannotation.org/projects/biored-valid-gemini-r-m) |
| DeepSeek | [biored-valid-deepseek-nr-ng](https://pubannotation.org/projects/biored-valid-deepseek-nr-ng) | [biored-valid-deepseek-nr-g](https://pubannotation.org/projects/biored-valid-deepseek-nr-g) | [biored-valid-deepseek-r-ng](https://pubannotation.org/projects/biored-valid-deepseek-r-ng) | [biored-valid-deepseek-r-g](https://pubannotation.org/projects/biored-valid-deepseek-r-g) | [biored-valid-deepseek-r-m](https://pubannotation.org/projects/biored-valid-deepseek-r-m) |

The intended use of this repository is:

1. reproduce the refinement workflow locally
2. generate your own final refined guideline
3. annotate the valid set
4. upload your results to your own PubAnnotation project
5. compare your outputs against the public projects and released result variants

This makes it possible to inspect not only gold comparisons, but also how annotation behavior changes across prompt conditions such as no-guideline, guideline-based, and moderated-guideline settings.

## Notes On Fidelity

This public release is designed to follow the paper's refinement path:

- random train subset sampling
- strict-match F1 evaluation
- discrepancy-driven refinement
- stopping at `F1 >= 0.9` or no improvement
- final annotation of the valid set

It is therefore best understood as a **paper-oriented modularization** of the refinement workflow, not as a full mirror of every capability from the original unified application.

## Citation

If you use this repository or want to cite the paper associated with this workflow, please cite:

**Refining and Reusing Annotation Guidelines for LLM Annotation**

The repository is a modularized reproduction release for the paper's guideline refinement workflow, built from a larger unified annotation framework.

Publication metadata is not finalized yet, so the citation entry below is a temporary placeholder and should be updated once the final venue and author list are available.

```bibtex
@inproceedings{TBD,
  title={Refining and Reusing Annotation Guidelines for LLM Annotation},
  author={TBD},
  booktitle={TBD},
  year={TBD}
}
```
