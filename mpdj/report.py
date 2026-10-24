"""Discovery report: artists that keep showing up as 'similar' that you don't have."""
from __future__ import annotations

import html
import sqlite3
import time
from pathlib import Path
from urllib.parse import quote_plus

from .names import norm


def suggestions(con: sqlite3.Connection, library_artists: list[str], min_count: int = 3) -> list[tuple[int, str, float]]:
    """[(times seen, name, summed match)] for artists not in the library, most seen first."""
    have = {norm(a) for a in library_artists}
    ignore = {r["norm"] for r in con.execute("SELECT norm FROM suggest_ignore")}
    rows = con.execute(
        "SELECT other_norm, MAX(other) AS name, COUNT(*) AS n, SUM(match) AS m FROM similar "
        "GROUP BY other_norm HAVING n >= ? ORDER BY n DESC, m DESC", (min_count,)).fetchall()
    return [(r["n"], r["name"], r["m"]) for r in rows
            if r["other_norm"] not in have and r["other_norm"] not in ignore]


def write_html(path: Path, rows: list[tuple[int, str, float]], links: list[list[str]],
               seeds: int) -> Path:
    esc = html.escape
    head = "".join(f"<th>{esc(label)}</th>" for label, _ in links)
    body = []
    for n, name, m in rows:
        cells = "".join(
            f'<td><a href="{esc(tpl.format(q=quote_plus(name)))}" target="_blank" rel="noopener">{esc(label)}</a></td>'
            for label, tpl in links)
        body.append(f"<tr><td class=n>{n}</td><td class=n>{m:.1f}</td><td>{esc(name)}</td>{cells}</tr>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Suggested Artists</title>
<style>
:root {{ --bg:#fff; --fg:#1a1a1a; --muted:#666; --line:#e3e3e3; --link:#0b57d0; --stripe:#f6f6f6; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141414; --fg:#e8e8e8; --muted:#999; --line:#2c2c2c; --link:#8ab4f8; --stripe:#1b1b1b; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.4 system-ui,sans-serif; margin:0 auto; padding:24px 16px; max-width:900px; }}
h1 {{ font-size:1.4rem; margin:0 0 4px; }} p {{ color:var(--muted); margin:0 0 16px; }}
table {{ border-collapse:collapse; width:100%; }}
th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }}
tr:nth-child(even) td {{ background:var(--stripe); }}
td.n {{ font-variant-numeric:tabular-nums; color:var(--muted); width:4em; }}
a {{ color:var(--link); }}
</style></head><body>
<h1>Suggested Artists</h1>
<p>{len(rows)} artists you don't have, from the similar-artist lists of {seeds} artists you do.
Generated {time.strftime('%Y-%m-%d %H:%M')}. Hide one with <code>mpdj suggest --ignore "Name"</code>.</p>
<table><thead><tr><th>Seen</th><th>Match</th><th>Artist</th>{head}</tr></thead>
<tbody>
{chr(10).join(body)}
</tbody></table></body></html>
""")
    return path
