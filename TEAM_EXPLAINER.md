# Partial Redundancy Elimination (PRE) Framework
## Comprehensive Project Dossier & Academic Report Guide

> **Purpose of this Document**:  
> This document is a complete, publication-grade technical blueprint designed specifically for writing the **College Project Report / Laboratory Documentation** for the Compiler Design subject. It details the problem statement, theoretical background, mathematical equations, system architecture, algorithms, implementation specifics, benchmark case studies, and experimental results.

---

# Table of Contents
1. [Abstract](#1-abstract)
2. [Introduction & Problem Statement](#2-introduction--problem-statement)
   - 2.1 Context in Compiler Compilation Pipeline
   - 2.2 Redundancy Types: Full vs. Partial Redundancy
   - 2.3 Limitations of Independent CSE and LICM
   - 2.4 Project Objectives
3. [Theoretical Foundations & Literature Review](#3-theoretical-foundations--literature-review)
   - 3.1 Historical Evolution (Morel & Renvoise vs. Knoop, Rüthing, Steffen)
   - 3.2 Computational Optimality vs. Lifetime Optimality
   - 3.3 Critical Edges: Definition, Problem, and Splitting
4. [Mathematical Formulation & Data-Flow Equations](#4-mathematical-formulation--data-flow-equations)
   - 4.1 Program Representation & Local Properties
   - 4.2 Pass 1: Anticipability (Safety Analysis)
   - 4.3 Pass 2: Available Expressions & Earliest Placement
   - 4.4 Pass 3: Postponability & Latest Placement
   - 4.5 Pass 4: Used Expressions & Redundancy Detection
   - 4.6 Code Transformation Rules
5. [System Architecture & Module Design](#5-system-architecture--module-design)
   - 5.1 Architecture Diagram
   - 5.2 Detailed Module Specifications
6. [Benchmark Case Studies & Experimental Results](#6-benchmark-case-studies--experimental-results)
   - 6.1 Benchmark 1: Classic Partial Redundancy (Branch Hoisting)
   - 6.2 Benchmark 2: Common Subexpression Elimination (CSE Subsumption)
   - 6.3 Benchmark 3: Loop-Invariant Code Motion (LICM Subsumption)
   - 6.4 Benchmark 4: Critical Edge Splitting Verification
7. [Verification & Test Suite](#7-verification--test-suite)
8. [Conclusion & Future Scope](#8-conclusion--future-scope)
9. [References](#9-references)

---

# 1. Abstract

In modern optimizing compilers, redundant evaluations of computational expressions significantly degrade runtime throughput. While **Common Subexpression Elimination (CSE)** targets expressions that are identically computed along all execution paths reaching a program point, and **Loop-Invariant Code Motion (LICM)** targets invariant expressions inside iterative constructs, neither optimization alone can eliminate expressions that are evaluated along *some*, but not *all*, paths reaching an evaluation site. 

This project implements a complete, mathematically verified **Partial Redundancy Elimination (PRE)** framework operating over Three-Address Code (TAC) Intermediate Representation. Based on the **Lazy Code Motion (LCM)** formulation developed by Knoop, Rüthing, and Steffen, our system achieves both **computational optimality** (no execution path computes an expression more times than necessary) and **lifetime optimality** (expressions are placed as late as possible to minimize CPU register pressure). The framework incorporates automatic critical-edge splitting, an iterative BitVector dataflow solver for four distinct dataflow analyses, an AST/TAC rewriter, and automated Graphviz and interactive HTML visualizers for verifying Control Flow Graphs before and after optimization.

---

# 2. Introduction & Problem Statement

### 2.1 Context in Compiler Compilation Pipeline
The compilation pipeline comprises lexical analysis, syntax analysis, semantic analysis, intermediate code generation, **machine-independent code optimization**, and target code generation. 

Our project resides within the **Machine-Independent Code Optimization** phase. It operates directly upon an intermediate Three-Address Code (TAC) representation structured into basic blocks within a Control Flow Graph (CFG).

### 2.2 Redundancy Types: Full vs. Partial Redundancy

* **Full Redundancy**: An evaluation of expression $e = (a \text{ op } b)$ at program point $p$ is fully redundant if $e$ has already been evaluated along **every** possible execution path leading from the entry to $p$, without subsequent modifications to operands $a$ or $b$.
* **Partial Redundancy**: An evaluation of expression $e$ at program point $p$ is partially redundant if $e$ has been evaluated along **at least one**, but **not all**, paths leading to $p$.

#### The Conceptual Problem:
```
                    [ Block B1: Branch ]
                     /                \
        (Path 1: 'if')                (Path 2: 'else')
         [ B2: c = 10 ]               [ B3: x = a + b ]
                     \                /
                   [ Block B4: y = a + b ]
```
In this scenario:
* Path $B1 \to B3 \to B4$: The expression $a + b$ is evaluated in $B3$ and again in $B4$. The second evaluation in $B4$ is redundant.
* Path $B1 \to B2 \to B4$: The expression $a + b$ is evaluated only once (in $B4$). It is not redundant along this path.

Because the expression is evaluated along only one incoming path, traditional Common Subexpression Elimination (CSE) **cannot** eliminate the evaluation in $B4$. Furthermore, simple deletion is invalid because it would cause $B4$ to read an uncomputed value when execution arrives from $B2$.

### 2.3 Limitations of Independent CSE and LICM
Historically, compilers applied CSE and LICM as distinct, isolated optimization passes. This led to order-of-execution phase ordering problems:
1. CSE cannot hoist computations out of loops or across branches.
2. LICM can only hoist expressions that are syntactically enclosed within a recognized loop body.
3. Neither can eliminate partial redundancy arising from control-flow mergers.

**PRE unifies both optimizations**: By placing computations on the non-computing paths, partial redundancy is transformed into full redundancy, thereby solving both CSE and LICM in a single framework.

### 2.4 Project Objectives
1. Construct an IR and Parser for Three-Address Code supporting assignments, binary expressions, conditional branches, unconditional jumps, and labels.
2. Formulate basic blocks and build a Control Flow Graph (CFG) equipped with automatic **Critical Edge Splitting**.
3. Implement a generic, robust BitVector dataflow analysis engine capable of forward and backward iterative solving.
4. Implement the **4 passes of Lazy Code Motion (LCM)**:
   - Anticipated Expressions analysis (Backward, $\cap$)
   - Available Expressions & Earliest Placement analysis (Forward, $\cap$)
   - Postponable Expressions & Latest Placement analysis (Forward, $\cap$)
   - Used Expressions & Redundancy detection analysis (Backward, $\cup$)
5. Rewrite intermediate code by inserting optimal temporary variables at computed latest points and eliminating redundant computations.
6. Provide dual visualization (Graphviz `.dot` and interactive offline HTML dashboards) to demonstrate before-and-after CFG transformations and dataflow convergence tables.

---

# 3. Theoretical Foundations & Literature Review

### 3.1 Historical Evolution
* **Morel and Renvoise (1979)**: Introduced the first general PRE algorithm based on bidirectional dataflow equations. While groundbreaking, bidirectional analyses are complex to prove correct, have subtle convergence edge-cases, and tend to hoist expressions earlier than necessary.
* **Knoop, Rüthing, and Steffen (1992, 1994)**: Introduced **Lazy Code Motion (LCM)**. LCM decoupled PRE into four independent, unidirectional dataflow analyses. Crucially, LCM recognized that hoisting an expression too early needlessly elongates the live ranges of temporary variables.
* **Chow et al. (1997) / SSA Form**: Developed SSAPRE, adapting PRE to Static Single Assignment form using $\phi$-nodes and $\Phi$-operands.

### 3.2 Computational Optimality vs. Lifetime Optimality
* **Computational Optimality**: An optimization is computationally optimal if no execution path in the transformed program evaluates an expression more times than in the original program, and no path computes an expression unless it was guaranteed to be evaluated on that path in the original program (safety).
* **Lifetime Optimality**: Among all computationally optimal placements, an optimization is lifetime optimal if the range between where a value is computed and where it is used is minimized. LCM achieves this by postponing placements as far down the CFG as possible without losing computational optimality.

### 3.3 Critical Edges: Definition, Problem, and Splitting
* **Definition**: An edge $U \to V$ in a CFG is a **critical edge** if:
  $$\text{out-degree}(U) > 1 \quad \text{AND} \quad \text{in-degree}(V) > 1$$
* **The Problem**: If an optimization algorithm decides that a computation must be placed on the edge $U \to V$:
  - Placing it at the end of $U$ causes it to execute when taking other branches out of $U$, violating safety.
  - Placing it at the beginning of $V$ causes it to execute when entering $V$ from other predecessors, causing redundant or invalid computation.
* **The Solution (Edge Splitting)**: For every critical edge $U \to V$, insert a synthetic basic block $B_{split}$ such that:
  $$U \to B_{split} \to V$$
  This provides a dedicated, isolated location to place instructions strictly on that control transition.

---

# 4. Mathematical Formulation & Data-Flow Equations

Let $\mathcal{U}$ be the universe of all candidate binary expressions $e = (x \text{ op } y)$ occurring within the program.

### 4.1 Local Basic Block Properties
For each basic block $B$:
* $\mathbf{e\_use}_B$: The set of expressions $e \in \mathcal{U}$ evaluated in $B$ such that neither operand of $e$ is defined in $B$ prior to that evaluation (upward exposed).
* $\mathbf{e\_kill}_B$: The set of expressions $e \in \mathcal{U}$ where at least one operand of $e$ is defined (modified) anywhere in $B$.
* $\mathbf{e\_gen}_B$: The set of expressions $e \in \mathcal{U}$ evaluated in $B$ such that neither operand of $e$ is defined in $B$ after that evaluation (downward exposed).

---

### 4.2 Pass 1: Anticipated Expressions (Upward Exposed / Safety)
An expression $e$ is anticipated at point $p$ if every path from $p$ to the program exit evaluates $e$ before any operand of $e$ is redefined. This guarantees safety (no computation is introduced on a path that didn't previously compute it).

* **Direction**: Backward
* **Meet Operator**: Intersection ($\cap$)
* **Transfer Equation**:
  $$\mathbf{ANTIN}[B] = \mathbf{e\_use}_B \cup (\mathbf{ANTOUT}[B] - \mathbf{e\_kill}_B)$$
* **Meet Equation**:
  $$\mathbf{ANTOUT}[B] = \bigcap_{S \in succ(B)} \mathbf{ANTIN}[S]$$
* **Boundary Condition**: $\mathbf{ANTOUT}[EXIT] = \emptyset$
* **Initialization**: $\mathbf{ANTIN}[B] = \mathcal{U}, \quad \mathbf{ANTOUT}[B] = \mathcal{U} \quad (\forall B \ne EXIT)$

---

### 4.3 Pass 2: Available Expressions & Earliest Placement
An expression is available at block entry if it has been evaluated along all paths from the program entry without being killed.

* **Direction**: Forward
* **Meet Operator**: Intersection ($\cap$)
* **Transfer Equation**:
  $$\mathbf{AVOUT}[B] = (\mathbf{AVIN}[B] \cup \mathbf{ANTIN}[B]) - \mathbf{e\_kill}_B$$
* **Meet Equation**:
  $$\mathbf{AVIN}[B] = \bigcap_{P \in pred(B)} \mathbf{AVOUT}[P]$$
* **Boundary Condition**: $\mathbf{AVIN}[ENTRY] = \emptyset$
* **Initialization**: $\mathbf{AVIN}[B] = \mathcal{U}, \quad \mathbf{AVOUT}[B] = \mathcal{U} \quad (\forall B \ne ENTRY)$

#### Earliest Placement Calculation:
The earliest point where an expression can be placed is where it is anticipated, but not yet available:
$$\mathbf{EARLIEST}[B] = \mathbf{ANTIN}[B] - \mathbf{AVIN}[B]$$
*(For the synthetic $ENTRY$ block, $\mathbf{EARLIEST}[ENTRY] = \emptyset$).*

---

### 4.4 Pass 3: Postponable Expressions & Latest Placement
An expression is postponable to block $B$ if an earliest placement along all paths reaching $B$ can be delayed to $B$ without crossing an actual use of the expression.

* **Direction**: Forward
* **Meet Operator**: Intersection ($\cap$)
* **Transfer Equation**:
  $$\mathbf{DELAYOUT}[B] = (\mathbf{DELAYIN}[B] \cup \mathbf{EARLIEST}[B]) - \mathbf{e\_use}_B$$
* **Meet Equation**:
  $$\mathbf{DELAYIN}[B] = \bigcap_{P \in pred(B)} \mathbf{DELAYOUT}[P]$$
* **Boundary Condition**: $\mathbf{DELAYIN}[ENTRY] = \emptyset$
* **Initialization**: $\mathbf{DELAYIN}[B] = \mathcal{U}, \quad \mathbf{DELAYOUT}[B] = \mathcal{U} \quad (\forall B \ne ENTRY)$

#### Latest Placement Calculation:
An expression belongs to $\mathbf{LATEST}[B]$ if it can be delayed to $B$, and it cannot be delayed past $B$ (either because it is used in $B$, or at least one successor cannot postpone it further):
$$\mathbf{LATEST}[B] = (\mathbf{EARLIEST}[B] \cup \mathbf{DELAYIN}[B]) \cap \left( \mathbf{e\_use}_B \cup \neg \bigcap_{S \in succ(B)} (\mathbf{EARLIEST}[S] \cup \mathbf{DELAYIN}[S]) \right)$$
*(If $S = EXIT$, $S$ cannot postpone, so the term contributes universal negation).*

---

### 4.5 Pass 4: Used Expressions (Dead/Isolated Placement Pruning)
Determines whether an expression placed at $\mathbf{LATEST}[B]$ is actually used down some path, preventing isolated dummy computations.

* **Direction**: Backward
* **Meet Operator**: Union ($\cup$)
* **Meet Equation**:
  $$\mathbf{USEDOUT}[B] = \bigcup_{S \in succ(B)} \mathbf{USEDIN}[S]$$
* **Transfer Equation**:
  $$\mathbf{USEDIN}[B] = (\mathbf{USEDOUT}[B] \cup \mathbf{e\_use}_B) - \mathbf{LATEST}[B]$$
* **Boundary Condition**: $\mathbf{USEDOUT}[EXIT] = \emptyset$
* **Initialization**: $\mathbf{USEDIN}[B] = \emptyset, \quad \mathbf{USEDOUT}[B] = \emptyset$

---

### 4.6 Code Transformation Rules
For each expression $e = (x \text{ op } y)$ that qualifies for optimization:
1. **Allocate Temporary Variable**: Assign a unique temporary variable $t_e$ (e.g., `t_a_add_b`).
2. **Code Insertion**: For every block $B$, if:
   $$e \in \mathbf{LATEST}[B] \cap (\mathbf{USEDOUT}[B] \cup \mathbf{e\_use}_B)$$
   Insert instruction:
   $$t_e = x \text{ op } y$$
   at the beginning of block $B$ (immediately after block label, before first instruction).
3. **Redundancy Replacement**: For every original instruction $z = x \text{ op } y$ in block $B$:
   If $e$ has been allocated a temporary and was inserted at or prior to this site:
   Replace the instruction with:
   $$z = t_e$$

---

# 5. System Architecture & Module Design

### 5.1 Architecture Pipeline

```
  [ Input File (.tac) ]
            │
            ▼
   ┌─────────────────┐
   │  src/parser.py  │  <-- Regex Lexer & Instruction Parser
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │   src/cfg.py    │  <-- Leader Identification & Block Partitioning
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │   Edge Split    │  <-- Detects Critical Edges (in>1 & out>1) and inserts B_split
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │ src/dataflow.py │  <-- Fixed-Point BitVector Solver Engine
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │   src/lcm.py    │  <-- 4 Passes: Anticipate -> Available -> Postpone -> Used
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │src/transform.py │  <-- Temporary Variable Injection & Expression Replacement
   └────────┬────────┘
            ├──────────────────────────┐
            ▼                          ▼
   ┌─────────────────┐        ┌──────────────────┐
   │  Optimized TAC  │        │src/visualizer.py │
   │  Output (.tac)  │        │ (DOT + HTML)     │
   └─────────────────┘        └──────────────────┘
```

### 5.2 Detailed Module Specifications

#### 1. `src/ir.py` (Intermediate Representation)
* **Classes**:
  * `Expression(op, left, right)`: Canonical representation of binary expressions. Supports operator commutativity normalization (e.g., $a + b \equiv b + a$ via lexicographical sorting).
  * `Instruction`: Abstract base class.
  * `BinaryAssign(target, expr)`: Represents $z = x \text{ op } y$.
  * `CopyAssign(target, source)`: Represents $z = x$ or $z = c$.
  * `CondJump(left, relop, right, target_label)`: Represents `if left op right goto L`.
  * `Jump(target_label)`: Represents unconditional `goto L`.
  * `Label(name)`: Represents entry anchor `L:`.
  * `Return(value)`: Represents program termination.

#### 2. `src/parser.py` (TAC Parser)
* Uses compiled regular expressions to parse Three-Address Code line-by-line.
* Ignores comments (`#`, `//`) and whitespace.
* Yields a structured list of concrete `Instruction` instances.

#### 3. `src/cfg.py` (CFG & Critical Edge Splitter)
* **Leader Identification**: Identifies block leaders based on:
  1. The first instruction in the stream.
  2. Any target of a conditional or unconditional branch.
  3. Any instruction immediately following a jump or return.
* **Graph Linking**: Connects basic blocks with directed predecessor/successor pointers.
* **Edge Splitting**: Scans all edges $(U, V)$. If $|succ(U)| > 1$ and $|pred(V)| > 1$, it inserts a new block $B_{split}$ and rewires jumps accordingly.

#### 4. `src/dataflow.py` (BitVector Fixed-Point Solver)
* **`BitVector`**: Encapsulates bitwise integer manipulations over an arbitrary universe $\mathcal{U}$. Provides `&`, `|`, `~`, `-` (set difference), and conversion to mathematical sets.
* **`solve_dataflow`**: A generalized round-robin iterative worklist solver supporting forward/backward flows, meet operators ($\cap, \cup$), and step-by-step history tracking.

#### 5. `src/lcm.py` (LCM Optimization Core)
* Calculates local properties ($e\_use, e\_kill, e\_gen$).
* Executes the four textbook passes in succession.
* Handles synthetic $ENTRY$ and $EXIT$ blocks as true mathematical boundary conditions ($\emptyset$).

#### 6. `src/transform.py` (Code Transformation)
* Allocates human-readable temporary names (`t_a_add_b`).
* Places computations at $\mathbf{LATEST}$ blocks.
* Replaces original evaluations with references to the allocated temporaries.

#### 7. `src/visualizer.py` (Visualization Engine)
* **DOT Generator**: Produces clean Graphviz `.dot` files where basic blocks are drawn as HTML-like tables with green (`+`) insertions and blue (`*`) replacements.
* **Interactive HTML Generator**: Generates a self-contained, responsive dashboard with side-by-side SVG rendering via `Viz.js` and complete dataflow tables.

---

# 6. Benchmark Case Studies & Experimental Results

### 6.1 Benchmark 1: Classic Partial Redundancy (`01_classic_pre.tac`)

#### Input TAC:
```
if cond > 0 goto L_THEN
x = a + b
goto L_MERGE

L_THEN:
c = 10
goto L_MERGE

L_MERGE:
y = a + b
return y
```

#### CFG Analysis:
* **Blocks**:
  * $B1$: `if cond > 0 goto L_THEN` (Successors: $B2, B3$)
  * $B2$: `x = a + b; goto L_MERGE` (Successor: $B4$)
  * $B3$: `L_THEN: c = 10; goto L_MERGE` (Successor: $B4$)
  * $B4$: `L_MERGE: y = a + b; return y` (Successor: $EXIT$)
* **Candidate Expression**: $\mathcal{U} = \{a + b\}$

#### LCM Data-Flow Solution:
| Block | ANTIN | ANTOUT | EARLIEST | DELAYIN | LATEST | USEDOUT |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B1** | $\{a+b\}$ | $\{a+b\}$ | $\{a+b\}$ | $\emptyset$ | $\emptyset$ | $\emptyset$ |
| **B2** | $\{a+b\}$ | $\{a+b\}$ | $\emptyset$ | $\{a+b\}$ | $\{a+b\}$ | $\{a+b\}$ |
| **B3** | $\{a+b\}$ | $\{a+b\}$ | $\emptyset$ | $\{a+b\}$ | $\{a+b\}$ | $\{a+b\}$ |
| **B4** | $\{a+b\}$ | $\{a+b\}$ | $\emptyset$ | $\emptyset$ | $\emptyset$ | $\emptyset$ |

#### Transformation:
* $a + b$ is earliest at $B1$, but delayed to $B2$ and $B3$.
* In $B2$: Used locally $\implies \mathbf{LATEST}[B2] = \{a+b\}$.
* In $B3$: Successor $B4$ cannot postpone $\implies \mathbf{LATEST}[B3] = \{a+b\}$.
* $t = a + b$ is inserted into $B2$ and $B3$.
* The redundant evaluation in $B4$ is replaced by $y = t$.

#### Optimized TAC Output:
```
// Block B1
if cond > 0 goto L_THEN

// Block B2
t_a_add_b = a + b
x = t_a_add_b
goto L_MERGE

// Block B3
L_THEN:
t_a_add_b = a + b
c = 10
goto L_MERGE

// Block B4
L_MERGE:
y = t_a_add_b
return y
```
* **Performance Gain**: The path taking $B2 \to B4$ previously computed $a + b$ twice. It now computes it once.

---

### 6.2 Benchmark 2: Common Subexpression Elimination (`02_cse.tac`)
* **Input**: $x * y$ is computed in block $B1$, control flows through branches, and $x * y$ is recomputed in merge block $B4$ without operands being redefined.
* **LCM Behavior**:
  * $\mathbf{EARLIEST}[B1] = \{x * y\}$
  * $\mathbf{LATEST}[B1] = \{x * y\}$
  * In $B4$: $\mathbf{EARLIEST}[B4] = \emptyset, \mathbf{LATEST}[B4] = \emptyset$.
* **Transformation**:
  * $t = x * y$ is computed once in $B1$.
  * The second evaluation in $B4$ is replaced by $t2 = t$.
* **Significance**: Proves that PRE automatically subsumes global CSE.

---

### 6.3 Benchmark 3: Loop-Invariant Code Motion (`03_licm.tac`)
* **Input**:
  ```
  i = 0
  n = 100
  L_LOOP:
  val = base * factor
  i = i + 1
  if i < n goto L_LOOP
  return val
  ```
* **Critical Edge Splitting**: The loop back-edge $B2 \to B2$ is split into $B\_split\_1$.
* **LCM Behavior**:
  * Expression $base * factor$ has invariant operands throughout the loop.
  * $\mathbf{EARLIEST}[B1] = \{base * factor\}$
  * $\mathbf{LATEST}[B1] = \{base * factor\}$
* **Transformation**:
  * Computation $t = base * factor$ is hoisted outside the loop into pre-header $B1$.
  * Inside loop body $B2$, `val = base * factor` becomes `val = t`.
* **Performance Gain**: 100 multiplications inside the loop are reduced to 1 multiplication prior to the loop. Proves that PRE automatically subsumes LICM.

---

### 6.4 Benchmark 4: Critical Edge Splitting (`04_critical_edge.tac`)
* **Input**: A conditional branch jumping directly to a join block where an expression is computed.
* **Framework Behavior**:
  * Detects critical edge $B1 \to B4$.
  * Automatically creates synthetic block $B\_split\_1$.
  * Safely places the hoisted computation inside $B\_split\_1$ without contaminating other paths out of $B1$ or into $B4$.

---

# 7. Verification & Test Suite

The framework includes an automated regression test suite using Python's `unittest` framework (`tests/test_pre.py`).

| Test Name | Tested Component | Expected Behavior | Status |
| :--- | :--- | :--- | :--- |
| `test_bitvector_operations` | `src/dataflow.py` | Verified correctness of $\cap, \cup, -, \sim$ operations. | **PASSED** |
| `test_parser_and_cfg_leaders` | `src/parser.py`, `src/cfg.py` | Accurate leader detection and basic block slicing. | **PASSED** |
| `test_classic_pre_pass` | `src/lcm.py`, `src/transform.py` | Verified insertion in missing branch and deletion at join. | **PASSED** |
| `test_cse_full_redundancy` | `src/lcm.py`, `src/transform.py` | Verified complete subsumption of global CSE. | **PASSED** |
| `test_licm_loop_hoisting` | `src/lcm.py`, `src/transform.py` | Verified loop-invariant hoisting to pre-header. | **PASSED** |

Execution command:
```powershell
python -m unittest discover tests
```
Result: `Ran 5 tests in 0.004s — OK`.

---

# 8. Conclusion & Future Scope

### 8.1 Conclusion
This project successfully implemented an end-to-end Partial Redundancy Elimination Framework based on the textbook Lazy Code Motion algorithm. By unifying Common Subexpression Elimination and Loop-Invariant Code Motion into four clean unidirectional dataflow passes, the system guarantees both computational and lifetime optimality. The project features full critical-edge splitting, automatic temporary allocation, and dual-mode visualization (Graphviz and interactive HTML), making it an exemplary implementation of modern compiler optimization theory.

### 8.2 Future Scope
1. **SSAPRE Integration**: Extending the framework from basic TAC into Static Single Assignment (SSA) form with $\phi$-placement.
2. **Register Pressure Throttling**: Integrating a heuristic to prevent code motion if register pressure exceeds the physical target architecture's register file capacity.
3. **Speculative PRE**: Allowing code insertion on paths where an expression is not anticipated, guarded by frequency-based edge profiling.

---

# 9. References
1. **Aho, A. V., Lam, M. S., Sethi, R., & Ullman, J. D.** (2006). *Compilers: Principles, Techniques, and Tools* (2nd ed., Chapter 9: Machine-Independent Optimizations). Addison-Wesley.
2. **Knoop, J., Rüthing, O., & Steffen, B.** (1994). *Optimal Code Motion: Theory and Practice*. ACM Transactions on Programming Languages and Systems (TOPLAS), 16(4), 1117-1155.
3. **Cooper, K. D., & Torczon, L.** (2011). *Engineering a Compiler* (2nd ed., Chapter 10: Scalar Optimizations). Morgan Kaufmann.
4. **Muchnick, S. S.** (1997). *Advanced Compiler Design and Implementation* (Chapter 13: Partial-Redundancy Elimination). Morgan Kaufmann.
5. **Morel, E., & Renvoise, C.** (1979). *Global Optimization by Suppression of Partial Redundancies*. Communications of the ACM, 22(2), 96-103.
