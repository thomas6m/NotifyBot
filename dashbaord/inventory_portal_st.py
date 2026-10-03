"""
NotifyBot Inventory Summary (Streamlit)

  pip install -r requirements.txt
  streamlit run inventory_portal_st.py

First CSV column = epoch time; a column named "email" holds ';'-separated addresses.

Trend: each refresh archives the previous file as  inventory.csv-<epoch>  in the same
folder. Every such snapshot is read to plot how the full-inventory KPIs change over time.

Snapshot KPIs are cached in  inventory.csv-<epoch>.meta.json  sidecar files (see
inventory_meta.py) so old CSVs are not re-parsed on every load.
"""
import fnmatch
import functools
import html
import json
import os
import re
import sys
from collections import Counter

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from inventory_meta import (
    KPI_LABELS, build_meta, diff_by, diff_inventories, find_col, history, kpis, parse_csv,
    union_count, valid_meta,
)

try:  # same validator notifybot.py uses; optional for the portal
    from email_validator import validate_email as _validate_email
except ImportError:
    _validate_email = None

FILTER_MODES = ["Dropdown", "filter.txt"]


# ------------------------------------------------------------------ filter.txt engine
# Mirrors notifybot.py's filter.txt handling (matches_filter_conditions,
# validate_filter_syntax, apply_filter_logic) so the portal selects the same rows
# and recipients NotifyBot would. notifybot.py is NOT imported or changed.
#   comma inside a line = AND, new line = OR (multi mode: one email per line)
#   '#' and blank lines ignored; operators =  !=  =~  !~ (regex anchored,
#   case-insensitive); after '=', * ? [seq] [!seq] are wildcards; a condition
#   with no operator is searched in every column.
# Speed: each condition is tested once per DISTINCT value of its column and mapped
# back with isin(), instead of row by row.
FTXT_OPERATORS = ("=~", "!~", "!=", "=")  # the order notifybot.py checks them in
FTXT_HINT = "comma = AND · new line = OR · = != =~ !~ · wildcards * ? [..] · # comment"
FTXT_BAD_EMAIL_CHARS = ("|", "`", "$", "\\")
INTERNAL_COLS = ("_ts", "_emails")


def ftxt_active_lines(text):
    """(line_number, line) for every non-blank, non-comment line."""
    return [(i, ln.strip()) for i, ln in enumerate(text.splitlines(), 1)
            if ln.strip() and not ln.strip().startswith("#")]


def ftxt_conditions(line):
    """A line's AND conditions: split on EVERY comma, like notifybot.py."""
    return [c.strip() for c in line.split(",") if c.strip()]


def ftxt_parse(cond):
    """(field, operator, value) exactly as notifybot.py's parse_condition.
    field is None when there is no operator (search every column, '*' match)."""
    cond = cond.strip()
    for op in ("=~", "!~", "!="):
        if op in cond:
            k, v = cond.split(op, 1)
            return k.strip(), op, v.strip().strip("\"'")
    if "=" in cond:
        k, v = cond.split("=", 1)
        v = v.strip().strip("\"'")
        return k.strip(), ("*" if any(ch in v for ch in "*?[") else "="), v
    return None, "*", cond


def ftxt_value_matches(op, pattern, value):
    text = str(value)
    if op == "=":
        return text.lower() == pattern.lower()
    if op == "!=":
        return text.lower() != pattern.lower()
    if op in ("=~", "!~"):
        try:
            hit = bool(re.fullmatch(pattern, text, re.IGNORECASE))
        except re.error:
            return False  # notifybot.py treats an invalid regex as "no match" for both
        return hit if op == "=~" else not hit
    return fnmatch.fnmatch(text.lower(), pattern.lower())


def ftxt_validate(text, columns):
    """(errors, hints). Errors are the ones notifybot.py's validate_filter_syntax
    reports (it refuses to send when there are any); hints are extra help."""
    errors, hints = [], []
    cols = set(columns)
    by_lower = {str(c).strip().lower(): c for c in columns}
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for cond in (c.strip() for c in line.split(",")):
            if not cond:
                continue
            op = next((o for o in FTXT_OPERATORS if o in cond), None)
            if op is None:
                if not any(ch in cond for ch in "*?["):
                    errors.append(f"Line {i}: No valid operator found in '{cond}'. "
                                  "Use =, !=, =~, !~, or wildcards (*,?,[])")
                continue
            field, value = (p.strip() for p in cond.split(op, 1))
            if not field:
                errors.append(f"Line {i}: Empty field name in '{cond}'")
            if not value:
                errors.append(f"Line {i}: Empty value in '{cond}'")
            if field and field not in cols:
                errors.append(f"Line {i}: Field '{field}' not found in inventory.csv headers")
                if field.startswith("﻿"):
                    hints.append("The file starts with a BOM (saved as 'UTF-8 with BOM'). "
                                 "Re-save it as plain UTF-8.")
                elif field.strip().lower() in by_lower:
                    hints.append(f"Line {i}: did you mean '{by_lower[field.strip().lower()]}' "
                                 f"instead of '{field}'? Field names are case-sensitive.")
            if op in ("=~", "!~"):
                vc = value.strip("\"'")
                try:
                    re.compile(vc)
                except re.error as e:
                    errors.append(f"Line {i}: Invalid regex pattern '{vc}': {e}")
    return errors, hints


def ftxt_warnings(text):
    """Valid but probably unintended."""
    return [f"Line {num}: '{cond}' has no field name, so it is matched against EVERY "
            "column (including email and time)."
            for num, line in ftxt_active_lines(text)
            for cond in ftxt_conditions(line) if ftxt_parse(cond)[0] is None]


def _col_values(df, col):
    return df[col].astype(object).where(df[col].notna(), "").astype(str)


def ftxt_condition_mask(df, cond):
    field, op, pattern = ftxt_parse(cond)
    if field is None:
        cols = [c for c in df.columns if c not in INTERNAL_COLS]  # any column may match
    elif field in df.columns:
        cols = [field]
    else:
        return pd.Series(False, index=df.index)  # unknown field: matches nothing
    mask = pd.Series(False, index=df.index)
    for col in cols:
        values = _col_values(df, col)
        ok = {v for v in values.unique() if ftxt_value_matches(op, pattern, v)}
        mask |= values.isin(ok)
    return mask


