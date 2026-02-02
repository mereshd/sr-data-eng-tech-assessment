## Writeup (please keep this short)

We’re evaluating how you think, communicate, and make tradeoffs. Bullet points are great.

Aim for ~1–2 pages.

---

## 1) What did you build?

Describe your pipeline flow at a high level (inputs → processing → outputs).

**Answer:**


---

## 2) What output did you produce?

What tables did you create in `output/warehouse.duckdb`? For the key output table(s), state:

- what each row represents (in plain English)
- primary keys / natural keys you rely on
- any important assumptions

**Answer:**


---

## 3) Incremental + idempotent behavior

Assume files arrive in two steps:

- `raw_input_20260123` first
- then `raw_input_20260124` (includes corrections + new data)

Explain:

- how you avoid double-counting on re-run
- how you handle late-arriving corrections (what is “latest wins”, and what key/grain makes that safe?)
- what happens if the *same filename* is resent with different content (even if you didn’t implement it)

**Answer:**


---

## 4) Data quality decisions

List 5–10 concrete data issues you saw in the raw inputs and how you handled each:

- reject vs quarantine vs “allow with warning”
- how you made issues debuggable (file/row pointers, issue types, severity, etc.)

**Answer:**


---

## 5) Client-facing: onboarding questions + debug playbook

Pretend you’re leading the customer implementation call.

### A) Questions you’d ask (8–12)

Examples: “What does delivery_date mean?”, “How are corrections sent?”, “What store identifier is canonical?”, “Do you have a store master / item master?”, etc.

**Answer:**


### B) Debug playbook (when numbers don’t match)

How would you trace a discrepancy from raw file → staged/model → final spend table? What queries/steps would you run?

**Answer:**


### C) Explain 3 concrete issues from this dataset to a non-technical stakeholder

Pick 3 issues you actually observed (aliases, missing fields, corrections, negative qty, schema drift) and explain:

- what happened
- how it impacts reported spend
- what you did (or would do) to make it safe

**Answer:**


---

## 6) If this were production (brief)

What would you do next with more time? (orchestrator, storage layout, monitoring/alerts, scaling/cost, tests)

**Answer:**

