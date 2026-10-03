# Runbook — `notifybot_builder.py`

## 1. Purpose

`notifybot_builder.py` is the **join step** of the pipeline. It does **not** talk
to OpenShift. It reads three files that already exist and produces a single flat
file, `notifybot.csv`, used by the downstream notification process ("notifybot").

For each namespace row in `notification.csv` it:

1. Looks up the **appid** in `Managed_Segments.xlsx` (key column `Application Id`)
   and appends the application details.
2. Looks up the **cluster** in `inventory.csv` (key column `cluster`) and appends
   the cluster details.
3. Extracts the **SOEID** (2 letters + 5 digits) from the owner / support-manager /
   app-manager fields, turns each into `<soeid>@citi.com`, and merges them into the
   recipient list.
4. Emits the recipient list as the **`email`** column: all lower-case, `;`-separated,
   de-duplicated, no trailing `;`.

> The producer script `notification_inventory.py` is separate and unchanged; this
> runbook covers only the join step.

---

## 2. Inputs

| File | Format | Key column | Produced by |
|---|---|---|---|
| `notification.csv` | CSV | `appid`, `cluster` | `notification_inventory.py` |
| `Managed_Segments.xlsx` | XLSX (first sheet) | `Application Id` | Managed-Segments export |
| `inventory.csv` | CSV | `cluster` | Cluster inventory |

**`notification.csv` expected header**

```
time,cluster,namespace,env,appid,ids
```

**`Managed_Segments.xlsx` columns used** (others pass through automatically)

- `Application Id` — join key (matched exactly; numeric cells like `123456.0`
  are normalized to `123456`)
- `Primary Business/Information Owner` — SOEID extracted, e.g. `Black, Tamara (TL68763)` → `tl68763@citi.com`
- `Support Manager` — SOEID extracted
- `Application Manager SOEID` — already a bare token (e.g. `MP06424`)

**`inventory.csv` columns** (typical)

```
cluster,cluster_type,dc,env,region,sectory,tagged
```

---

## 3. Output — `notifybot.csv`

Column order = notification columns (with `ids` renamed to **`email`**), then the
spreadsheet detail columns, then the inventory detail columns:

```
time,cluster,namespace,env,appid,email,
Application Name,Acronym,Technology Region,Business Criticality,Franchise Critical,
Primary Business/Information Owner,Support Manager,Application Manager,
Application Manager SOEID,MAS Critical,Technology Managed Seg Lvl 2,
Root Business Aligned Managed Segment Level,
cluster_type,dc,inv_env,region,sectory,tagged
```

Notes:

- **`email`** — merged recipients: notification edit/view ids first, then the
  three SOEID emails; all lower-cased, `;`-separated, de-duplicated.
- **`inv_env`** — inventory's `env` column is renamed on output because
  `notification.csv` already has an `env` column (collision handling; the
  spreadsheet uses a `seg_` prefix under the same rule).
- Detail columns are passed through unchanged (real spacing in names preserved;
  comma-bearing values are quoted by the CSV writer).

---

## 4. Prerequisites

- Python 3.6+
- Modules: **`openpyxl`** (only third-party dependency)

```bash
pip install openpyxl
# or, for the whole pipeline:
pip install -r requirements.txt
```

No `oc` login, cluster access, or network is required for this step.

---

## 5. Usage

```bash
python3 notifybot_builder.py \
  -n /data/OSE/output/notification.csv \
  -s /data/scripts/inventory/Managed_Segments.xlsx \
  -i /data/scripts/inventory/inventory.csv \
  -o /data/OSE/output/notifybot.csv
```

### Arguments

| Flag | Long | Required | Description |
|---|---|---|---|
| `-n` | `--notification` | yes | Path to `notification.csv` |
| `-s` | `--segments` | yes | Path to `Managed_Segments.xlsx` |
| `-i` | `--inventory` | yes | Path to `inventory.csv` |
| `-o` | `--output` | no | Output file or folder. A folder gets `notifybot.csv` appended. Default: `/data/OSE/output/notifybot.csv` |
| | `--log-level` | no | `DEBUG` / `INFO` / `WARNING` / `ERROR` (default `INFO`) |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — at least one row written |
| `1` | Failure — missing input file, empty/invalid notification.csv, key column not found, or no rows written |

---

## 6. What a healthy run looks like