def ftxt_line_masks(df, text):
    """[(line_number, line, mask)]: each mask is the AND of the line's conditions."""
    out = []
    for num, line in ftxt_active_lines(text):
        mask = pd.Series(True, index=df.index)
        for cond in ftxt_conditions(line):
            mask &= ftxt_condition_mask(df, cond)
        out.append((num, line, mask))
    return out


def ftxt_combine(df, masks):
    """OR of the lines (no active lines -> all rows)."""
    if not masks:
        return pd.Series(True, index=df.index)
    out = pd.Series(False, index=df.index)
    for _, _, m_ in masks:
        out |= m_
    return out


@functools.lru_cache(maxsize=None)
def ftxt_is_valid_email(email):
    """notifybot.py's is_valid_email rules (email_validator + sendmail-safety checks)."""
    e = email.strip()
    if _validate_email is not None:
        try:
            _validate_email(e, check_deliverability=False)
        except Exception:
            return False
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e):
        return False
    return len(e) <= 320 and not e.startswith("-") and not any(ch in e for ch in FTXT_BAD_EMAIL_CHARS)


def ftxt_recipients(df_matched, email_col="email"):
    """The TO list notifybot.py builds from these rows (single mode): split on ';' / ',',
    validated, de-duplicated case-insensitively, first spelling and file order kept.
    Returns (recipients, invalid) or None when there is no column named exactly 'email'."""
    if email_col not in df_matched.columns:
        return None
    out, seen, invalid = [], set(), set()
    for raw in df_matched[email_col]:
        for e in (x.strip() for x in re.split(r"[;,]", raw if isinstance(raw, str) else "")):
            if not e or e.lower() in seen:
                continue
            if ftxt_is_valid_email(e):
                seen.add(e.lower())
                out.append(e)
            else:
                invalid.add(e)
    return out, sorted(invalid)


def ftxt_line_breakdown(df, masks):
    """Per line: rows, valid recipients, recipients reached only through that line."""
    sets = []
    for _, _, m_ in masks:
        emails = frozenset().union(*df.loc[m_, "_emails"]) if m_.any() else frozenset()
        sets.append(frozenset(e for e in emails if ftxt_is_valid_email(e)))
    rows = []
    for i, (num, line, m_) in enumerate(masks):
        others = frozenset().union(*(s for j, s in enumerate(sets) if j != i))
        rows.append({"Line": num, "Condition": line, "Rows": int(m_.sum()),
                     "Recipients": len(sets[i]), "Only via this line": len(sets[i] - others)})
    return pd.DataFrame(rows, columns=["Line", "Condition", "Rows", "Recipients", "Only via this line"])

st.set_page_config(page_title="NotifyBot Inventory Summary", page_icon="📧", layout="wide")

