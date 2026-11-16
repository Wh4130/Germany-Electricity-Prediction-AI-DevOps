"""
Appendix table of the candidate features: name, description and data source (with link).

Reads the feature table of docs/FEATURES.md and keeps the columns that are model inputs or possible inputs
(`Model = x`) and do not leak the target (no `leakage` in the notes). Writes only the ROWS of the table, the
longtable header and the caption are in the LaTeX source (report/main.tex), so that they can be edited there:

    \\begin{longtable}{...}  header  \\endhead  \\input{tables/feature_sources.tex}  \\end{longtable}

Output: results/eda/tables/feature_sources.tex (rows) and feature_sources.csv

    uv run python src/analysis/eda/make_feature_sources_table.py
"""

from __future__ import annotations

import re

import pandas as pd

from eda_common import SRC_DIR, TABLES_DIR

FEATURES_MD = SRC_DIR.parent / "docs" / "FEATURES.md"

# The groups of the report (Table "Candidate features"), in this order. Other names of FEATURES.md are renamed.
GROUP_ORDER = ["Calendar", "Fourier terms", "Weather", "Sun position", "Day-ahead price", "Solar capacity",
               "Economic", "Policy"]
GROUP_RENAME = {"Fourier": "Fourier terms", "Electricity price": "Day-ahead price"}
GROUP_OVERRIDE = {"daylight_duration": "Sun position", "ipi_ei_level": "Economic"}  # by the first name of the row

# A short name for the rows that list many columns.
NAME_OVERRIDE = {
    "sin_y1": r"\texttt{sin\_y}$k$, \texttt{cos\_y}$k$ ($k=1,\dots,10$)",
    "sin_d1": r"\texttt{sin\_d}$k$, \texttt{cos\_d}$k$ ($k=1,\dots,6$)",
}

TEXT_REPLACE = [(" - ", "--"), ("°C", r"\textdegree{}C"), ("m²", "m$^2$")]


def parse_rows() -> list[dict]:
    """The rows of the feature table of FEATURES.md as dictionaries."""
    lines = FEATURES_MD.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "## Feature table")
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| Category"):
            continue
        cells = [c.strip() for c in line.strip()[1:-1].split("|")]  # keeps empty cells at the end
        if len(cells) != 9:
            raise ValueError(f"unexpected row with {len(cells)} cells: {line[:80]}")
        keys = ["category", "name", "description", "datatype", "model", "ablation", "source", "produced_by", "notes"]
        rows.append(dict(zip(keys, cells)))
    return rows


def escape(text: str, code: bool = False) -> str:
    """Escape LaTeX special characters; in code names a line break is allowed after an underscore."""
    for char in "&%#$":
        text = text.replace(char, "\\" + char)
    text = text.replace("_", "\\_\\allowbreak{}" if code else "\\_")
    return text


def format_text(text: str) -> str:
    """Plain text with `code` segments in typewriter and the replacements of TEXT_REPLACE outside of code."""
    out = []
    for i, part in enumerate(text.split("`")):
        if i % 2:
            out.append(r"\texttt{" + escape(part, code=True) + "}")
        else:
            part = escape(part)
            for old, new in TEXT_REPLACE:  # after the escaping, the replacements are LaTeX
                part = part.replace(old, new)
            out.append(part)
    return "".join(out)


def link_map(rows: list[dict]) -> dict[str, str]:
    """Text of every link of the source column -> URL, so that a later mention without a link gets it too."""
    links = {}
    for row in rows:
        for text, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", row["source"]):
            bare = text.replace("`", "")
            links.setdefault(bare, url)
            if " via " in bare:  # "Destatis 12411LJ003 via DBnomics" is also mentioned as "Destatis 12411LJ003"
                links.setdefault(bare.split(" via ")[0], url)
    return links


def format_source(source: str, links: dict[str, str]) -> str:
    """Markdown links to \\href. A name that is linked elsewhere in the table is linked here as well."""
    pieces = re.split(r"(\[[^\]]+\]\(https?://[^)]+\))", source)
    out = []
    for piece in pieces:
        match = re.fullmatch(r"\[([^\]]+)\]\((https?://[^)]+)\)", piece)
        if match:
            out.append(r"\href{" + match.group(2).replace("%", r"\%").replace("#", r"\#") + "}{"
                       + format_text(match.group(1)) + "}")
            continue
        # plain text: link the names that are known from another row (the longest name first)
        placeholders = {}
        for k, (text, url) in enumerate(sorted(links.items(), key=lambda kv: -len(kv[0]))):
            bare = text.replace("`", "")
            if bare in piece.replace("`", ""):
                token = f"\x00{k}\x00"
                piece = piece.replace("`" + bare + "`", token).replace(bare, token)
                placeholders[token] = r"\href{" + url + "}{" + format_text(text) + "}"
        formatted = format_text(piece)
        for token, latex in placeholders.items():
            formatted = formatted.replace(token, latex)
        out.append(formatted)
    return "".join(out)


def main() -> None:
    rows = parse_rows()
    links = link_map(rows)
    keep = [r for r in rows if r["model"] == "x" and "leakage" not in r["notes"]]

    records = []
    for r in keep:
        names = re.findall(r"`([^`]+)`", r["name"])
        first = names[0]
        group = GROUP_OVERRIDE.get(first, GROUP_RENAME.get(r["category"], r["category"]))
        resolution = "D" if "**D**" in r["notes"] else "H" if "**H**" in r["notes"] else ""
        name_tex = NAME_OVERRIDE.get(first) or ", ".join(r"\texttt{" + escape(n, code=True) + "}" for n in names)
        if resolution:
            name_tex += f" ({resolution})"
        records.append(dict(group=group, feature=", ".join(names), resolution=resolution,
                            description=r["description"].replace("`", ""), source=re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", r["source"]),
                            name_tex=name_tex, description_tex=format_text(r["description"]),
                            source_tex=format_source(r["source"], links)))

    df = pd.DataFrame(records)
    df["order"] = df["group"].map(GROUP_ORDER.index)
    df = df.sort_values("order", kind="stable").drop(columns="order").reset_index(drop=True)

    lines, previous = [], None
    for r in df.itertuples():
        if previous is not None and r.group != previous:
            lines.append(r"\addlinespace[3pt]")
        shown = r.group if r.group != previous else ""
        lines.append(" & ".join([shown, r.name_tex, r.description_tex, r.source_tex]) + r" \\")
        previous = r.group

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    (TABLES_DIR / "feature_sources.tex").write_text("\n".join(lines) + "\n")
    df[["group", "feature", "resolution", "description", "source"]].to_csv(TABLES_DIR / "feature_sources.csv", index=False)
    print(f"saved {len(df)} rows to {TABLES_DIR / 'feature_sources.tex'}")
    print(df.groupby("group", sort=False).size().to_string())


if __name__ == "__main__":
    main()
