## Deliverables (what to submit)

Please submit either:

- a zip of the `sr-data-eng-tech-assessment/` folder, or
- a repo link (GitHub/GitLab) with this folder and your changes.

Include the following **three** items:

### 1) Working pipeline implementation

Implement your pipeline under:

- `candidate_pipeline/`

Your solution should be runnable with:

```bash
python -m scaffolding.transfer_input_to_s3 --raw_input raw_input_20260123
python -m scaffolding.transfer_input_to_s3 --raw_input raw_input_20260124 --append
```

Note: `transfer_input_to_s3` **automatically triggers** your pipeline (`python -m candidate_pipeline run`) after copying files into `data/s3/.../pending/`.
You can also rerun the pipeline manually at any time:

```bash
python -m candidate_pipeline run
```

### 2) Produced outputs

Commit or include the generated `output/` artifacts from your last run:

- `output/warehouse.duckdb`

### 3) Written solution: `WRITEUP.md`

Keep it short (~1–2 pages). Use the guided prompts in the template.

## Where to write your docs

The templates live in this folder:

- `deliverables/WRITEUP.md`

