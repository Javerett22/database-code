import re
import shutil
import sqlite3

import pandas as pd

PLACEHOLDERS = {"", "need context", "chk seq", "none"}


# ---------- text cleaning ----------

def normalize(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def clean(s):
    s = str(s).replace("\ufffd", "").replace("ï¿½", "").replace("\xa0", " ")
    return s.strip()


def is_placeholder(value):
    return pd.isna(value) or normalize(clean(value)) in PLACEHOLDERS


# ---------- CSV -> alias map ----------

def get_synonyms(row):
    cells = [clean(v) for v in row.iloc[6:14] if pd.notna(v)]
    return [c for c in cells if c]


def add_row_to_map(alias_map, row):
    canonical = row.iloc[5]
    if is_placeholder(canonical):
        return
    canonical = clean(canonical)
    for alias in [canonical] + get_synonyms(row):
        alias_map.setdefault(normalize(alias), set()).add(canonical)


def csv_to_alias_map(csv_file):
    df = pd.read_csv(csv_file, encoding="cp1252")
    alias_map = {}
    for _, row in df.iterrows():
        add_row_to_map(alias_map, row)
    return alias_map


# ---------- matching ----------

def compile_alias(alias):
    # not surrounded by letters/digits, so "a1" doesn't hit "a12"
    return re.compile(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])")


def build_matcher(alias_map):
    longest_first = sorted(alias_map, key=len, reverse=True)
    return [(alias, compile_alias(alias)) for alias in longest_first]


def unwrap(canon):
    """One canonical -> the string. Several -> keep the set (ambiguous)."""
    return next(iter(canon)) if len(canon) == 1 else canon


def find_potential_matches(name, alias_map, patterns):
    n = normalize(name)
    return [(alias, alias_map[alias]) for alias, pat in patterns if pat.search(n)]


def find_best_match(name, alias_map, patterns):
    """Longest matching alias wins. Returns (canonical, alias) or (None, None)."""
    n = normalize(name)
    if n in alias_map:
        return unwrap(alias_map[n]), n
    for alias, pat in patterns:  # already longest-first
        if pat.search(n):
            return unwrap(alias_map[alias]), alias
    return None, None


# ---------- database ----------

def fetch_distinct_names(cur, table, column):
    sql = f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
    return [r[0] for r in cur.execute(sql)]


def classify_names(names, alias_map, patterns, overwrite):
    updates, ambiguous, unmatched = {}, {}, []
    for name in names:
        canon, _ = find_best_match(name, alias_map, patterns)
        if canon is None:
            unmatched.append(name)
        elif isinstance(canon, set):
            ambiguous[name] = canon
        elif canon != name or not overwrite:
            updates[name] = canon
    return updates, ambiguous, unmatched


def report(names, updates, ambiguous, unmatched):
    print(f"{len(names)} distinct names: {len(updates)} to update, "
          f"{len(ambiguous)} ambiguous, {len(unmatched)} unmatched")
    for old, new in list(updates.items())[:20]:
        print(f"  {old!r} -> {new!r}")
    if ambiguous:
        print("AMBIGUOUS (skipped):", ambiguous)
    if unmatched:
        print("UNMATCHED (left as is):", unmatched)


def ensure_column(cur, table, column):
    cols = [r[1] for r in cur.execute(f'PRAGMA table_info("{table}")')]
    if column not in cols:
        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" TEXT')


def apply_updates(con, table, column, target, updates):
    sql = f'UPDATE "{table}" SET "{target}" = ? WHERE "{column}" = ?'
    rows = [(canon, name) for name, canon in updates.items()]
    with con:  # one transaction, rolls back on error
        con.executemany(sql, rows)

def write_changes(con, db_path, table, column, target, updates):
    if target == column:
        shutil.copy2(db_path, db_path + ".bak")
    else:
        ensure_column(con.cursor(), table, target)
    apply_updates(con, table, column, target, updates)


def update_database(db_path, table, column, alias_map, patterns,
                    target_column=None, dry_run=True):
    overwrite = target_column is None
    target = column if overwrite else target_column
    con = sqlite3.connect(db_path)
    names = fetch_distinct_names(con.cursor(), table, column)
    result = classify_names(names, alias_map, patterns, overwrite)
    report(names, *result)
    if dry_run:
        print("Dry run, nothing written.")
    else:
        write_changes(con, db_path, table, column, target, result[0])
    con.close()
    return result


# ---------- entry point ----------

def main():
    alias_map = csv_to_alias_map("/home/benne77/Team_Miles_Schedule(Sequences).csv")
    patterns = build_matcher(alias_map)
    update_database(
        db_path="/home/benne77/data.db",
        table="data_table",
        column="protein",
        alias_map=alias_map,
        patterns=patterns,
        target_column="protein_canonical",  # or None to overwrite in place
        dry_run=False,
    )


if __name__ == "__main__":
    main()