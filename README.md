# Sightline OS — Sr Data Engineer assessment (2 hours)

You’re building a small, local ingestion pipeline that turns messy distributor invoice CSVs into a queryable DuckDB “warehouse”. Here is the setup:

- **Step 0**: We have raw files from our client in `data/raw_inputs/`.
- **Step 1**: We use `transfer_input_to_s3` to simulate those files arriving in our “S3” bucket (`data/s3/`).
- **Step 2**: When files are received in the S3 folder, we automatically ingest them into DuckDB (`output/warehouse.duckdb`) and move the processed files to a `processed/` subfolder within `data/s3/`
  - --> This is the only step you should build/modify. Do not change Step 0 or Step 1.

## Context

At Sightline, customers send us messy supply-chain data (schema drift, late corrections, duplicates, inconsistent identifiers). We need numbers that customers trust. This assessment uses a simplified but realistic slice: **outbound invoices** (delivery cases and spend data at item x store x distributor level).

## The task

You will build the ingestion pipeline code in: `candidate_pipeline/`.

When we run `python -m scaffolding.transfer_input_to_s3 ...`, your pipeline entrypoint should run and:

1) ingest newly-arrived files from `data/s3/{partner}/{org}/pending/`
2) write/update the DuckDB database at `output/warehouse.duckdb`
3) leverage the mapping files in `data/mappings/` to handle messy identifiers / UOM variants
4) on success, move processed files to `data/s3/{partner}/{org}/processed/`

### Pipeline entrypoint (required)

Your pipeline must be runnable with:

```bash
python -m candidate_pipeline run
```

## What we provide

- **Raw inputs** (two “arrival bundles”):
  - `data/raw_inputs/raw_input_20260123/`
  - `data/raw_inputs/raw_input_20260124/`
- **Mappings** in `data/mappings/` — **you should use these**:
  - `data/mappings/stores.csv`: map `store_code` from the invoice files to a canonical `store_id`
  - `data/mappings/uom_conversions.csv`: normalize UOM variants (e.g. `ea` vs `EA` vs `EACH`, `LBS` → `LB`)
  - `data/mappings/distributors.csv`: validate/standardize distributor codes (optional, but expected to be used for checks)
- **Scaffolding script** to copy a raw_input bundle into the simulated S3 workspace (see below)

The raw data intentionally includes messy realities:

- Store code aliases (e.g. `NYC001` vs `NYC-001`)
- Credits/returns (negative quantities)
- Late-arriving corrections (a later file updates earlier values)
- Mild schema drift (extra columns like `promo_discount` / `tax`)

## How to run it (end-to-end)

```bash
cd sr-data-eng-tech-assessment

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Simulate first input arriving into “S3” (this should trigger your pipeline)
python -m scaffolding.transfer_input_to_s3 --raw_input raw_input_20260123

# Simulate second input arriving (append into S3; this should trigger your pipeline)
python -m scaffolding.transfer_input_to_s3 --raw_input raw_input_20260124 --append
```

The simulated S3 workspace lives at `data/s3/` and follows this layout:

`{partner}/{org_id__customer}/pending/*.csv`

### Data folders (what’s what)

- `data/raw_inputs/`: the original “client” files (fixed; do not edit)
- `data/s3/`: the simulated S3 bucket (runtime workspace; created by Step 1)
- `data/mappings/`: customer canonical data you should use for mapping/normalization (stores, distributors, UOM)

After a successful run, your pipeline should move ingested files into:

`{partner}/{org_id__customer}/processed/*.csv`

Do **not** delete or edit the raw inputs under `data/raw_inputs/`.

## What you deliver

### 1) Pipeline code + CLI

- Your pipeline code lives in `candidate_pipeline/`.
- It must provide a working entrypoint at `python -m candidate_pipeline run`.
- Provide clear CLI logging: processed files, success/failure, and counts of ingested/deduped/dropped rows.

### 2) Output file

- `output/warehouse.duckdb`

### 3) Output table

Inside `output/warehouse.duckdb`, create a table named **`fact_spend_daily`** that answers:
“How much did we buy (quantity + spend) per day, per store, per item?”

At minimum, it must contain these fields:
- `org_id`
- `business_date` (a date you choose for reporting; explain whether you use invoice date vs delivery date)
- `store_id` (a stable store identifier; if you can’t map it, use a consistent placeholder and explain it)
- `item_number` (the item identifier from the file; keep it consistent across runs)
- `quantity` (numeric)
- `spend_usd` (numeric)

### 4) Required behavior

- **Idempotent**: running the transfer script multiple times must not create duplicate data in the DB.
- **Pending vs processed**:
  - files should only move from `pending/` → `processed/` after successful processing
  - if a file isn’t processed or fails, it should remain in `pending/`
- **Corrections**: handle the correction file(s) consistently (document your rule).
- **Testing**: include at least a minimal test(s) that gives us confidence your pipeline works (smoke test is fine).

## Deliverables

Submit either a zip of this folder or a repo link including:
- your `candidate_pipeline/` code
- `output/warehouse.duckdb`
- `deliverables/WRITEUP.md`

See `deliverables/DELIVERABLES.md` for the exact checklist.

## Tools / constraints

- Python 3.10+ (3.11 recommended)
- Use any libraries you want
- You may use an LLM. **However, you must understand everything you submit** (code + SQL + approach) and be able to explain and defend your decisions live.
- Keep it local. Don’t set up cloud infra.


