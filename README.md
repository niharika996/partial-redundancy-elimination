# ⚡ Partial Redundancy Elimination (PRE) Framework
### Compiler Optimization via Lazy Code Motion (LCM)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: Passing](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/test_pre.py)
[![Course: Compiler Design](https://img.shields.io/badge/Course-Compiler%20Design%20Lab-orange.svg)](#)

A complete, self-contained, and mathematically verified implementation of the **Partial Redundancy Elimination (PRE)** optimization framework based on **Lazy Code Motion (LCM)** (*Knoop, Rüthing, Steffen 1994* / *Dragon Book Chapter 9*).

Operates directly on **Three-Address Code (TAC)** Intermediate Representation, builds Control Flow Graphs, splits critical edges, executes four unidirectional bitvector dataflow analyses, rewrites code to eliminate redundant calculations, and outputs interactive visual CFG dashboards.

---

## 🌟 Key Features

* **Subsumes Classic Optimizations**: Unifies both **Common Subexpression Elimination (CSE)** and **Loop-Invariant Code Motion (LICM)** into a single unified framework.
* **Dual Optimality**:
  * **Computational Optimality**: Guarantees no execution path computes an expression more times than the original program.
  * **Lifetime Optimality**: Places hoisted expressions as late as possible (*lazily*), minimizing register pressure.
* **Critical Edge Splitting**: Automatically detects and splits edges between multi-successor and multi-predecessor blocks to guarantee safe code motion.
* **Pure Python Standard Library**: Zero external dependencies required to run the pipeline or dataflow passes.
* **Interactive Visualization**: Generates both Graphviz `.dot` files and self-contained interactive HTML dashboards showing side-by-side CFGs before and after optimization.
* **Automated Regression Suite**: Unit tests verifying BitVector operations, CFG leader detection, branch hoisting, CSE, and loop hoisting.

---

## 🏗️ Architecture & Pipeline

```
[ Input TAC File ]
        │
        ▼
[ TAC Parser & Lexer ] ────────────► Tokenizes instructions, expressions, and branches
        │
        ▼
[ CFG Construction ] ──────────────► Partitions basic blocks and connects control edges
        │
        ▼
[ Critical Edge Splitter ] ────────► Inserts synthetic landing blocks (B_split_k)
        │
        ▼
[ LCM Data-Flow Engine ]
  ├─ Pass 1: Anticipability (Backward, ∩)  ──► Guarantees Safety
  ├─ Pass 2: Available & Earliest (Forward, ∩)──► Finds earliest placement points
  ├─ Pass 3: Postponable & Latest (Forward, ∩)──► Delays placement (Lifetime optimality)
  └─ Pass 4: Used Expressions (Backward, ∪) ──► Prunes isolated/dead placements
        │
        ▼
[ Code Transformation ] ───────────► Inserts temporaries (t_e) at LATEST & replaces redundant math
        │
        ├──────────────────────────┐
        ▼                          ▼
[ Optimized TAC Output ]   [ Visual CFG Dashboard (HTML / DOT) ]
```

---

## 📂 Project Structure

```
.
├── main.py                    # Main CLI runner & pipeline orchestrator
├── README.md                  # GitHub Project Overview & Documentation
├── TEAM_EXPLAINER.md          # Comprehensive Academic Project Report Dossier
├── .gitignore                 # Standard Python ignore rules
├── src/
│   ├── ir.py                  # Intermediate Representation (TAC, Expressions, Instructions)
│   ├── parser.py              # Regex-based TAC Parser
│   ├── cfg.py                 # BasicBlock, CFG builder & Critical Edge Splitting
│   ├── dataflow.py            # BitVector engine & Fixed-point iterative solver
│   ├── lcm.py                 # The 4 Lazy Code Motion passes
│   ├── transform.py           # Temporary variable allocation & expression rewriter
│   └── visualizer.py         # Graphviz DOT generator & HTML dashboard creator
├── input_examples/
│   ├── 01_classic_pre.tac     # Benchmark 1: Partial redundancy on branch
│   ├── 02_cse.tac             # Benchmark 2: Common Subexpression Elimination
│   ├── 03_licm.tac            # Benchmark 3: Loop-Invariant Code Motion
│   └── 04_critical_edge.tac   # Benchmark 4: Critical Edge Splitting
├── tests/
│   └── test_pre.py            # Automated unit tests (unittest)
└── output/                    # Generated DOT graphs, HTML reports, and optimized TAC
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/niharika996/partial-redundancy-elimination.git
cd partial-redundancy-elimination
```

### 2. Run the Optimizer
Run the framework on the classic PRE benchmark:
```bash
python main.py input_examples/01_classic_pre.tac
```

**Terminal Output:**
```
================================================================================
   PARTIAL REDUNDANCY ELIMINATION (PRE) FRAMEWORK - LAZY CODE MOTION (LCM)
================================================================================
[*] Reading input TAC file: input_examples/01_classic_pre.tac
[*] Initial CFG constructed with 4 basic blocks.
[*] Candidate Expressions Universe (U): a + b

--- LCM Data-Flow Solution Sets ---
Block | ANTIN   | ANTOUT  | EARLIEST | DELAYIN | LATEST  | USEDOUT
------+---------+---------+----------+---------+---------+--------
B1    | {a + b} | {a + b} | {a + b}  | {}      | {}      | {}     
B2    | {a + b} | {a + b} | {}       | {a + b} | {a + b} | {a + b}
B3    | {a + b} | {a + b} | {}       | {a + b} | {a + b} | {a + b}
B4    | {a + b} | {a + b} | {}       | {}      | {}      | {}     

[*] Applying Code Transformation...
    [+] [B2] INSERT: t_a_add_b = a + b
    [-] [B2] REPLACE: x = a + b  ==>  x = t_a_add_b
    [+] [B3] INSERT: t_a_add_b = a + b
    [-] [B4] REPLACE: y = a + b  ==>  y = t_a_add_b

[SUCCESS] PRE optimization successfully finished!
```

### 3. View the Interactive Visual Dashboard
Open the generated HTML dashboard in your web browser:
```bash
# Windows
start output/01_classic_pre_report.html

# macOS
open output/01_classic_pre_report.html

# Linux
xdg-open output/01_classic_pre_report.html
```
The dashboard renders side-by-side SVG Control Flow Graphs with inserted instructions highlighted in green (`+`) and replaced redundant instructions in blue (`*`).

### 4. Run Automated Test Suite
```bash
python -m unittest discover tests
```
Output:
```
.....
----------------------------------------------------------------------
Ran 5 tests in 0.004s

OK
```

---

## 📊 Benchmark Suite

| Benchmark | File | Scenario | Optimization Applied |
| :--- | :--- | :--- | :--- |
| **01: Classic PRE** | `01_classic_pre.tac` | Expression `a + b` evaluated on `else` path and in join block. | Inserts `t = a + b` on `then` path (`B3`); eliminates evaluation in join block (`B4`). |
| **02: Full CSE** | `02_cse.tac` | Expression `x * y` computed in `B1` and recomputed in `B4`. | Subsumes CSE: detects full availability and replaces second computation with `t2 = t_x_mul_y`. |
| **03: LICM** | `03_licm.tac` | Expression `base * factor` inside a 100-iteration loop. | Subsumes LICM: hoists computation to loop pre-header (`B1`); loop executes only once. |
| **04: Edge Split** | `04_critical_edge.tac` | Multi-successor to multi-predecessor control edge. | Detects critical edge; splits edge via `B_split_1` to safely place hoisted code. |

---

## 📖 Academic Documentation & Project Report

If you are preparing a college/university project report, refer to **[`TEAM_EXPLAINER.md`](TEAM_EXPLAINER.md)**. It provides a complete academic dossier including:
- Formal Abstract and Problem Formulation.
- Complete LaTeX mathematical dataflow equations ($ANTIN, AVIN, DELAYIN, USEDIN$).
- Literature review (Morel & Renvoise vs. Knoop et al.).
- Empirical results with before-and-after TAC code and convergence tables.
- Formal bibliography and citations.

---

## 📜 License

This project is open-source and available under the [MIT License](LICENSE).
