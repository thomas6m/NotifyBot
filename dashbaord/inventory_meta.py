"""
Inventory parsing, KPIs and per-snapshot metadata for the NotifyBot Inventory Summary.

Each archived snapshot  inventory.csv-<epoch>  gets a small sidecar file
inventory.csv-<epoch>.meta.json  holding its KPIs. The dashboard reads these
instead of re-parsing every old CSV. A sidecar is rebuilt automatically when it is
missing or when its CSV's size / modified time no longer match.

The current file gets one too (inventory.csv.meta.json). Archiving keeps the file's
size and modified time, so moving the sidecar along with the CSV keeps it valid:

  mv inventory.csv           inventory.csv-<epoch>
  mv inventory.csv.meta.json inventory.csv-<epoch>.meta.json
  cp new.csv inventory.csv
  python inventory_meta.py inventory.csv      # builds sidecars that are missing / stale
"""
import glob
import io
import json
import os
import re
import sys
from collections import Counter
from itertools import chain

import pandas as pd

META_VERSION = 2
META_SUFFIX = ".meta.json"
KPI_LABELS = ["Clusters", "Cluster + namespace", "Namespaces", "App IDs", "Unique emails"]
SNAP_RX = re.compile(r"-(\d{9,13})$")


# ------------------------------------------------------------------ parsing
def parse_email_column(col):
    """';'/','-separated addresses per row -> frozenset per row.
    Identical addresses share one string object, which roughly halves memory on big files."""
    pool = {}
    out = []
    for raw in col.str.lower().str.replace(",", ";", regex=False):
        out.append(frozenset(
            pool.setdefault(e, e) for e in (x.strip() for x in raw.split(";")) if "@" in e
        ))
    return pd.Series(out, index=col.index)


def to_ts(v):
    """Epoch seconds or milliseconds -> UTC timestamps."""
    t = pd.to_numeric(v, errors="coerce")
    t = t.where(t < 1e11, t / 1000)  # milliseconds -> seconds
    return pd.to_datetime(t, unit="s", utc=True)


def find_col(df, name):
    """Case-insensitive column lookup; None if the file doesn't have it."""
    return next((c for c in df.columns if c.strip().lower() == name), None)


def parse_csv(data: bytes):
    df = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    time_col = df.columns[0]
    email_col = find_col(df, "email")
    if email_col is None:
        raise ValueError("No 'email' column found in the CSV")
    df["_ts"] = to_ts(df[time_col])
    df["_emails"] = parse_email_column(df[email_col].astype(str))
    return df, time_col, email_col


# ------------------------------------------------------------------ KPIs
def union_count(series):
    return len(frozenset().union(*series)) if len(series) else 0


def nuniq(s):
    s = s.astype(str).str.strip()
    return s[s != ""].nunique()


def kpis(d):
    cc, nc, ac = (find_col(d, n) for n in ("cluster", "namespace", "appid"))
    return {
        "Clusters": nuniq(d[cc]) if cc else None,
        "Cluster + namespace": len(d[[cc, nc]].drop_duplicates()) if cc and nc else None,
        "Namespaces": nuniq(d[nc]) if nc else None,
        "App IDs": nuniq(d[ac]) if ac else None,
        "Unique emails": union_count(d["_emails"]),
    }


def snapshot_time(d):
    """When this file was taken: its latest time value."""
    ts = d["_ts"].dropna()
    return ts.max() if len(ts) else None


# ------------------------------------------------------------------ metadata sidecars
def _stamp(path):
    st = os.stat(path)
    return st.st_size, st.st_mtime_ns


def build_meta(path, d=None):
    """Write <path>.meta.json (best effort) and return the metadata.
    Pass the already-parsed DataFrame as `d` to avoid reading the file again."""
    size, mtime = _stamp(path)
    if d is None:
        with open(path, "rb") as fh:
            d, _, _ = parse_csv(fh.read())
    ts = d["_ts"].dropna()
    meta = {
        "version": META_VERSION,
        "source": os.path.basename(path),
        "size": size,
        "mtime_ns": mtime,
        "rows": len(d),
        "when": ts.max().timestamp() if len(ts) else None,
        "when_min": ts.min().timestamp() if len(ts) else None,
        "kpis": kpis(d),
    }
    tmp = path + META_SUFFIX + ".tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(meta, fh, indent=2)
        os.replace(tmp, path + META_SUFFIX)  # atomic: readers never see half a file
    except OSError:
        pass  # read-only folder: still return the KPIs, just don't cache them
    return meta


def valid_meta(path):
    try:
        with open(path + META_SUFFIX) as fh:
            meta = json.load(fh)
        if meta.get("version") == META_VERSION and (meta.get("size"), meta.get("mtime_ns")) == _stamp(path):
            return meta
    except (OSError, ValueError):
        pass
    return None


