"""
Partial Redundancy Elimination (PRE) Framework CLI.
Runs the complete Lazy Code Motion (LCM) optimization pipeline on TAC input.
"""

import sys
import os
import argparse
import copy
from typing import Dict

from src.parser import parse_tac_file
from src.cfg import build_cfg, CFG
from src.lcm import LCMFramework
from src.transform import LCMTransformer
from src.visualizer import generate_dot, generate_html_report


def print_banner():
    banner = """
================================================================================
   PARTIAL REDUNDANCY ELIMINATION (PRE) FRAMEWORK - LAZY CODE MOTION (LCM)
================================================================================
"""
    print(banner)


def print_table(title: str, headers: list, rows: list):
    print(f"\n--- {title} ---")
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header_str = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    sep_str = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_str)
    print(sep_str)
    for row in rows:
        print(" | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row)))


def run_pipeline(input_file: str, output_dir: str = "output", verbose: bool = False):
    print_banner()
    print(f"[*] Reading input TAC file: {input_file}")
    instructions = parse_tac_file(input_file)

    # 1. Build initial CFG
    cfg = build_cfg(instructions)
    print(f"[*] Initial CFG constructed with {len(cfg.blocks)} basic blocks.")

    # 2. Split Critical Edges
    split_logs = cfg.split_critical_edges()
    if split_logs:
        print("[*] Critical Edge Splitting:")
        for log in split_logs:
            print(f"    - {log}")
    else:
        print("[*] No critical edges detected.")

    # Clone CFG for pre-optimization visualization
    orig_dot = generate_dot(cfg, title="Original CFG (Edges Split)")

    # 3. Initialize LCM Framework
    lcm = LCMFramework(cfg)
    universe_str = ", ".join(str(e) for e in lcm.universe) or "{}"
    print(f"\n[*] Candidate Expressions Universe (U): {universe_str}")

    # Display Local Block Properties
    local_rows = []
    for b in cfg.get_user_blocks():
        lp = lcm.locals[b]
        local_rows.append([
            b.name,
            repr(lp.e_use),
            repr(lp.e_kill),
            repr(lp.e_gen)
        ])
    print_table("Local Block Properties", ["Block", "e_use (Upward)", "e_kill", "e_gen (Downward)"], local_rows)

    # 4. Run LCM Passes
    print("\n[*] Executing 4-Pass Lazy Code Motion...")
    lcm.run_all_passes()
    print("    [+] Pass 1: Anticipated Expressions (Backward) - Converged in "
          f"{len(lcm.ant_history)} iterations.")
    print("    [+] Pass 2: Available & Earliest (Forward)      - Converged in "
          f"{len(lcm.av_history)} iterations.")
    print("    [+] Pass 3: Postponable & Latest (Forward)     - Converged in "
          f"{len(lcm.delay_history)} iterations.")
    print("    [+] Pass 4: Used Expressions (Backward)        - Converged in "
          f"{len(lcm.used_history)} iterations.")

    # Display LCM Results Table
    df_rows = []
    for b in cfg.get_user_blocks():
        df_rows.append([
            b.name,
            repr(lcm.ant_in[b]),
            repr(lcm.ant_out[b]),
            repr(lcm.earliest[b]),
            repr(lcm.delay_in[b]),
            repr(lcm.latest[b]),
            repr(lcm.used_out[b])
        ])
    print_table("LCM Data-Flow Solution Sets",
                ["Block", "ANTIN", "ANTOUT", "EARLIEST", "DELAYIN", "LATEST", "USEDOUT"],
                df_rows)

    # 5. Transform Code
    print("\n[*] Applying Code Transformation (Insertion at LATEST & Redundancy Replacement)...")
    transformer = LCMTransformer(lcm)
    records = transformer.transform()

    total_inserted = sum(len(r.inserted) for r in records.values())
    total_replaced = sum(len(r.replaced) for r in records.values())
    print(f"    [+] Computations Inserted: {total_inserted}")
    print(f"    [+] Computations Replaced: {total_replaced}")

    for b_name, rec in records.items():
        for ins in rec.inserted:
            print(f"        [+] [{b_name}] INSERT: {ins}")
        for orig, mod in rec.replaced:
            print(f"        [-] [{b_name}] REPLACE: {orig}  ==>  {mod}")

    # Generate output directory if not exists
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_file))[0]

    # Save Transformed TAC
    out_tac_path = os.path.join(output_dir, f"{base_name}_optimized.tac")
    with open(out_tac_path, "w", encoding="utf-8") as f:
        for b in cfg.get_user_blocks():
            f.write(f"// Block {b.name}\n")
            for inst in b.instructions:
                f.write(f"{inst}\n")
            f.write("\n")
    print(f"\n[*] Optimized TAC saved to: {out_tac_path}")

    # 6. Generate Visualizations (DOT and HTML)
    opt_dot = generate_dot(cfg, title="Optimized CFG (Post-LCM)", records=records)
    orig_dot_path = os.path.join(output_dir, f"{base_name}_orig.dot")
    opt_dot_path = os.path.join(output_dir, f"{base_name}_opt.dot")

    with open(orig_dot_path, "w", encoding="utf-8") as f:
        f.write(orig_dot)
    with open(opt_dot_path, "w", encoding="utf-8") as f:
        f.write(opt_dot)
    print(f"[*] Graphviz DOT files saved to: {orig_dot_path} and {opt_dot_path}")

    html_path = os.path.join(output_dir, f"{base_name}_report.html")
    generate_html_report(orig_dot, opt_dot, lcm, records, html_path)
    print(f"[*] Interactive Visual Dashboard saved to: {html_path}")
    print("\n[SUCCESS] PRE optimization successfully finished!\n")


def main():
    parser = argparse.ArgumentParser(description="Partial Redundancy Elimination (PRE) Framework")
    parser.add_argument("input", nargs="?", default="input_examples/01_classic_pre.tac",
                        help="Path to the input TAC file (default: input_examples/01_classic_pre.tac)")
    parser.add_argument("-o", "--output", default="output",
                        help="Output directory for generated files (default: output)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose iteration logs")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)

    run_pipeline(args.input, args.output, args.verbose)


if __name__ == "__main__":
    main()