# one colour per KPI, used by the cards and the trend chart
KPI_COLORS = {
    "Clusters": "#2557d6",
    "Cluster + namespace": "#0e9384",
    "Namespaces": "#7a5af8",
    "App IDs": "#dc6803",
    "Unique emails": "#dd2590",
}
_accent_rules = "\n".join(
    f'[class*="st-key-kpi_"] [data-testid="stColumn"]:nth-child({i}) {{ --accent: {c}; }}'
    for i, c in enumerate(KPI_COLORS.values(), 1)
)
st.markdown(f"""<style>
/* ---------- header banner */
.nb-banner {{
  background: linear-gradient(120deg, #1a3fa8 0%, #2557d6 55%, #4f7cf0 100%);
  color: #fff; border-radius: 14px; padding: 22px 16px 18px; margin: -8px 0 18px;
  text-align: center; box-shadow: 0 6px 18px rgba(37, 87, 214, .25);
}}
.nb-banner h1 {{ color: #fff; margin: 0; padding: 0; font-size: 2.1rem; letter-spacing: .3px; }}
.nb-banner.nb-archived {{
  background: linear-gradient(120deg, #7a2e0e 0%, #b54708 55%, #dc6803 100%);
  box-shadow: 0 6px 18px rgba(181, 71, 8, .25);
}}
.nb-banner.nb-compare {{
  background: linear-gradient(120deg, #3b1f8f 0%, #6941c6 55%, #8b6cf0 100%);
  box-shadow: 0 6px 18px rgba(105, 65, 198, .25);
}}
.st-key-kpi_cmp [data-testid="stColumn"]:nth-child(1) {{ --accent: #067647; }}
.st-key-kpi_cmp [data-testid="stColumn"]:nth-child(2) {{ --accent: #b42318; }}
.st-key-kpi_cmp [data-testid="stColumn"]:nth-child(3) {{ --accent: #dc6803; }}
.st-key-kpi_cmp [data-testid="stColumn"]:nth-child(4) {{ --accent: #0e9384; }}
.st-key-kpi_cmp [data-testid="stColumn"]:nth-child(5) {{ --accent: #dd2590; }}
.st-key-kpi_cmp [data-testid="stMetric"] {{
  background: linear-gradient(160deg, color-mix(in srgb, var(--accent) 14%, #fff) 0%, #fff 75%);
  border-top: 4px solid var(--accent);
}}
.nb-badge {{
  display: inline-block; background: rgba(255,255,255,.22); color: #fff; font-weight: 700;
  font-size: .72rem; letter-spacing: .8px; padding: 3px 9px; border-radius: 999px; margin-right: 10px;
}}
.nb-banner p {{ color: rgba(255,255,255,.82); margin: 6px 0 0; font-size: .9rem; }}

/* ---------- section headings */
.nb-section {{
  display: flex; align-items: center; gap: 10px; margin: 18px 0 8px;
  font-weight: 700; font-size: 1.02rem; color: #1d2330;
}}
.nb-section::before {{
  content: ""; width: 5px; height: 20px; border-radius: 3px; background: var(--c, #2557d6);
}}
.nb-section span {{ font-weight: 500; font-size: .82rem; color: #6b7385; }}

/* ---------- KPI cards */
{_accent_rules}
[class*="st-key-kpi_"] [data-testid="stMetric"] {{
  border-radius: 14px; padding: 16px 12px 12px; height: 100%;
  border: 1px solid color-mix(in srgb, var(--accent) 22%, transparent);
  box-shadow: 0 2px 10px rgba(29, 35, 48, .06);
  transition: transform .15s ease, box-shadow .15s ease;
}}
[class*="st-key-kpi_"] [data-testid="stMetric"]:hover {{
  transform: translateY(-2px); box-shadow: 0 8px 20px rgba(29, 35, 48, .10);
}}
.st-key-kpi_full [data-testid="stMetric"] {{
  background: linear-gradient(160deg, color-mix(in srgb, var(--accent) 14%, #fff) 0%, #fff 75%);
  border-top: 4px solid var(--accent);
}}
.st-key-kpi_sel [data-testid="stMetric"] {{
  background: #fff; border-left: 4px solid var(--accent);
}}
/* centre label, value and delta */
[class*="st-key-kpi_"] [data-testid="stMetric"] * {{ text-align: center; }}
[class*="st-key-kpi_"] [data-testid="stMetricLabel"],
[class*="st-key-kpi_"] [data-testid="stMetricValue"],
[class*="st-key-kpi_"] [data-testid="stMetricDelta"] {{
  display: flex; justify-content: center; width: 100%; margin: 0 auto;
}}
[class*="st-key-kpi_"] [data-testid="stMetricLabel"] > div {{ margin: 0 auto; }}
[class*="st-key-kpi_"] [data-testid="stMetricLabel"] p {{
  font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .6px;
  color: #5b6377;
}}
[class*="st-key-kpi_"] [data-testid="stMetricValue"] {{
  color: var(--accent); font-weight: 800; font-size: 2.2rem; line-height: 1.25;
}}
.st-key-kpi_sel [data-testid="stMetricValue"] {{ font-size: 1.8rem; }}
[class*="st-key-kpi_"] [data-testid="stMetricDelta"] {{ font-weight: 600; }}

/* ---------- tables */
.nb-table-wrap {{
  border: 1px solid #dfe4ee; border-radius: 12px; overflow: auto;
  box-shadow: 0 2px 10px rgba(29, 35, 48, .05); margin-bottom: 14px; background: #fff;
}}
table.nb-table {{
  width: 100%; border-collapse: separate; border-spacing: 0;
  font-size: .9rem; color: #1d2330; font-variant-numeric: tabular-nums;
}}
table.nb-table thead th {{
  position: sticky; top: 0; z-index: 1;
  background: linear-gradient(180deg, #1f2f57 0%, #18254a 100%); color: #fff;
  text-transform: uppercase; font-size: .72rem; font-weight: 700; letter-spacing: .7px;
  padding: 12px 14px; text-align: center; white-space: nowrap;
  border-bottom: 3px solid var(--hc, #2557d6);
}}
table.nb-table thead th:first-child {{ text-align: left; }}
table.nb-table td {{
  padding: 10px 14px; text-align: center; border-bottom: 1px solid #eef1f6; white-space: nowrap;
}}
table.nb-table td:first-child {{ text-align: left; font-weight: 600; color: #26304a; }}
table.nb-table tbody tr:nth-child(even) td {{ background: #f8fafd; }}
table.nb-table tbody tr:hover td {{ background: #eef3ff; }}
table.nb-table tbody tr:last-child td {{ border-bottom: none; }}
table.nb-table td.up {{ color: #067647; font-weight: 600; }}
table.nb-table td.down {{ color: #b42318; font-weight: 600; }}
table.nb-table td.muted {{ color: #9aa2b4; }}

/* ---------- misc */
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #eef2fb 0%, #f7f9fd 100%); }}
[data-testid="stExpander"] details {{ border-radius: 12px; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
</style>""", unsafe_allow_html=True)