def read_meta(path, d=None):
    """Metadata for one CSV: from its sidecar if still valid, otherwise rebuilt
    (from `d` when the caller already has the file parsed)."""
    return valid_meta(path) or build_meta(path, d)


def snapshot_files(base):
    """Archived snapshots <base>-<epoch> (sidecars and other files excluded)."""
    out = []
    for f in glob.glob(glob.escape(base) + "-*"):
        mo = SNAP_RX.search(f)
        if mo and os.path.isfile(f):
            out.append((f, mo.group(1)))
    return out


def _ts(sec):
    return None if sec is None else pd.Timestamp(sec, unit="s", tz="UTC")


def history(base):
    """Full-inventory KPIs for the current file and every <base>-<epoch> archive, oldest first.
    Built only from sidecars, so it never needs the big CSVs in memory once they exist."""
    pts = []
    cur = None
    if os.path.isfile(base):
        try:
            meta = read_meta(base)
            cur = {"when": _ts(meta["when"]), "file": os.path.basename(base),
                   "path": os.path.abspath(base), "rows": meta["rows"], "latest": True,
                   "_min": _ts(meta.get("when_min")), **meta["kpis"]}
        except Exception:
            cur = None
    for f, epoch in snapshot_files(base):
        try:
            meta = read_meta(f)
        except Exception:
            continue  # skip unreadable / malformed archives
        # the epoch in the file name is the snapshot time; content is the fallback
        when = to_ts(pd.Series([epoch])).iat[0]
        if pd.isna(when):
            when = _ts(meta.get("when"))
        if cur is not None and cur["_min"] is not None and cur["_min"] <= when <= cur["when"]:
            continue  # same data as the current file
        pts.append({"when": when, "file": os.path.basename(f), "path": os.path.abspath(f),
                    "rows": meta["rows"], "latest": False, **meta["kpis"]})
    if cur is not None:
        cur.pop("_min")
        pts.append(cur)
    cols = ["when", "file", "path", "rows", "latest", *KPI_LABELS]
    h = pd.DataFrame(pts, columns=cols).dropna(subset=["when"])
    h["latest"] = h["latest"].astype(bool)
    return h.sort_values(["when", "latest"]).reset_index(drop=True)


# ------------------------------------------------------------------ comparing two inventories
INTERNAL = ("_ts", "_emails")


def _fmt_set(s, limit=None):
    items = sorted(s)
    if limit and len(items) > limit:
        return ";".join(items[:limit]) + f";… (+{len(items) - limit} more)"
    return ";".join(items)


