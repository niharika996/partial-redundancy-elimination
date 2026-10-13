"""
CFG and Optimization Visualizer.
Generates:
  1. Graphviz DOT files (.dot)
  2. Self-contained interactive HTML reports with side-by-side CFGs and Dataflow tables.
"""

from typing import Dict, List, Optional
import html
from src.cfg import CFG, BasicBlock
from src.lcm import LCMFramework
from src.transform import TransformationRecord


def generate_dot(
    cfg: CFG,
    title: str = "Control Flow Graph",
    records: Optional[Dict[str, TransformationRecord]] = None
) -> str:
    """
    Generates a Graphviz DOT representation of the CFG.
    """
    dot_lines = [
        'digraph CFG {',
        '    node [shape=box, style="filled,rounded", fontname="Courier New", fontsize=11];',
        '    edge [fontname="Helvetica", fontsize=10];',
        f'    labelloc="t"; label="{title}";',
        ''
    ]

    for block in cfg.get_all_blocks():
        if block == cfg.entry:
            dot_lines.append(f'    "{block.name}" [label="ENTRY", fillcolor="#d1e7dd", color="#0f5132", penwidth=2];')
        elif block == cfg.exit:
            dot_lines.append(f'    "{block.name}" [label="EXIT", fillcolor="#f8d7da", color="#842029", penwidth=2];')
            bg_color = "#e8f4fd" if "split" in block.name.lower() else "#ffffff"
            border_color = "#0284c7" if "split" in block.name.lower() else "#495057"
            table_lines = [
                f'<table border="1" cellborder="0" cellspacing="0" cellpadding="4" bgcolor="{bg_color}" color="{border_color}" style="rounded">',
                f'<tr><td align="center" border="0"><b>{block.name}</b></td></tr>',
                '<tr><td align="center" border="1" sides="t"></td></tr>'
            ]

            rec = records.get(block.name) if records else None

            if not block.instructions:
                table_lines.append('<tr><td align="left"><i>(empty)</i></td></tr>')
            else:
                for inst in block.instructions:
                    inst_str = html.escape(str(inst))
                    if rec and str(inst) in rec.inserted:
                        table_lines.append(f'<tr><td align="left"><font color="#198754"><b>+ {inst_str}</b></font></td></tr>')
                    elif rec and any(mod == str(inst) for _, mod in rec.replaced):
                        table_lines.append(f'<tr><td align="left"><font color="#0d6efd"><b>* {inst_str}</b></font></td></tr>')
                    else:
                        table_lines.append(f'<tr><td align="left">{inst_str}</td></tr>')

            table_lines.append('</table>')
            html_label = "<" + "".join(table_lines) + ">"
            dot_lines.append(f'    "{block.name}" [shape=none, margin=0, label={html_label}];')

    dot_lines.append('')
    # Add edges
    for block in cfg.get_all_blocks():
        for succ in block.succs:
            dot_lines.append(f'    "{block.name}" -> "{succ.name}";')

    dot_lines.append('}')
    return "\n".join(dot_lines)


