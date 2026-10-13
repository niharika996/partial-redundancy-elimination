"""
Data-Flow Analysis Framework with BitVector and Iterative Solver.
Provides generic fixed-point solvers for forward and backward passes.
"""

from typing import List, Dict, Set, Any, Tuple, Optional
from src.ir import Expression


class BitVector:
    """
    Fixed-size BitVector representing subsets of a universe of elements (e.g. Expressions).
    Provides bitwise set operations with high readability.
    """
    def __init__(self, universe: List[Any], bits: Optional[int] = None):
        self.universe = universe
        self.size = len(universe)
        if bits is None:
            self.value = 0
        else:
            self.value = bits & ((1 << self.size) - 1)

    @classmethod
    def all_ones(cls, universe: List[Any]) -> 'BitVector':
        """Universal set (all bits 1)."""
        val = (1 << len(universe)) - 1
        return cls(universe, val)

    @classmethod
    def all_zeros(cls, universe: List[Any]) -> 'BitVector':
        """Empty set (all bits 0)."""
        return cls(universe, 0)

    @classmethod
    def from_set(cls, universe: List[Any], items: Set[Any]) -> 'BitVector':
        val = 0
        for i, elem in enumerate(universe):
            if elem in items:
                val |= (1 << i)
        return cls(universe, val)

    def to_set(self) -> Set[Any]:
        res = set()
        for i, elem in enumerate(self.universe):
            if (self.value >> i) & 1:
                res.add(elem)
        return res

    def bit_string(self) -> str:
        """Returns bit string representation e.g. [1, 0, 1]."""
        return "".join(str((self.value >> i) & 1) for i in range(self.size))

    def __and__(self, other: 'BitVector') -> 'BitVector':
        return BitVector(self.universe, self.value & other.value)

    def __or__(self, other: 'BitVector') -> 'BitVector':
        return BitVector(self.universe, self.value | other.value)

    def __sub__(self, other: 'BitVector') -> 'BitVector':
        """Set difference: self - other (self AND NOT other)."""
        return BitVector(self.universe, self.value & ~other.value)

    def __invert__(self) -> 'BitVector':
        """Bitwise NOT relative to universe size."""
        mask = (1 << self.size) - 1
        return BitVector(self.universe, (~self.value) & mask)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BitVector):
            return False
        return self.value == other.value and self.universe == other.universe

    def __repr__(self) -> str:
        elements = [str(e) for e in self.to_set()]
        return "{" + ", ".join(sorted(elements)) + "}"


class DataFlowProblem:
    """
    Abstract specification of a Data-Flow Analysis problem.
    """
    def __init__(self, name: str, direction: str, meet_op: str, boundary_val: BitVector, init_val: BitVector):
        assert direction in ("forward", "backward")
        assert meet_op in ("intersect", "union")
        self.name = name
        self.direction = direction
        self.meet_op = meet_op
        self.boundary_val = boundary_val
        self.init_val = init_val

    def transfer(self, block: Any, in_or_out: BitVector) -> BitVector:
        raise NotImplementedError


def solve_dataflow(
    blocks: List[Any],
    problem: DataFlowProblem,
    entry_block: Any,
    exit_block: Any
) -> Tuple[Dict[Any, BitVector], Dict[Any, BitVector], List[Dict[str, Any]]]:
    """
    Iterative worklist / round-robin fixed-point solver.
    Returns: (IN_sets, OUT_sets, iteration_history)
    """
    in_set: Dict[Any, BitVector] = {}
    out_set: Dict[Any, BitVector] = {}
    history: List[Dict[str, Any]] = []

    universe = problem.init_val.universe

    # Initialize sets
    for b in blocks:
        in_set[b] = BitVector(universe, problem.init_val.value)
        out_set[b] = BitVector(universe, problem.init_val.value)

    # Apply boundary condition
    if problem.direction == "forward":
        in_set[entry_block] = BitVector(universe, problem.boundary_val.value)
    else:
        out_set[exit_block] = BitVector(universe, problem.boundary_val.value)

    changed = True
    iteration = 0

    while changed:
        iteration += 1
        changed = False
        step_snapshot = {}

        for b in blocks:
            old_in = BitVector(universe, in_set[b].value)
            old_out = BitVector(universe, out_set[b].value)

            if problem.direction == "forward":
                if b == entry_block:
                    in_set[b] = BitVector(universe, problem.boundary_val.value)
                    out_set[b] = BitVector(universe, problem.boundary_val.value)
                    continue
                elif b.preds:
                    if problem.meet_op == "intersect":
                        res = BitVector.all_ones(universe)
                        for p in b.preds:
                            res = res & out_set[p]
                        in_set[b] = res
                    else:  # union
                        res = BitVector.all_zeros(universe)
                        for p in b.preds:
                            res = res | out_set[p]
                        in_set[b] = res
                else:
                    in_set[b] = BitVector.all_zeros(universe)

                # OUT[B] = Transfer(B, IN[B])
                out_set[b] = problem.transfer(b, in_set[b])

            else:  # backward
                if b == exit_block:
                    out_set[b] = BitVector(universe, problem.boundary_val.value)
                    in_set[b] = BitVector(universe, problem.boundary_val.value)
                    continue
                elif b.succs:
                    if problem.meet_op == "intersect":
                        res = BitVector.all_ones(universe)
                        for s in b.succs:
                            res = res & in_set[s]
                        out_set[b] = res
                    else:  # union
                        res = BitVector.all_zeros(universe)
                        for s in b.succs:
                            res = res | in_set[s]
                        out_set[b] = res
                else:
                    out_set[b] = BitVector.all_zeros(universe)

                # IN[B] = Transfer(B, OUT[B])
                in_set[b] = problem.transfer(b, out_set[b])

            if in_set[b] != old_in or out_set[b] != old_out:
                changed = True

            step_snapshot[b.name] = (repr(in_set[b]), repr(out_set[b]))

        history.append({
            "iteration": iteration,
            "snapshot": step_snapshot
        })

    return in_set, out_set, history
