## Writeup (please keep this short)

We're evaluating how you think, communicate, and make tradeoffs. Bullet points are great.

Aim for ~1–2 pages.

---

## 1) What did you build?

Describe your pipeline flow at a high level (inputs → processing → outputs).

**Answer:**

A modular Python pipeline (`candidate_pipeline/`) with 5 modules:

1. **Discover** (`ingest.py`): Scans `data/s3/{partner}/{org}/pending/*.csv` for new files. Extracts metadata (partner, org_id, correction flag) from the folder path and filename.
2. **Load**: Reads each CSV as all-string columns to avoid premature type coercion. Selects only expected columns (ignoring schema drift like `tax`, `promo_discount`).
3. **Transform** (`transform.py`): Cleans numerics (strips `$`, `,`, spaces), parses dates (multi-format via `dateutil`), normalizes store codes (hyphen-agnostic matching to `stores.csv`), normalizes UOM variants (via `uom_conversions.csv`), uppercases currency, and computes missing `extended_price`.
4. **Validate** (`quality.py`): Deduplicates exact-duplicate rows. Quarantines rows where both dates are unparseable. Flags (but keeps) negative quantities, zero quantities, and unmapped stores.
5. **Write** (`warehouse.py`): Uses delete-then-insert into DuckDB staging + fact tables (delete any prior rows for the same `source_file`, then insert fresh). Handles corrections by deleting prior rows for corrected invoice_ids. Moves processed files to `processed/`.

---

## 2) What output did you produce?

**Answer:**

Four tables in `output/warehouse.duckdb`:

- **`fact_spend_daily`** (primary output): Each row = one invoice line item. Natural key: `(org_id, invoice_id, item_number, store_id, distributor_code)`. Contains `business_date` (= delivery_date), `quantity`, `spend_usd`.
- **`stg_invoice_lines`**: Full audit trail with raw + normalized values, quality flags, and source_file traceability.
- **`quarantine`**: Rejected rows with issue_type and the original raw data as JSON.
- **`pipeline_log`**: File-level processing stats (rows ingested/quarantined/deduped).

**Key assumption**: `business_date` = `delivery_date` (when goods arrived), not `invoice_date` (when invoice was issued). If `delivery_date` is invalid, falls back to `invoice_date`.

---

## 3) Incremental + idempotent behavior

**Answer:**

- **Avoiding double-counting**: After successful processing, files move from `pending/` to `processed/`. Re-running finds no pending files → no-op. DB-level safety: before inserting rows from a file, we delete any prior rows with that `source_file` key, so partial failures are safely re-processable.
- **Late-arriving corrections**: Files with `_CORRECTION` in the filename trigger deletion of all existing rows for the corrected `invoice_id`s across all tables before inserting the new data. "Last write wins" at `invoice_id` granularity.
- **Same filename, different content**: Currently not handled — the file would be in `processed/` so the new version wouldn't be picked up. To handle this in production, I'd hash file contents and compare against a `file_hash` column in `pipeline_log`, re-processing if the hash differs.

---

## 4) Data quality decisions

**Answer:**

| # | Issue | Action | Rationale |
|---|-------|--------|-----------|
| 1 | Multiple date formats (`2026-01-05`, `01/05/2026`, `2026/01/05`) | **Allow** — parse with `dateutil` | US context → `dayfirst=False` |
| 2 | Invalid date `2026-01-35` (INV-1009) | **Allow with fallback** — use `delivery_date` | Only quarantine if BOTH dates are bad |
| 3 | Store code aliases (`NYC001` vs `NYC-001`) | **Allow** — strip hyphens for matching | Maps to canonical `store_id` |
| 4 | Unmapped store `NYC-999` | **Allow with warning** — placeholder `UNMAPPED__NYC-999` | Flagged in `quality_flags`; preserves data |
| 5 | UOM variants (`EACH`, `ea`, `LBS`, `CASE`) | **Allow** — normalize via `uom_conversions.csv` | Maps to canonical `EA`, `LB`, `CS` |
| 6 | Price with `$` prefix (`"$2.35"`) | **Allow** — strip before parsing | Common in Sysco files |
| 7 | Quantity with separators (`"1 000"`, `"1,000"`) | **Allow** — strip commas/spaces | Thousands formatting |
| 8 | Missing `extended_price` | **Allow** — compute as `qty * unit_price` | One GFS row had empty value |
| 9 | Exact duplicate rows (INV-1003, INV-1008) | **Deduplicate** — keep first, log count | 2 duplicate pairs found |
| 10 | Negative quantities (-25, -50) | **Allow with flag** | Valid credits/returns |
| 11 | Zero quantity (INV-1013, 0 cilantro) | **Allow with flag** | May be placeholder or cancelled line |
| 12 | Schema drift (`tax`, `promo_discount`) | **Ignore extra columns** | Only select expected columns |
| 13 | Currency case (`usd` vs `USD`) | **Allow** — uppercase normalize | |
| 14 | Correction file for INV-1007 | **Replace** — delete + reinsert | Filename convention `_CORRECTION` |

All issues are debuggable via `stg_invoice_lines.quality_flags` (comma-separated flag strings like `NEGATIVE_QTY,UNMAPPED_STORE`) and the `quarantine` table (with `issue_type`, `issue_detail`, and full raw row as JSON).