def generate_html_report(
    original_cfg_dot: str,
    optimized_cfg_dot: str,
    lcm: LCMFramework,
    records: Dict[str, TransformationRecord],
    output_html_path: str
):
    """
    Generates a rich, standalone HTML dashboard with:
      - Summary Metrics
      - Data-flow analysis tables for each pass
      - Pre- vs Post-optimization code comparison
      - Embedded DOT graph visualizer via viz.js / SVG
    """
    universe_str = ", ".join(f"<code>{html.escape(str(e))}</code>" for e in lcm.universe) or "None"

    # Build Dataflow table rows
    df_rows = []
    for b in lcm.cfg.get_all_blocks():
        b_name = b.name
        ant_in = html.escape(repr(lcm.ant_in.get(b, {})))
        ant_out = html.escape(repr(lcm.ant_out.get(b, {})))
        earliest = html.escape(repr(lcm.earliest.get(b, {})))
        delay_in = html.escape(repr(lcm.delay_in.get(b, {})))
        latest = html.escape(repr(lcm.latest.get(b, {})))
        used_out = html.escape(repr(lcm.used_out.get(b, {})))

        df_rows.append(f"""
        <tr>
            <td><strong>{b_name}</strong></td>
            <td><code>{ant_in}</code></td>
            <td><code>{ant_out}</code></td>
            <td><code>{earliest}</code></td>
            <td><code>{delay_in}</code></td>
            <td><code>{latest}</code></td>
            <td><code>{used_out}</code></td>
        </tr>
        """)

    # Transformations list
    trans_items = []
    for b_name, rec in records.items():
        if rec.inserted or rec.replaced:
            for ins in rec.inserted:
                trans_items.append(f"<li class='inserted'><strong>{b_name}</strong>: Inserted <code>{html.escape(ins)}</code></li>")
            for orig, mod in rec.replaced:
                trans_items.append(f"<li class='replaced'><strong>{b_name}</strong>: Replaced <code>{html.escape(orig)}</code> &rarr; <code>{html.escape(mod)}</code></li>")

    if not trans_items:
        trans_html = "<p class='text-muted'>No redundancies found to eliminate.</p>"
    else:
        trans_html = "<ul>" + "".join(trans_items) + "</ul>"

    # HTML template with embedded styles & Viz.js for offline standalone rendering
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Partial Redundancy Elimination (PRE) - Lab Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js"></script>
    <style>
        :root {{
            --primary: #2563eb;
            --success: #16a34a;
            --danger: #dc2626;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text: #1e293b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 24px;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
        }}
        .header {{
            background: linear-gradient(135deg, #1e40af, #3b82f6);
            color: white;
            padding: 24px 32px;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 26px; }}
        .header p {{ margin: 0; opacity: 0.9; }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 18px;
            border-bottom: 2px solid var(--border);
            padding-bottom: 10px;
            color: #0f172a;
        }}
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 900px) {{
            .grid-2 {{ grid-template-columns: 1fr; }}
        }}
        .graph-container {{
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            overflow: auto;
            min-height: 350px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 12px;
        }}
        th, td {{
            border: 1px solid var(--border);
            padding: 10px 12px;
            text-align: left;
        }}
        th {{
            background: #f1f5f9;
            font-weight: 600;
        }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        code {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: Consolas, monospace;
            font-size: 12px;
        }}
        .inserted {{ color: var(--success); font-weight: 500; margin-bottom: 6px; }}
        .replaced {{ color: #0284c7; font-weight: 500; margin-bottom: 6px; }}
        .badge {{
            display: inline-block;
            background: #e2e8f0;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }}
    </style>
</head>
<body>

    <div class="header">
        <h1>Compiler Optimization: Partial Redundancy Elimination (PRE)</h1>
        <p>Implementation based on the Lazy Code Motion (LCM) Framework by Knoop, Rüthing, & Steffen</p>
    </div>

    <div class="card">
        <h2>Optimization Overview</h2>
        <p><strong>Candidate Universe Expressions (&Upsilon;):</strong> {universe_str}</p>
        <p><strong>Key Transformations Executed:</strong></p>
        {trans_html}
    </div>

    <div class="card">
        <h2>Side-by-Side Control Flow Graphs (CFG)</h2>
        <div class="grid-2">
            <div>
                <h3>1. Original CFG (After Critical Edge Splitting)</h3>
                <div class="graph-container" id="graph-orig">Loading Original CFG...</div>
            </div>
            <div>
                <h3>2. Optimized CFG (After Lazy Code Motion)</h3>
                <div class="graph-container" id="graph-opt">Loading Optimized CFG...</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>LCM Data-Flow Analysis Table</h2>
        <table>
            <thead>
                <tr>
                    <th>Block</th>
                    <th>ANTIN (Pass 1)</th>
                    <th>ANTOUT (Pass 1)</th>
                    <th>EARLIEST (Pass 2)</th>
                    <th>DELAYIN (Pass 3)</th>
                    <th>LATEST (Pass 3)</th>
                    <th>USEDOUT (Pass 4)</th>
                </tr>
            </thead>
            <tbody>
                {"".join(df_rows)}
            </tbody>
        </table>
    </div>

    <script>
        const origDot = `{original_cfg_dot.replace('`', '\\`')}`;
        const optDot = `{optimized_cfg_dot.replace('`', '\\`')}`;

        try {{
            const viz = new Viz();
            viz.renderSVGElement(origDot)
                .then(element => {{
                    const container = document.getElementById("graph-orig");
                    container.innerHTML = "";
                    container.appendChild(element);
                }})
                .catch(err => {{
                    document.getElementById("graph-orig").innerHTML = "<pre>" + origDot + "</pre>";
                }});

            viz.renderSVGElement(optDot)
                .then(element => {{
                    const container = document.getElementById("graph-opt");
                    container.innerHTML = "";
                    container.appendChild(element);
                }})
                .catch(err => {{
                    document.getElementById("graph-opt").innerHTML = "<pre>" + optDot + "</pre>";
                }});
        }} catch(e) {{
            document.getElementById("graph-orig").innerHTML = "<pre>" + origDot + "</pre>";
            document.getElementById("graph-opt").innerHTML = "<pre>" + optDot + "</pre>";
        }}
    </script>
</body>
</html>
"""
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
