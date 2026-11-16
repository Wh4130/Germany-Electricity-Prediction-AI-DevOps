"""
Writing report tables: one CSV per table (raw numbers) plus one Markdown file
that collects them, formatted, in ``src/results/final_report/tables``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.common.paths import TABLES_DIR

MWH_DECIMALS = 0
PCT_DECIMALS = 1


def _number_format(name: str) -> str:
    """Format spec of a numeric column, from its name (first matching rule wins)."""
    if "TWh" in name:
        return ",.2f"
    if "EUR" in name and "%" not in name:
        return ",.1f"
    if "(MWh)" in name:
        return f",.{MWH_DECIMALS}f"
    if "/" in name and "MAE" in name:  # ratios
        return ".2f"
    if "change" in name.lower():
        return f"+.{PCT_DECIMALS}f"
    if "%" in name:
        return f".{PCT_DECIMALS}f"
    if name in ("n", "n_days", "Days", "Hours / days", "Lead day", "Horizon", "Rank", "Models", "Origins"):
        return "d"
    return f",.{MWH_DECIMALS}f"


def fmt(df: pd.DataFrame) -> pd.DataFrame:
    """Numbers as text for Markdown: MWh without decimals, %, TWh and ratios with decimals."""
    out = df.copy()
    for col in out.columns:
        if not pd.api.types.is_numeric_dtype(out[col]) or pd.api.types.is_bool_dtype(out[col]):
            continue
        spec = _number_format(str(col))
        out[col] = out[col].map(lambda v, s=spec: "" if pd.isna(v) else format(int(v) if s == "d" else v, s))
    return out


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join(lines)


_LATEX_ESCAPES = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
                  "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def latex_escape(text) -> str:
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in str(text))


def latex_table(raw: pd.DataFrame, shown: pd.DataFrame, bold_rows=None) -> str:
    """
    A booktabs ``tabular`` for the LaTeX report. ``shown`` is the formatted table (``fmt``), ``raw`` the numbers
    (they decide the alignment: text columns left, numeric columns right). The bold rows are the same as in the
    Markdown table. Cells and headers are escaped, so the file can be ``\\input`` as it is.
    """
    def label(col) -> str:
        return " ".join(map(str, col)) if isinstance(col, tuple) else str(col)

    numeric = [pd.api.types.is_numeric_dtype(raw[c]) and not pd.api.types.is_bool_dtype(raw[c]) for c in raw.columns]
    bold = set(bold_rows) if bold_rows is not None else set()
    lines = [r"\begin{tabular}{" + "".join("r" if n else "l" for n in numeric) + "}", r"\toprule",
             " & ".join(latex_escape(label(c)) for c in shown.columns) + r" \\", r"\midrule"]
    for i, row in enumerate(shown.itertuples(index=False)):
        cells = ["" if pd.isna(v) else latex_escape(v) for v in row]
        if i in bold and cells[0]:  # as in the Markdown table: the label of the row
            cells[0] = r"\textbf{" + cells[0] + "}"
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


class Report:
    """Collects the tables: one CSV and one LaTeX ``tabular`` each, all of them in one Markdown file."""

    def __init__(self, out_dir: Path = TABLES_DIR, md_name: str = "report_tables.md", title: str = "Report tables",
                 prefix: str = ""):
        self.out_dir = Path(out_dir)
        self.md_name = md_name
        self.prefix = prefix
        self.parts: list[str] = [f"# {title}\n"]
        self.n_tables = 0
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def add(self, name: str, title: str, df: pd.DataFrame, note: str = "", bold_rows=None):
        df = df.reset_index(drop=True)
        df.to_csv(self.out_dir / f"{self.prefix}{name}.csv", index=False)
        shown = fmt(df).astype(object)
        (self.out_dir / f"{self.prefix}{name}.tex").write_text(latex_table(df, shown, bold_rows))
        if bold_rows is not None and len(shown):
            first = shown.columns[0]
            shown.loc[bold_rows, first] = "**" + shown.loc[bold_rows, first].astype(str) + "**"
        self.parts.append(f"## {title}\n")
        if note:
            self.parts.append(note + "\n")
        self.parts.append(md_table(shown) + "\n")
        self.n_tables += 1

    def section(self, title: str):
        self.parts.append(f"\n# {title}\n")

    def write(self) -> Path:
        path = self.out_dir / self.md_name
        path.write_text("\n".join(self.parts))
        return path