def diff_inventories(a, b, time_a, email_a, time_b, email_b):
    """Differences going from inventory `a` (older) to `b` (newer).

    Rows are matched on cluster + namespace (one row each); if a file lacks those
    columns, on all its other fields. Time columns are ignored (they change every run).

    Returns a dict with:
      key           list of key column names
      added         rows only in b
      removed       rows only in a
      changed       rows in both whose fields or email list differ, with a description
      emails_added  DataFrame(email, rows) - addresses in b but nowhere in a
      emails_removed                       - addresses in a but nowhere in b
      cols_added / cols_removed            - columns that appeared / disappeared
      dup_a / dup_b number of duplicate keys (only the first row of each is compared)
      unchanged     number of matched rows with no difference
    """
    skip_a = {time_a, email_a, *INTERNAL}
    skip_b = {time_b, email_b, *INTERNAL}
    fa = [c for c in a.columns if c not in skip_a]
    fb = [c for c in b.columns if c not in skip_b]

    cc_a, nc_a = find_col(a, "cluster"), find_col(a, "namespace")
    cc_b, nc_b = find_col(b, "cluster"), find_col(b, "namespace")
    if cc_a and nc_a and cc_b and nc_b:
        key_a, key_b = [cc_a, nc_a], [cc_b, nc_b]
    else:
        common = [c for c in fa if c in fb]
        if not common:
            raise ValueError("The two files have no columns in common to match rows on.")
        key_a = key_b = common
    key = list(key_a)

    def keyed(d, kcols, fields, email_col):
        k = d[kcols].astype(str).apply(lambda s: s.str.strip())
        k.columns = key
        out = k.copy()
        for c in fields:
            if c not in kcols:
                out[c] = d[c].astype(str).str.strip()
        out["_emails"] = d["_emails"].values
        out["_email_raw"] = d[email_col].values
        out["_k"] = k[key[0]].str.cat([k[c] for c in key[1:]], sep="\x1f") if len(key) > 1 else k[key[0]]
        dups = int(out["_k"].duplicated().sum())
        return out.drop_duplicates("_k").set_index("_k"), dups

    A, dup_a = keyed(a, key_a, fa, email_a)
    B, dup_b = keyed(b, key_b, fb, email_b)

    only_a = A.index.difference(B.index)
    only_b = B.index.difference(A.index)
    both = A.index.intersection(B.index)

    def present(d, idx, email_label="email"):
        cols = [c for c in d.columns if c not in ("_emails", "_email_raw")]
        out = d.loc[idx, cols].copy()
        out["emails"] = d.loc[idx, "_emails"].map(len).values
        out[email_label] = d.loc[idx, "_email_raw"].values
        return out.reset_index(drop=True)

    added = present(B, only_b)
    removed = present(A, only_a)

    # matched rows: compare every field both files have, and the email sets
    cmp_fields = [c for c in A.columns if c in B.columns and c not in key and not c.startswith("_")]
    Ab, Bb = A.loc[both], B.loc[both]
    diff_mask = pd.Series(False, index=both)
    field_diffs = {}
    for c in cmp_fields:
        neq = Ab[c].values != Bb[c].values
        if neq.any():
            field_diffs[c] = neq
            diff_mask |= neq
    e_a, e_b = Ab["_emails"].values, Bb["_emails"].values
    email_neq = pd.Series([x != y for x, y in zip(e_a, e_b)], index=both)
    diff_mask |= email_neq.values

    rows = []
    av = {c: Ab[c].to_numpy() for c in field_diffs}
    bv = {c: Bb[c].to_numpy() for c in set(key) | set(cmp_fields)}
    for i in diff_mask.to_numpy().nonzero()[0]:
        parts = [f"{c}: {av[c][i] or '(blank)'} → {bv[c][i] or '(blank)'}"
                 for c, neq in field_diffs.items() if neq[i]]
        plus, minus = e_b[i] - e_a[i], e_a[i] - e_b[i]
        rec = {c: bv[c][i] for c in key}
        rec.update({c: bv[c][i] for c in cmp_fields})  # current values, for context
        rec.update({
            "change": "; ".join(parts) if parts else "email list only",
            "+ emails": len(plus), "− emails": len(minus),
            "emails added": _fmt_set(plus), "emails removed": _fmt_set(minus),
        })
        rows.append(rec)
    changed = pd.DataFrame(rows, columns=[*key, *cmp_fields, "change", "+ emails", "− emails",
                                          "emails added", "emails removed"])

    ca = Counter(chain.from_iterable(A["_emails"]))
    cb = Counter(chain.from_iterable(B["_emails"]))
    ea = sorted(set(cb) - set(ca))
    er = sorted(set(ca) - set(cb))
    emails_added = pd.DataFrame({"email": ea, "rows": [cb[e] for e in ea]})
    emails_removed = pd.DataFrame({"email": er, "rows": [ca[e] for e in er]})

    return {
        "key": key, "added": added, "removed": removed, "changed": changed,
        "emails_added": emails_added, "emails_removed": emails_removed,
        "cols_added": [c for c in fb if c not in fa], "cols_removed": [c for c in fa if c not in fb],
        "dup_a": dup_a, "dup_b": dup_b, "unchanged": int(len(both) - diff_mask.sum()),
    }


def diff_by(d, col, top=None):
    """Added / removed / changed row counts per value of `col` (e.g. env, cluster)."""
    parts = []
    for name, frame in (("Added", d["added"]), ("Removed", d["removed"]), ("Changed", d["changed"])):
        if col in frame.columns and len(frame):
            parts.append(frame[col].replace("", "(blank)").value_counts().rename(name))
    if not parts:
        return pd.DataFrame()
    t = pd.concat(parts, axis=1).fillna(0).astype(int)
    for c in ("Added", "Removed", "Changed"):
        if c not in t.columns:
            t[c] = 0
    t["Δ Net rows"] = t["Added"] - t["Removed"]
    t = t[["Added", "Removed", "Changed", "Δ Net rows"]]
    t = t.assign(_s=t["Added"] + t["Removed"] + t["Changed"]).sort_values("_s", ascending=False).drop(columns="_s")
    t.index.name = col
    return (t.head(top) if top else t).reset_index()


# ------------------------------------------------------------------ CLI
def main(argv):
    base = argv[1] if len(argv) > 1 else "inventory.csv"
    files = sorted(f for f, _ in snapshot_files(base))
    if os.path.isfile(base):
        files.append(base)
    if not files:
        print(f"Neither {base} nor any {base}-<epoch> snapshot found.")
    for f in files:
        try:
            meta = read_meta(f)
            print(f"ok    {f}{META_SUFFIX}  rows={meta['rows']}  " +
                  "  ".join(f"{k}={v}" for k, v in meta["kpis"].items()))
        except Exception as e:
            print(f"skip  {f}: {e}")


if __name__ == "__main__":
    main(sys.argv)