```
INFO - NOTIFYBOT FLAT-FILE BUILD
INFO - Managed_Segments: 1450 applications, 12 detail columns
INFO - inventory: 38 clusters, 6 detail columns
INFO - ============================================================
INFO - notifybot rows written: 512
INFO -   segment matches:  498 hit / 14 miss
INFO -   inventory matches: 512 hit / 0 miss
INFO -   SOEID emails merged into ids: 1490 across 498 rows
INFO - Output: /data/OSE/output/notifybot.csv
INFO - ============================================================
INFO - Elapsed: 0.6s

SUCCESS: notifybot.csv written -> /data/OSE/output/notifybot.csv
```

**Post-run checks**

1. `head -1 notifybot.csv` — confirm the `email` column is present.
2. Spot-check one row: `email` is lower-case, `;`-separated, no trailing `;`.
3. Compare `notifybot rows written` against `notification.csv` row count — they
   should match (every notification row is carried through).

---

## 7. Behaviour reference (design decisions)

| Topic | Behaviour |
|---|---|
| **appid match** | Exact full-value equality (raw + normalized). A 6-digit appid never matches a 7-digit `Application Id`. Numeric cells normalized (`123456.0` → `123456`); text ids keep leading zeros. |
| **appid = NA / blank / not found** | Application detail cells left blank; row kept. |
| **cluster not found** | Inventory detail cells left blank; row kept. |
| **SOEID regex** | `\b[A-Za-z]{2}\d{5}\b` — 2 letters + 5 digits, bounded so a 6+-digit run gives no false match. |
| **SOEID email case** | Lower-cased before `@citi.com`. |
| **email de-dup** | Case-insensitive; existing ids listed first, then SOEID emails. |
| **email separator** | `;`, no trailing `;` (constants `IDS_SEPARATOR`, `IDS_TRAILING`). |
| **Duplicate keys** | Duplicate `Application Id` or `cluster` → last occurrence wins, logged as a warning. |
| **Whitespace** | Header names and join keys are space-normalized (trim + collapse internal runs), so `Application  Id` or `gcbsg01p ` still match. Display values keep their real spacing. |
| **Column name collision** | Incoming column that clashes with an existing one is prefixed: `seg_` (spreadsheet) / `inv_` (inventory). This is why inventory `env` becomes `inv_env`. |

---

## 8. Configuration knobs (top of the script)

| Constant | Default | Effect |
|---|---|---|
| `SEGMENTS_KEY` | `"Application Id"` | Spreadsheet join-key column name |
| `INVENTORY_KEY` | `"cluster"` | Inventory join-key column name |
| `SOEID_SOURCE_COLUMNS` | owner / support mgr / app-mgr SOEID | Columns scanned for SOEIDs |
| `IDS_INPUT_COL` / `IDS_OUTPUT_COL` | `"ids"` / `"email"` | Source column and output column name |
| `IDS_SEPARATOR` | `";"` | Separator between ids |
| `IDS_TRAILING` | `False` | Add a trailing separator when `True` |
| `EMPTY_APPIDS` | `{"", "na", "n/a", ...}` | appid values treated as "no application" |
| `DEFAULT_OUTPUT_DIR` | `/data/OSE/output` | Output folder when `-o` omitted |

---

## 9. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `key column 'Application Id' not found` | Spreadsheet header differs or wrong sheet is first | Check the first sheet's header row; update `SEGMENTS_KEY` if renamed |
| `key column 'cluster' not found` | inventory.csv header differs | Check header; update `INVENTORY_KEY` if renamed |
| `expected an 'appid'/'cluster' column` | notification.csv header changed | Confirm it came from the current `notification_inventory.py` |
| Many `segment miss` | appids not present in the spreadsheet, or stored differently | Verify `Application Id` values; remember matching is exact |
| `inventory miss` for a cluster | cluster absent from inventory.csv, or name mismatch | Add/fix the cluster row |
| `email` field has commas / looks wrong | Wrong separator expected downstream | Adjust `IDS_SEPARATOR` / `IDS_TRAILING` |
| `ModuleNotFoundError: openpyxl` | Dependency missing | `pip install openpyxl` |
| No output file | `notifybot rows written: 0` (empty notification.csv) | Confirm the producer step ran and wrote rows |

---

## 10. Pipeline context

```
notification_inventory.py  ->  notification.csv  \
                                                   \
Managed_Segments.xlsx  ----------------------------->  notifybot_builder.py  ->  notifybot.csv
                                                   /
inventory.csv  ------------------------------------/
```

Run order: `notification_inventory.py` first (produces `notification.csv`), then
`notifybot_builder.py` to join it with the two reference files.
