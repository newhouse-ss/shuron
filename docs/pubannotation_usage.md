# PubAnnotation Upload And Evaluation Guide

This repository stops at producing **PubAnnotation-format prediction files**. The final comparison step is intentionally done in PubAnnotation.

## The Intended Division Of Labor

This repository is responsible for:

- running guideline refinement on sampled train documents
- generating a final refined guideline
- annotating the valid set with that guideline
- exporting one PubAnnotation JSON file per document

PubAnnotation is responsible for:

- hosting your uploaded prediction project
- hosting the public evaluation project
- letting you inspect the same documents across projects

In short:

- this repo = execution and export
- PubAnnotation = inspection and comparison

## Recommended End-To-End Flow

1. Run iterative refinement with one of the published specs.
2. Take the resulting `final_guidelines.txt`.
3. Annotate the full valid set with `scripts/annotate_pubannotation_dir.py`.
4. Create your own PubAnnotation project for the target dataset.
5. Upload the generated JSON files into that project.
6. Open the matching public evaluation project.
7. Compare the same documents using `sourcedb` and `sourceid`.

## What The Repo Outputs

After valid-set annotation, the output directory looks like this:

```text
outputs/<run_name>/
  10074612.json
  10539815.json
  10840460.json
  ...
```

Each file is already a PubAnnotation document with fields such as:

- `text`
- `sourcedb`
- `sourceid`
- `denotations`

That means you do **not** need to convert the format before upload.

Reference:

- [PubAnnotation annotation format](https://www.pubannotation.org/docs/annotation-format/)

## The Most Important Identity Check

Before uploading, make sure these three things are aligned:

- the files you generated locally
- the project you create in PubAnnotation
- the public evaluation project you want to compare against

The important identity fields are:

- `sourcedb`
- `sourceid`

PubAnnotation comparison is effectively document-identity-based. Matching filenames alone are not enough if the document identity differs.

## Creating Your Own Project

The exact PubAnnotation UI may change, but the practical goal is simple:

1. create a new project for your dataset
2. make sure the project is using the same documents you want to compare
3. upload your generated annotations into that project

Helpful references:

- [Creating annotations](https://www.pubannotation.org/docs/create-annotation/)
- [Annotation editor](https://www.pubannotation.org/docs/annotation-editor/)

## Inspecting Documents Inside A Project

Once you open a project page, you can use the **Documents** section to inspect the underlying dataset entries.

The usual navigation flow is:

1. open a project
2. scroll to **Documents**
3. click the source database entry
4. review the document table
5. click a specific `source ID` entry for a detailed document page

The document table is useful because it lets you quickly inspect:

- `source DB`
- `source ID`
- `text`
- `size`
- `# Ann.`

This is often the fastest way to confirm that your uploaded project and the public evaluation project are aligned at the document level before you inspect annotations in detail.

## Recommended Annotation View: TextAE

On the detailed document page, the best view for manual inspection is usually:

`Annotations -> TextAE`

TextAE is recommended because it gives a clear visual rendering of:

- entity spans
- entity labels
- span boundaries in context

That makes it much easier to compare:

- no-guideline outputs
- guideline-conditioned outputs
- moderated / refined-guideline outputs

across the same document.

## Upload Options

### Option 1: Use The PubAnnotation UI

Best when:

- you want to inspect a few files manually
- you are trying the workflow for the first time
- you want a low-friction sanity check before uploading a full valid set

### Option 2: Use The PubAnnotation API

Best when:

- you want to upload the entire valid set
- you want a repeatable batch workflow

Reference:

- [PubAnnotation API](https://www.pubannotation.org/docs/api/)

Example request shape:

```bash
curl -H "content-type: application/json" -u "USERNAME:PASSWORD" -d @annotations.json "https://pubannotation.org/projects/<your-project>/docs/sourcedb/<SOURCE_DB>/sourceid/<SOURCE_ID>/annotations.json"
```

## Public Evaluation Projects

- BC5CDR: [https://pubannotation.org/projects/bc5cdr-valid](https://pubannotation.org/projects/bc5cdr-valid)
- BioRED: [https://pubannotation.org/projects/biored-valid](https://pubannotation.org/projects/biored-valid)
- NCBI Disease: [https://pubannotation.org/projects/ncbi-valid](https://pubannotation.org/projects/ncbi-valid)

## Practical Comparison Checklist

When you compare your project with the public evaluation project, check:

1. are `sourcedb` and `sourceid` identical?
2. are you looking at the same dataset and split?
3. was the valid set annotated with the final refined guideline?
4. did you upload the full output directory rather than a partial mix of files?

If all four are true, then the project comparison is meaningful.

## Recommended Usage Pattern

The published repo surface is aimed at the paper-style path:

1. use a published spec
2. sample `10` train documents
3. refine until `F1 >= 0.9` or no improvement
4. annotate the valid `100` documents
5. upload the valid-set predictions to your own PubAnnotation project
6. compare them with the public evaluation project

If you want a smaller local smoke test, make a temporary local copy of a spec and reduce `sample_size`, but keep that outside the published repo surface.

## Why PubAnnotation Is Kept Separate

This repository already includes:

- datasets
- schemas
- guideline files
- refinement code
- valid-set annotation code

So PubAnnotation is intentionally used only for the final evaluation-facing step. That separation keeps the reproduction code self-contained while still giving readers a shared place to inspect and compare results.
