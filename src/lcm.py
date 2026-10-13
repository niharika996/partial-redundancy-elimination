"""
Lazy Code Motion (LCM) Framework implementation.
Implements the 4-pass data-flow optimization pipeline:
  Pass 1: Anticipated Expressions (Backward, Intersection)
  Pass 2: Available Expressions & Earliest Placement (Forward, Intersection)
  Pass 3: Postponable Expressions & Latest Placement (Forward, Intersection)
  Pass 4: Used Expressions & Redundancy Detection (Backward, Union)
"""

from typing import List, Dict, Set, Tuple
from src.ir import Expression, BinaryAssign
from src.cfg import CFG, BasicBlock
from src.dataflow import BitVector, DataFlowProblem, solve_dataflow


class LocalProperties:
    """Stores e_use, e_kill, e_gen for each basic block."""
    def __init__(self, block: BasicBlock, universe: List[Expression]):
        self.block = block
        self.universe = universe

        # 1. Compute e_use and e_gen
        e_use_set: Set[Expression] = set()
        e_gen_set: Set[Expression] = set()
        defined_vars: Set[str] = set()

        for inst in block.instructions:
            # Check expressions in this instruction
            for expr in inst.get_expressions():
                # Upward exposed if operands haven't been defined earlier in this block
                if not (expr.operands() & defined_vars):
                    e_use_set.add(expr)
                # Tentatively downward exposed
                e_gen_set.add(expr)

            # Record defined variables and invalidate e_gen
            defs = inst.get_defined_vars()
            if defs:
                defined_vars.update(defs)
                # Any expression in e_gen whose operands are now modified is killed
                e_gen_set = {ex for ex in e_gen_set if not (ex.operands() & defs)}

        # 2. Compute e_kill: any expression in universe whose operand is defined in block
        e_kill_set: Set[Expression] = set()
        for expr in universe:
            if expr.operands() & defined_vars:
                e_kill_set.add(expr)

        self.e_use = BitVector.from_set(universe, e_use_set)
        self.e_kill = BitVector.from_set(universe, e_kill_set)
        self.e_gen = BitVector.from_set(universe, e_gen_set)