def html_table(d, max_height=None):
    """Static, styled table: navy headers, centred values, zebra rows.
    KPI columns get their KPI colour under the header; 'Δ' columns are green/red."""
    def head(c):
        base = c[2:] if str(c).startswith("Δ ") else c
        color = KPI_COLORS.get(base, "#2557d6")
        return f'<th style="--hc:{color}">{html.escape(str(c))}</th>'

    def cell(c, v):
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return '<td class="muted">–</td>'
        if str(c).startswith("Δ "):
            v = int(v)
            cls = "up" if v > 0 else "down" if v < 0 else "muted"
            return f'<td class="{cls}">{"▲ " if v > 0 else "▼ " if v < 0 else ""}{abs(v):,}</td>'
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f"<td>{int(v):,}</td>" if float(v).is_integer() else f"<td>{v:,.2f}</td>"
        return f"<td>{html.escape(str(v)) or '(blank)'}</td>"

    rows = "".join(
        "<tr>" + "".join(cell(c, v) for c, v in zip(d.columns, rec)) + "</tr>"
        for rec in d.itertuples(index=False, name=None)
    )
    style = f' style="max-height:{max_height}px"' if max_height else ""
    st.markdown(
        f'<div class="nb-table-wrap"{style}><table class="nb-table"><thead><tr>'
        + "".join(head(c) for c in d.columns)
        + f"</tr></thead><tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def section(title, note="", color="#2557d6"):
    st.markdown(
        f'<div class="nb-section" style="--c:{color}">{html.escape(title)}'
        f'{f"<span>{html.escape(note)}</span>" if note else ""}</div>',
        unsafe_allow_html=True,
    )


@st.cache_resource(max_entries=3, show_spinner="Loading inventory file… (large files take a few seconds)")
def load_file(fpath, size, mtime_ns):
    """Parsed once per file version and shared by every user of the dashboard.
    Keeps at most 3 files in memory (e.g. latest + two archives being reviewed)."""
    with open(fpath, "rb") as fh:
        return parse_csv(fh.read())


@st.cache_resource(max_entries=2, show_spinner="Loading uploaded file…")
def load_upload(file_id, _upload):
    return parse_csv(_upload.getvalue())


def file_key(fpath):
    fpath = os.path.abspath(fpath)  # same file -> same cache entry, however it was named
    s_ = os.stat(fpath)
    return fpath, s_.st_size, s_.st_mtime_ns


# A filter "spec" is hashable, so it can be part of cache keys:
#   ("dropdown", ((field, pattern), ...))   sidebar pickers
#   ("filtertxt", text)                     filter.txt lines (notifybot.py semantics)
NO_FILTER = ("dropdown", ())


def spec_active(spec):
    if spec[0] == "filtertxt":
        return bool(ftxt_active_lines(spec[1]))
    return bool(spec[1])


def spec_mask(d, spec):
    """Boolean row mask of a filter spec on DataFrame d."""
    if spec[0] == "filtertxt":
        return ftxt_combine(d, ftxt_line_masks(d, spec[1]))
    mask = pd.Series(True, index=d.index)
    for f, pattern in spec[1]:
        if f in d.columns:
            mask &= match_values(d[f], pattern)
    return mask


@st.cache_resource(max_entries=16, show_spinner="Evaluating filter.txt…")
def txt_lines(key, text, _df):
    """Per-line masks of a filter.txt, cached per file + text."""
    return ftxt_line_masks(_df, text)


@st.cache_resource(max_entries=32, show_spinner="Applying filters…")
def selection(key, spec, _df):
    """Filtered rows plus everything derived from them, cached per file + filter spec,
    so switching tabs or searching emails does not recompute on 70k rows."""
    if spec[0] == "filtertxt":
        mask = ftxt_combine(_df, txt_lines(key, spec[1], _df))
    else:
        mask = spec_mask(_df, spec)
    m = _df[mask]
    cnt = Counter(e for s_ in m["_emails"] for e in s_)
    env = None
    ec = find_col(_df, "env")
    if ec and len(m):
        env = pd.DataFrame([{"Env": e or "(blank)", **kpis(g)} for e, g in m.groupby(ec)])
        env = env.sort_values("Unique emails", ascending=False)
    return m, cnt, kpis(m), env


@st.cache_resource(max_entries=32, show_spinner="Building breakdown…")
def breakdown(key, spec, by, _m):
    g = _m.groupby(by).agg(unique_emails=("_emails", union_count))
    return g.sort_values("unique_emails", ascending=False)


def match_values(series, spec):
    """'*' = everything. Otherwise comma-separated patterns, case-insensitive,
    full match, with * (any text) and ? (one char) wildcards, e.g. 'prod*, uat'."""
    pats = [p.strip().lower() for p in spec.split(",") if p.strip()] or ["*"]
    if "*" in pats:
        return pd.Series(True, index=series.index)
    rx = [re.compile(re.escape(p).replace(r"\*", ".*").replace(r"\?", ".")) for p in pats]
    ok = {v for v in series.unique() if any(r.fullmatch(v.strip().lower()) for r in rx)}
    return series.isin(ok)


def copy_button(text, label="📋 Copy"):
    """Copy button that also works when the app is served over plain http://
    (the browser Clipboard API, used by st.code, only works on https or localhost)."""
    payload = json.dumps(text).replace("</", "<\\/")
    n = text.count(";") + 1 if text else 0
    components.html(f"""
<button id="b" style="font:14px sans-serif;padding:6px 14px;border:1px solid #c9cfdb;
  border-radius:6px;background:#2557d6;color:#fff;cursor:pointer">{html.escape(label)} ({n:,})</button>
<span id="m" style="font:13px sans-serif;margin-left:10px;color:#2a7a3b"></span>
<script>
const text = {payload};
const btn = document.getElementById("b"), msg = document.getElementById("m");
function legacyCopy() {{
  const ta = document.createElement("textarea");
  ta.value = text; ta.setAttribute("readonly", "");
  ta.style.position = "fixed"; ta.style.opacity = "0";
  document.body.appendChild(ta); ta.select();
  let ok = false; try {{ ok = document.execCommand("copy"); }} catch (e) {{}}
  document.body.removeChild(ta); return ok;
}}
btn.onclick = async () => {{
  let ok = false;
  if (navigator.clipboard && window.isSecureContext) {{
    try {{ await navigator.clipboard.writeText(text); ok = true; }} catch (e) {{}}
  }}
  if (!ok) ok = legacyCopy();
  msg.style.color = ok ? "#2a7a3b" : "#b42318";
  msg.textContent = ok ? "Copied!" : "Copy blocked by the browser: select the text below and press Ctrl+C";
  setTimeout(() => msg.textContent = "", 4000);
}};
</script>""", height=45)


def filter_sidebar(fields, note="", columns=None):
    """Filter input panel in the sidebar: Dropdown pickers or an uploaded filter.txt.

    Returns (spec, problems): spec is a hashable filter spec (see NO_FILTER);
    problems lists filter.txt errors - when it is not empty, nothing should be filtered.
    `columns` = every column filter.txt may reference (defaults to `fields`)."""
    with st.sidebar:
        st.divider()
        st.subheader("Filters")
        if note:
            st.caption(note)
        mode = st.segmented_control(
            "Filter input", FILTER_MODES, default=FILTER_MODES[0], key="filter_mode",
            help="Dropdown: pick fields and values. filter.txt: upload a campaign's "
                 "filter.txt to see exactly which rows and recipients notifybot.py would select.",
        ) or FILTER_MODES[0]
        if mode == "filter.txt":
            return _filtertxt_panel(columns or fields)
        return ("dropdown", _dropdown_panel(fields)), []


def _filtertxt_panel(columns):
    """Upload a filter.txt, show its content and validate it (inside the sidebar).
    Read the way notifybot.py reads it: UTF-8, surrounding whitespace stripped."""
    up = st.file_uploader(
        "Upload filter.txt", type=["txt"], key="ftxt_upload",
        help="Rules as in notifybot.py: a comma inside a line = AND, each new line = OR "
             "(in multi mode each line is a separate email). Operators: = exact, != not equal, "
             "=~ regex (whole value, case-insensitive), !~ regex not. Wildcards after '=': "
             "* ? [abc] [!abc]. Lines starting with # are comments. A comma ALWAYS splits "
             "conditions, even inside quotes - use =~\"a|b\" for 'a or b'.",
    )
    st.caption(FTXT_HINT)
    if up is None:
        st.caption("No file uploaded yet: showing all rows.")
        return NO_FILTER, []

    try:
        text = up.getvalue().decode("utf-8").strip()
    except UnicodeDecodeError as e:
        msg = f"{up.name} is not valid UTF-8 ({e}). notifybot.py could not read it either."
        st.error(msg)
        return NO_FILTER, [msg]

    n = len(ftxt_active_lines(text))
    with st.expander(f"📄 {up.name} · {n} active line{'s' if n != 1 else ''}", expanded=True):
        st.code(text or "(empty file)", language=None, line_numbers=True)

    if n == 0:
        msg = f"{up.name} has no active conditions (only comments or blank lines): notifybot.py would send nothing."
        st.error(msg)
        return NO_FILTER, [msg]

    errors, hints = ftxt_validate(text, columns)
    for e in errors:
        st.error(e)
    for h in hints:
        st.info(h)
    if errors:
        return NO_FILTER, errors
    for w in ftxt_warnings(text):
        st.warning(w)
    st.caption("✅ Valid for notifybot.py")
    return ("filtertxt", text), []


def _dropdown_panel(fields):
    """Field pickers (the original sidebar filters); returns ((field, pattern), ...)."""
    chosen = st.multiselect(
        "Fields to filter on", fields,
        help="Pick one or more fields, then type the value for each. "
             "A row must match ALL of the field conditions (AND).",
    )
    out = []
    for f in chosen:
        pattern = st.text_input(
            f, value="*", key=f"val_{f}",
            help="* = all. Wildcards: prod*, *-177207, ?at. Several values: uat, prod*",
        )
        out.append((f, pattern))
    if len(chosen) > 1:
        st.caption("Field conditions are combined with **AND**.")
    return tuple(out)


def apply_filters(d, spec):
    return d[spec_mask(d, spec)] if spec_active(spec) else d


@st.cache_resource(max_entries=8, show_spinner="Comparing the two inventories…")
def compare(key_a, key_b, spec, _a, _b):
    """Diff of two loaded files (after the sidebar filters), cached per file pair + filter spec."""
    (a, ta, ea), (b, tb, eb) = _a, _b
    a, b = apply_filters(a, spec), apply_filters(b, spec)
    res = diff_inventories(a, b, ta, ea, tb, eb)
    res["kpis_a"], res["kpis_b"] = kpis(a), kpis(b)
    res["rows_a"], res["rows_b"] = len(a), len(b)
    return res


@st.cache_resource(max_entries=16, show_spinner="Preparing CSV…")
def to_csv_bytes(cache_key, _frame):
    return _frame.to_csv(index=False).encode("utf-8")


def download(label, frame, fname, key):
    """Download button; for big results the CSV is only built when asked for."""
    if len(frame) > 5000 and not st.checkbox(f"Prepare {label.lower()} ({len(frame):,} rows)", key=f"prep_{key}"):
        return
    st.download_button(f"⬇ {label}", to_csv_bytes(key, frame), fname, "text/csv", key=f"dl_{key}")


def compare_view(hist, snaps, snap_label):
    with st.sidebar:
        st.divider()
        st.subheader("Files to compare")
        ia = st.selectbox("Older inventory (A)", range(len(snaps)), index=1,
                          format_func=snap_label, key="cmp_a")
        ib = st.selectbox("Newer inventory (B)", range(len(snaps)), index=0,
                          format_func=snap_label, key="cmp_b")
    ra, rb = snaps.iloc[ia], snaps.iloc[ib]
    if ia == ib:
        st.info("Pick two different inventory files in the sidebar to compare.")
        st.stop()
    try:
        ka, kb = file_key(ra["path"]), file_key(rb["path"])
        A, B = load_file(*ka), load_file(*kb)
    except Exception as e:
        st.error(f"Could not load the files: {e}")
        st.stop()

    skip = lambda d: {d[1], d[2], "_ts", "_emails"}
    fields = [c for c in A[0].columns if c not in skip(A)]
    fields += [c for c in B[0].columns if c not in skip(B) and c not in fields]
    all_cols = [c for c in A[0].columns if c not in ("_ts", "_emails")]
    all_cols += [c for c in B[0].columns if c not in ("_ts", "_emails") and c not in all_cols]
    spec, problems = filter_sidebar(fields, "Optional: compare only matching rows, e.g. env = prod.",
                                    columns=all_cols)
    if problems:
        st.error("The uploaded filter.txt has problems (see the sidebar) - fix the file "
                 "and upload it again to compare.")
        st.stop()
    res = compare(ka, kb, spec, A, B)

    st.markdown(
        f'<div class="nb-banner nb-compare"><h1>🔍 Compare Inventory Snapshots</h1>'
        f'<p><b>A</b> {html.escape(ra["file"])} · {ra["when"]:%Y-%m-%d %H:%M} UTC  →  '
        f'<b>B</b> {html.escape(rb["file"])} · {rb["when"]:%Y-%m-%d %H:%M} UTC</p></div>',
        unsafe_allow_html=True,
    )
    if ra["when"] > rb["when"]:
        st.warning("A is newer than B, so “added” and “removed” are read backwards in time. "
                   "Swap the two files in the sidebar to see changes going forward.")

    key_txt = " + ".join(res["key"])
    filt_note = ""
    if spec_active(spec):
        filt_note = " · filtered by filter.txt" if spec[0] == "filtertxt" else " · filtered"
    section("What changed", f"rows matched on {key_txt}{filt_note}")
    kc = st.container(key="kpi_cmp")
    net = res["rows_b"] - res["rows_a"]
    cards = [
        ("Rows added", len(res["added"])), ("Rows removed", len(res["removed"])),
        ("Rows changed", len(res["changed"])), ("Emails added", len(res["emails_added"])),
        ("Emails removed", len(res["emails_removed"])),
    ]
    for col, (label, val) in zip(kc.columns(5), cards):
        col.metric(label, f"{val:,}")
    st.caption(
        f"{res['rows_a']:,} rows in A → {res['rows_b']:,} rows in B (net {net:+,})  ·  "
        f"{res['unchanged']:,} rows unchanged  ·  “Emails added/removed” = addresses that "
        "appear in one file and nowhere in the other"
    )
    if res["cols_added"] or res["cols_removed"]:
        st.info("Column changes: "
                + (f"added {', '.join(res['cols_added'])}. " if res["cols_added"] else "")
                + (f"removed {', '.join(res['cols_removed'])}." if res["cols_removed"] else ""))
    if res["dup_a"] or res["dup_b"]:
        st.warning(f"Duplicate {key_txt} keys found (A: {res['dup_a']:,}, B: {res['dup_b']:,}); "
                   "only the first row of each was compared.")

    section("KPI comparison", color="#7a5af8")
    kt = pd.DataFrame({
        "Metric": KPI_LABELS,
        f"A · {ra['when']:%Y-%m-%d}": [res["kpis_a"][k] for k in KPI_LABELS],
        f"B · {rb['when']:%Y-%m-%d}": [res["kpis_b"][k] for k in KPI_LABELS],
    })
    kt["Δ Change"] = [
        None if res["kpis_a"][k] is None or res["kpis_b"][k] is None
        else res["kpis_b"][k] - res["kpis_a"][k] for k in KPI_LABELS
    ]
    html_table(kt)

    section("Where the changes are", "rows added / removed / changed per value", color="#dc6803")
    bf = find_col(B[0], "env") or (fields[0] if fields else None)
    second = res["key"][0]
    sc, _ = st.columns([1, 2])
    by = sc.selectbox("Group by", fields, index=fields.index(bf) if bf in fields else 0, key="cmp_by")
    c1, c2 = st.columns(2)
    for colw, field in ((c1, by), (c2, second)):
        with colw:
            st.markdown(f"**By {html.escape(field)}**")
            t = diff_by(res, field, top=25)
            if len(t):
                html_table(t, max_height=420)
            else:
                st.caption("No differences.")

    tag = f"{os.path.basename(ra['file'])}_vs_{os.path.basename(rb['file'])}".replace(".csv", "")
    t_add, t_rem, t_chg, t_em = st.tabs([
        f"➕ Added rows ({len(res['added']):,})", f"➖ Removed rows ({len(res['removed']):,})",
        f"✏️ Changed rows ({len(res['changed']):,})",
        f"📧 Emails (+{len(res['emails_added']):,} / −{len(res['emails_removed']):,})",
    ])
    MAX = 2000

    def row_list(frame, what, k):
        if not len(frame):
            st.caption(f"No rows {what}.")
            return
        q = st.text_input("Search", placeholder="cluster, namespace, appid, email…", key=f"q_{k}")
        view = frame
        if q:
            cols = [c for c in frame.columns if len(frame) <= 20000 or c != "email"]
            hay = frame[cols[0]].astype(str).str.cat([frame[c].astype(str) for c in cols[1:]], sep=" ")
            view = frame[hay.str.contains(q, case=False, regex=False)]
        shown = view.drop(columns=[c for c in ("email",) if c in view.columns])
        if len(view) > MAX:
            st.caption(f"Showing the first {MAX:,} of {len(view):,} rows. Download for the full list.")
        st.dataframe(shown.head(MAX), width="stretch", hide_index=True, height=380)
        download(f"Download {what} rows CSV", view, f"{what}_rows_{tag}.csv", f"{k}_{len(view)}_{q}")

    with t_add:
        st.caption("Rows in B with no matching row in A (new cluster + namespace).")
        row_list(res["added"], "added", "add")
    with t_rem:
        st.caption("Rows in A with no matching row in B (cluster + namespace no longer present).")
        row_list(res["removed"], "removed", "rem")
    with t_chg:
        st.caption("Rows in both files where a field value or the email list changed.")
        ch = res["changed"]
        if len(ch):
            kinds = ch["change"].str.split("; ").explode().str.split(":").str[0]
            summary = kinds.value_counts().rename_axis("What changed").reset_index(name="Rows")
            html_table(summary.head(15))
            show_cols = [*res["key"]] + [c for c in ("env", "appid") if c in ch.columns and c not in res["key"]] + \
                ["change", "+ emails", "− emails", "emails added", "emails removed"]
            row_list(ch[show_cols], "changed", "chg")
            with st.expander("Email changes for one row"):
                kc0 = res["key"]
                labels = ch[kc0[0]].astype(str).str.cat([ch[c].astype(str) for c in kc0[1:]], sep=" / ")
                pick = st.selectbox("Row", labels.index, format_func=lambda i: labels[i], index=None,
                                    placeholder="Type to search…", key="chg_pick")
                if pick is not None:
                    r_ = ch.loc[pick]
                    st.write(f"**Change:** {r_['change']}")
                    e1, e2 = st.columns(2)
                    with e1:
                        st.write(f"**Added ({r_['+ emails']})**")
                        copy_button(r_["emails added"], "📋 Copy added")
                        st.text_area("added", r_["emails added"], height=100, label_visibility="collapsed",
                                     key=f"ea_{pick}")
                    with e2:
                        st.write(f"**Removed ({r_['− emails']})**")
                        copy_button(r_["emails removed"], "📋 Copy removed")
                        st.text_area("removed", r_["emails removed"], height=100, label_visibility="collapsed",
                                     key=f"er_{pick}")
        else:
            st.caption("No rows changed.")
    with t_em:
        st.caption("Addresses present in one file and nowhere in the other. "
                   "“rows” = how many rows the address appears in.")
        e1, e2 = st.columns(2)
        for colw, frame, what, k in ((e1, res["emails_added"], "Added", "eadd"),
                                     (e2, res["emails_removed"], "Removed", "erem")):
            with colw:
                st.markdown(f"**{what} addresses: {len(frame):,}**")
                if len(frame):
                    st.dataframe(frame, width="stretch", hide_index=True, height=320)
                    joined = ";".join(frame["email"])
                    copy_button(joined, f"📋 Copy {what.lower()}")
                    download(f"Download {what.lower()} emails CSV", frame,
                             f"emails_{what.lower()}_{tag}.csv", f"{k}_{len(frame)}")
    st.stop()


# ------------------------------------------------------------------ sidebar
def default_inventory_path():
    """Starting value of the 'Inventory file' box, first match wins:
      1. streamlit run inventory_portal_st.py -- --inventory /path/file.csv
      2. environment variable NOTIFYBOT_INVENTORY=/path/file.csv
      3. inventory.csv (in the folder the portal was started from)"""
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a in ("--inventory", "-i") and i + 1 < len(args):
            return args[i + 1]
        if a.startswith("--inventory="):
            return a.split("=", 1)[1]
    return os.environ.get("NOTIFYBOT_INVENTORY") or "inventory.csv"


with st.sidebar:
    st.title("📧 NotifyBot Inventory")
    path = st.text_input(
        "Inventory file", default_inventory_path(),
        help="Path of the current inventory file (any name, any folder). Archived snapshots "
             "named <this name>-<epoch> in the same folder are listed below.",
    ).strip()

if path and os.path.isfile(path) and not valid_meta(path):
    # new current file: parse it once, for display and for its metadata sidecar
    try:
        build_meta(path, load_file(*file_key(path))[0])
    except Exception:
        pass  # reported below when the file is loaded
hist = history(path) if path else pd.DataFrame()

snaps = hist.iloc[::-1].reset_index(drop=True) if len(hist) else hist  # newest first


def snap_label(i):
    r_ = snaps.iloc[i]
    tag = "Latest" if r_["latest"] else "Archived"
    return f"{tag} · {r_['when']:%Y-%m-%d %H:%M} UTC · {int(r_['rows']):,} rows"


with st.sidebar:
    mode = st.segmented_control(
        "View", ["📊 Dashboard", "🔍 Compare"], default="📊 Dashboard", key="mode",
        help="Compare: pick two inventory files and see the rows and emails added, removed or changed.",
    ) or "📊 Dashboard"

if mode == "🔍 Compare":
    if len(snaps) < 2:
        st.info("Comparing needs at least two inventory files: the current one and an archived "
                f"`{os.path.basename(path)}-<epoch>` snapshot.")
        st.stop()
    compare_view(hist, snaps, snap_label)

with st.sidebar:
    up = None
    if len(hist):
        sel = st.selectbox(
            "Inventory snapshot", range(len(snaps)), format_func=snap_label, key="snapshot",
            help="Pick an archived inventory file to review it with the same KPIs, filters and email lists.",
        )
        chosen_snap = snaps.iloc[sel]
        st.caption(f"File: `{chosen_snap['file']}`")
    with st.expander("Upload a file instead"):
        up = st.file_uploader(
            "Upload inventory CSV", type="csv", label_visibility="collapsed",
            help="For files that are not on the server. Large files load much faster from a path.",
        )

if up is not None:
    try:
        df, time_col, email_col = load_upload(up.file_id, up)
    except Exception as e:
        st.error(str(e))
        st.stop()
    src, key, snap_row = up.name, ("upload", up.file_id), None
elif len(hist):
    snap_row = chosen_snap
    try:
        key = file_key(snap_row["path"])
        df, time_col, email_col = load_file(*key)
    except Exception as e:
        st.error(f"Could not load {snap_row['file']}: {e}")
        st.stop()
    src = snap_row["file"]
else:
    st.info("Enter the path of the inventory file in the sidebar, or upload one, to begin.")
    st.stop()

fields = [c for c in df.columns if c not in (time_col, email_col, "_ts", "_emails")]

spec, problems = filter_sidebar(fields, columns=[c for c in df.columns if c not in ("_ts", "_emails")])
if problems:
    st.error(f"The uploaded filter.txt has {len(problems)} problem(s), listed in the sidebar. "
             "notifybot.py would refuse it too - fix the file and upload it again.")
    st.stop()

m, cnt, k_sel, envdf = selection(key, spec, df)
emails = sorted(cnt)

# ------------------------------------------------------------------ main
archived = snap_row is not None and not snap_row["latest"]
badge = '<span class="nb-badge">ARCHIVED SNAPSHOT</span>' if archived else ""
when_txt = f"  ·  snapshot {snap_row['when']:%Y-%m-%d %H:%M} UTC" if snap_row is not None else ""
st.markdown(
    f'<div class="nb-banner{" nb-archived" if archived else ""}"><h1>📧 NotifyBot Inventory Summary</h1>'
    f'<p>{badge}Source: {html.escape(str(src))}{when_txt}  ·  {len(df):,} rows loaded</p></div>',
    unsafe_allow_html=True,
)

fmt = lambda v: "n/a" if v is None or pd.isna(v) else f"{int(v):,}"

# ---- full inventory: values of the file being viewed, change vs the snapshot before it
if snap_row is not None:
    pos = hist.index[hist["path"] == snap_row["path"]][0]
    k_full = {c: snap_row[c] for c in KPI_LABELS}
    prev = hist.iloc[pos - 1] if pos > 0 else None
else:  # uploaded file: not part of the history
    k_full, prev = kpis(df), None

section("Full inventory", "archived inventory file" if archived else "complete inventory file")
kpi_full = st.container(key="kpi_full")
for col, (label, val) in zip(kpi_full.columns(len(k_full)), k_full.items()):
    delta = None
    if prev is not None and pd.notna(val) and pd.notna(prev[label]):
        delta = int(val - prev[label])
    spark = hist[label].dropna().astype(int).tolist() if len(hist) else []
    col.metric(
        label, fmt(val), delta=delta,
        chart_data=spark if len(spark) > 1 else None, chart_type="line",
    )
if prev is not None:
    st.caption(
        f"Change shown vs previous snapshot {prev['when']:%Y-%m-%d %H:%M} UTC  ·  "
        f"{len(hist)} snapshots in history"
    )

if len(hist) > 1:
    with st.expander("📈 Trend over time", expanded=True):
        pick = st.segmented_control(
            "Metrics", KPI_LABELS, selection_mode="multi",
            default=["Clusters", "Namespaces", "App IDs"], key="trend_metrics",
        )
        shown = [c for c in KPI_LABELS if c in (pick or KPI_LABELS)]
        chart = hist.set_index("when")[shown]
        chart.index.name = "Snapshot (UTC)"
        st.line_chart(chart, height=280, color=[KPI_COLORS[c] for c in shown])
        tbl = hist[["when", *KPI_LABELS]].copy()
        tbl.insert(0, "Snapshot (UTC)", tbl.pop("when").dt.strftime("%Y-%m-%d %H:%M"))
        for c in KPI_LABELS:
            tbl[f"Δ {c}"] = tbl[c].diff()
        html_table(tbl.iloc[::-1], max_height=360)
elif snap_row is not None:
    st.caption(
        f"No trend yet: archived snapshots named `{os.path.basename(path)}-<epoch>` "
        "will appear here once they exist next to the current file."
    )

txt_mode = spec[0] == "filtertxt"
section("Based on selection",
        "rows matching filter.txt" if txt_mode and spec_active(spec) else "rows matching the sidebar filters",
        color="#0e9384")
kpi_sel = st.container(key="kpi_sel")
for col, (label, val) in zip(kpi_sel.columns(5), k_sel.items()):
    col.metric(label, fmt(val))

# ---- filter.txt: what notifybot.py would do with this filter on this file
if txt_mode and spec_active(spec):
    section("filter.txt preview", "what notifybot.py would select from this inventory file",
            color="#dd2590")
    masks = txt_lines(key, spec[1], df)
    st.markdown("**Per line** (each line is an OR branch; in multi mode each line is a separate email)")
    html_table(ftxt_line_breakdown(df, masks), max_height=320)

    res_ = ftxt_recipients(m)
    if res_ is None:
        st.warning("This file has no column named exactly `email`, which notifybot.py "
                   "requires - it would find no recipients.")
    else:
        to_list, invalid = res_
        p1, p2, p3 = st.columns(3)
        p1.metric("Single mode: TO recipients", f"{len(to_list):,}")
        p2.metric("Multi mode: emails", f"{len(masks):,}")
        p3.metric("Invalid addresses skipped", f"{len(invalid):,}")
        st.caption("Before exclude.txt, additional_to.txt, cc.txt and bcc.txt, which "
                   "notifybot.py applies in the campaign folder.")
        if to_list:
            joined = ";".join(to_list)
            b1, b2 = st.columns([1, 3])
            b1.download_button("⬇ Download as to.txt", "\n".join(to_list) + "\n", "to.txt",
                               "text/plain", key="dl_to_txt")
            with b2:
                copy_button(joined, "📋 Copy recipients")
        if invalid:
            with st.expander(f"Invalid addresses ({len(invalid):,})"):
                st.text_area("invalid", "\n".join(invalid), height=120,
                             label_visibility="collapsed", key="invalid_list")

section("By environment", color="#7a5af8")
if envdf is not None:
    html_table(envdf)
else:
    st.caption("No 'env' column in this file, or no rows match the filters.")

tab1, tab2, tab3, tab4 = st.tabs(["Unique emails", "Breakdown", "Matching rows", "Field overview"])

with tab1:
    st.caption(f"{sum(cnt.values()):,} email entries before de-dup  →  {len(emails):,} unique")
    q = st.text_input("Search emails", placeholder="e.g. smith or @citi.com")
    edf = pd.DataFrame({"email": emails, "appears_in_rows": [cnt[e] for e in emails]})
    if q:
        edf = edf[edf["email"].str.contains(q, case=False, regex=False)]
    st.dataframe(edf, width="stretch", hide_index=True, height=380)
    d1, d2 = st.columns([1, 3])
    d1.download_button("⬇ Download CSV", edf.to_csv(index=False), "unique_emails.csv", "text/csv")
    with st.expander("Copy as ';' separated list"):
        joined = ";".join(edf["email"])
        copy_button(joined, "📋 Copy emails")
        st.text_area("Emails", joined, height=120, key="copy_all", label_visibility="collapsed")

TOP = 300
with tab2:
    by = st.selectbox("Break down by", fields)
    if len(m):
        g = breakdown(key, spec, by, m)
        note = f" (top {TOP:,} of {len(g):,} values)" if len(g) > TOP else ""
        st.caption(f"Values of **{by}** by number of unique emails{note}")
        html_table(g.head(TOP).reset_index().rename(columns={"unique_emails": "Unique emails"}), max_height=420)
        pick = st.selectbox(
            "Show emails for value", g.index.tolist(), index=None,
            placeholder="Type to search a value…",
        )
        if pick is not None:
            sub = sorted(frozenset().union(*m.loc[m[by] == pick, "_emails"]))
            st.write(f"**{len(sub)}** unique emails for `{pick or '(blank)'}`")
            joined = ";".join(sub)
            copy_button(joined, "📋 Copy emails")
            st.text_area("Emails", joined, height=120, key=f"copy_{by}_{pick}", label_visibility="collapsed")
    else:
        st.warning("No rows match the current filters.")

MAX_ROWS = 2000
with tab3:
    show = [c for c in df.columns if c not in ("_ts", "_emails")]
    if len(m) > MAX_ROWS:
        st.caption(f"Showing the first {MAX_ROWS:,} of {len(m):,} matching rows. Use the filters to narrow down.")
    st.dataframe(m[show].head(MAX_ROWS), width="stretch", hide_index=True, height=420)

with tab4:
    ov = pd.DataFrame({
        "field": fields,
        "distinct_values": [m[f].nunique() for f in fields],
        "top_value": [(m[f].mode().iat[0] if len(m) else "") for f in fields],
    })
    html_table(ov.rename(columns={
        "field": "Field", "distinct_values": "Distinct values", "top_value": "Top value",
    }), max_height=520)