---

## 5) Client-facing: onboarding questions + debug playbook

### A) Questions you'd ask (8–12)

**Answer:**

1. What does `delivery_date` represent — actual delivery or scheduled delivery? Is it always populated?
2. Is `invoice_date` ever different from `delivery_date`? Which should we use for spend reporting?
3. How are corrections sent? Is the `_CORRECTION` filename suffix a standard convention, or can corrections arrive as regular files?
4. When a correction arrives, does it replace the entire invoice or just specific line items?
5. Do you have a canonical item master we can use for item_number mapping? (Different distributors use different codes for the same product.)
6. What store identifier is authoritative — `store_code`, `store_id`, or something else? How do we handle new stores?
7. Can the same invoice_id appear across multiple distributors, or is it globally unique?
8. Are duplicate rows in invoice files intentional (e.g., split shipments) or data entry errors?
9. What is the expected behavior for negative quantities — are these always returns/credits?
10. Do you expect us to track `promo_discount` and `tax` columns, or are they informational only?
11. What is the expected cadence of file delivery? Daily? How soon after delivery do files arrive?
12. Is there a reconciliation report we can use to validate our totals against your system of record?

### B) Debug playbook (when numbers don't match)

**Answer:**

1. **Identify the discrepancy**: Which store, date range, item, or invoice is off?
2. **Check `fact_spend_daily`**: `SELECT * FROM fact_spend_daily WHERE store_id = ? AND business_date = ?` — see what's in the final table.
3. **Trace to staging**: `SELECT * FROM stg_invoice_lines WHERE invoice_id = ?` — compare raw vs normalized values. Check `quality_flags` for any transformations applied.
4. **Check for corrections**: `SELECT * FROM pipeline_log WHERE source_file LIKE '%CORRECTION%'` — was data replaced by a later correction?
5. **Check quarantine**: `SELECT * FROM quarantine WHERE source_file = ?` — were any rows rejected?
6. **Check deduplication**: Compare `rows_loaded` vs `rows_ingested` in `pipeline_log` — how many rows were deduped?
7. **Go to source**: Read the original CSV from `data/s3/{partner}/{org}/processed/` — compare raw values against staged data.

### C) Explain 3 concrete issues from this dataset to a non-technical stakeholder

**Answer:**

**1. Store Code Aliases (NYC001 vs NYC-001)**
- **What happened**: The same store (East Village) appears as "NYC001" in some invoices and "NYC-001" in others. If we treat these as different stores, spend gets split across phantom locations.
- **Impact**: Without normalization, you'd see two separate "stores" in reports, each showing roughly half the actual spend.
- **What we did**: We built a matching rule that ignores hyphens, so both variants map to the same canonical store. All spend for East Village appears in one place.

**2. Late-Arriving Correction (INV-1007)**
- **What happened**: On Jan 6, an invoice was filed showing 1,000 limes. The next day, a corrected version arrived showing 950 limes — the original count was wrong.
- **Impact**: If we kept both, the lime spend would be double-counted ($190 + $180.50). If we only kept the original, the numbers would be wrong by $9.50.
- **What we did**: The correction file replaces the original. Our system detects the `_CORRECTION` marker and swaps in the updated numbers, so your reports always reflect the latest truth.

**3. Duplicate Invoice Lines (INV-1003 TOGO BOX)**
- **What happened**: The same line item (200 to-go boxes at $0.11 each) appeared twice in one invoice file — likely a data export glitch.
- **Impact**: Without deduplication, you'd see $44 in to-go box spend instead of the actual $22.
- **What we did**: We detect and remove exact-duplicate rows within the same invoice. The pipeline logs how many duplicates were removed so you can review.

---

## 6) If this were production (brief)

**Answer:**

- **Orchestration**: Replace the scaffolding script with Airflow/Dagster DAGs triggered by S3 event notifications (or on a schedule). Add retry logic with exponential backoff.
- **Storage**: Move from local DuckDB to a cloud warehouse (Snowflake/BigQuery/Redshift). Use Parquet on S3 as the staging layer. Partition fact tables by `business_date`.
- **Monitoring/Alerts**: Track row counts, quarantine rates, and processing latency. Alert on: quarantine rate > 5%, no files received in expected window, fact table row count drops unexpectedly.
- **Data quality**: Add a reconciliation step comparing our computed totals against client-provided control totals (e.g., monthly invoice summaries from the distributor portal — if the numbers diverge, something was missed or double-counted). Add dbt tests for referential integrity (every `store_id` in the fact table maps to a known store) and row-level validation (e.g., flag rows where a distributor-provided `extended_price` drifts from `quantity * unit_price` — could indicate volume discounts or data errors).
- **Scaling**: Parallelize file processing (each file is independent). For very large files, switch from pandas to DuckDB-native CSV reading or Polars.
- **Tests**: Add contract tests for incoming CSV schemas (catch distributor format changes before bad data enters the pipeline). Add regression tests against known-good snapshots (diff fact table output after every code change to catch subtle drift). Add integration tests that validate the full pipeline against expected business outcomes — total spend per store, correction behavior, quarantine contents.
- **Item master**: Build an item mapping table to normalize item_number across distributors (e.g., `00012345` and `CHKN-THIGH-10` are both chicken thighs).