class LCMFramework:
    """
    Main driver for the Lazy Code Motion optimization algorithm.
    """
    def __init__(self, cfg: CFG):
        self.cfg = cfg
        # Collect all expressions across the entire program
        all_exprs = sorted(list(cfg.get_all_expressions()), key=lambda e: str(e))
        self.universe: List[Expression] = all_exprs

        # Map block -> LocalProperties
        self.locals: Dict[BasicBlock, LocalProperties] = {}
        all_blocks = self.cfg.get_all_blocks()
        for b in all_blocks:
            self.locals[b] = LocalProperties(b, self.universe)

        # Data-flow results
        self.ant_in: Dict[BasicBlock, BitVector] = {}
        self.ant_out: Dict[BasicBlock, BitVector] = {}
        self.ant_history: List[Dict] = []

        self.av_in: Dict[BasicBlock, BitVector] = {}
        self.av_out: Dict[BasicBlock, BitVector] = {}
        self.av_history: List[Dict] = []

        self.earliest: Dict[BasicBlock, BitVector] = {}

        self.delay_in: Dict[BasicBlock, BitVector] = {}
        self.delay_out: Dict[BasicBlock, BitVector] = {}
        self.delay_history: List[Dict] = []

        self.latest: Dict[BasicBlock, BitVector] = {}

        self.used_in: Dict[BasicBlock, BitVector] = {}
        self.used_out: Dict[BasicBlock, BitVector] = {}
        self.used_history: List[Dict] = []

    def run_all_passes(self):
        """Executes all 4 passes of Lazy Code Motion in sequence."""
        self.pass1_anticipability()
        self.pass2_availability_and_earliest()
        self.pass3_postponability_and_latest()
        self.pass4_used_expressions()

    # -------------------------------------------------------------
    # Pass 1: Anticipated Expressions (Upward Exposed / Safety)
    # Direction: Backward
    # Meet: Intersection
    # Transfer: ANTIN[B] = e_use[B] | (ANTOUT[B] - e_kill[B])
    # Boundary: ANTOUT[EXIT] = empty
    # -------------------------------------------------------------
    def pass1_anticipability(self):
        class AnticipatedProblem(DataFlowProblem):
            def __init__(prob_self, universe, locals_dict):
                super().__init__(
                    name="Anticipated",
                    direction="backward",
                    meet_op="intersect",
                    boundary_val=BitVector.all_zeros(universe),
                    init_val=BitVector.all_ones(universe)
                )
                prob_self.locals_dict = locals_dict

            def transfer(prob_self, block: BasicBlock, out_vec: BitVector) -> BitVector:
                lp = prob_self.locals_dict[block]
                return lp.e_use | (out_vec - lp.e_kill)

        problem = AnticipatedProblem(self.universe, self.locals)
        all_blocks = self.cfg.get_all_blocks()
        self.ant_in, self.ant_out, self.ant_history = solve_dataflow(
            all_blocks, problem, self.cfg.entry, self.cfg.exit
        )

    # -------------------------------------------------------------
    # Pass 2: Available Expressions & Earliest Placement
    # Direction: Forward
    # Meet: Intersection
    # Transfer: AVOUT[B] = (AVIN[B] | ANTIN[B]) - e_kill[B]
    # Boundary: AVIN[ENTRY] = empty
    # EARLIEST[B] = ANTIN[B] - AVIN[B]
    # -------------------------------------------------------------
    def pass2_availability_and_earliest(self):
        class AvailableProblem(DataFlowProblem):
            def __init__(prob_self, universe, locals_dict, ant_in_dict):
                super().__init__(
                    name="Available",
                    direction="forward",
                    meet_op="intersect",
                    boundary_val=BitVector.all_zeros(universe),
                    init_val=BitVector.all_ones(universe)
                )
                prob_self.locals_dict = locals_dict
                prob_self.ant_in_dict = ant_in_dict

            def transfer(prob_self, block: BasicBlock, in_vec: BitVector) -> BitVector:
                lp = prob_self.locals_dict[block]
                ant_in_val = prob_self.ant_in_dict[block]
                return (in_vec | ant_in_val) - lp.e_kill

        problem = AvailableProblem(self.universe, self.locals, self.ant_in)
        all_blocks = self.cfg.get_all_blocks()
        self.av_in, self.av_out, self.av_history = solve_dataflow(
            all_blocks, problem, self.cfg.entry, self.cfg.exit
        )

        # Compute EARLIEST[B]
        for b in all_blocks:
            if b == self.cfg.entry:
                self.earliest[b] = BitVector.all_zeros(self.universe)
            else:
                self.earliest[b] = self.ant_in[b] - self.av_in[b]

    # -------------------------------------------------------------
    # Pass 3: Postponable Expressions & Latest Placement
    # Direction: Forward
    # Meet: Intersection
    # Transfer: DELAYOUT[B] = (DELAYIN[B] | EARLIEST[B]) - e_use[B]
    # Boundary: DELAYIN[ENTRY] = empty
    # LATEST[B] = (EARLIEST[B] | DELAYIN[B]) & (e_use[B] | NOT(INTERSECT_{S in succs} (EARLIEST[S] | DELAYIN[S])))
    # -------------------------------------------------------------
    def pass3_postponability_and_latest(self):
        class PostponableProblem(DataFlowProblem):
            def __init__(prob_self, universe, locals_dict, earliest_dict):
                super().__init__(
                    name="Postponable",
                    direction="forward",
                    meet_op="intersect",
                    boundary_val=BitVector.all_zeros(universe),
                    init_val=BitVector.all_ones(universe)
                )
                prob_self.locals_dict = locals_dict
                prob_self.earliest_dict = earliest_dict

            def transfer(prob_self, block: BasicBlock, in_vec: BitVector) -> BitVector:
                lp = prob_self.locals_dict[block]
                earliest_val = prob_self.earliest_dict[block]
                return (in_vec | earliest_val) - lp.e_use

        problem = PostponableProblem(self.universe, self.locals, self.earliest)
        all_blocks = self.cfg.get_all_blocks()
        self.delay_in, self.delay_out, self.delay_history = solve_dataflow(
            all_blocks, problem, self.cfg.entry, self.cfg.exit
        )

        # Compute LATEST[B]
        for b in all_blocks:
            if b in (self.cfg.entry, self.cfg.exit):
                self.latest[b] = BitVector.all_zeros(self.universe)
                continue

            earliest_or_delay = self.earliest[b] | self.delay_in[b]
            lp = self.locals[b]

            # Successor intersection of (EARLIEST[S] | DELAYIN[S])
            if b.succs:
                succ_meet = BitVector.all_ones(self.universe)
                for s in b.succs:
                    if s == self.cfg.exit:
                        # EXIT block cannot postpone anything
                        succ_meet = succ_meet & BitVector.all_zeros(self.universe)
                    else:
                        succ_meet = succ_meet & (self.earliest[s] | self.delay_in[s])
                not_succ_meet = ~succ_meet
            else:
                not_succ_meet = BitVector.all_ones(self.universe)

            self.latest[b] = earliest_or_delay & (lp.e_use | not_succ_meet)

    # -------------------------------------------------------------
    # Pass 4: Used Expressions (Backward, Union)
    # Direction: Backward
    # Meet: Union
    # Transfer: USEDIN[B] = (USEDOUT[B] | e_use[B]) - LATEST[B]
    # Boundary: USEDOUT[EXIT] = empty
    # -------------------------------------------------------------
    def pass4_used_expressions(self):
        class UsedProblem(DataFlowProblem):
            def __init__(prob_self, universe, locals_dict, latest_dict):
                super().__init__(
                    name="Used",
                    direction="backward",
                    meet_op="union",
                    boundary_val=BitVector.all_zeros(universe),
                    init_val=BitVector.all_zeros(universe)
                )
                prob_self.locals_dict = locals_dict
                prob_self.latest_dict = latest_dict

            def transfer(prob_self, block: BasicBlock, out_vec: BitVector) -> BitVector:
                lp = prob_self.locals_dict[block]
                latest_val = prob_self.latest_dict[block]
                return (out_vec | lp.e_use) - latest_val

        problem = UsedProblem(self.universe, self.locals, self.latest)
        all_blocks = self.cfg.get_all_blocks()
        self.used_in, self.used_out, self.used_history = solve_dataflow(
            all_blocks, problem, self.cfg.entry, self.cfg.exit
        )
