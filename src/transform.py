"""
Code Transformation module for Partial Redundancy Elimination (LCM).
Inserts computations at LATEST placement points and replaces redundant evaluations.
"""

from typing import Dict, List, Set, Tuple
from src.ir import Instruction, BinaryAssign, CopyAssign, Label, Expression
from src.cfg import CFG, BasicBlock
from src.lcm import LCMFramework


class TransformationRecord:
    """Stores information about transformations made to a basic block."""
    def __init__(self, block_name: str):
        self.block_name = block_name
        self.inserted: List[str] = []
        self.replaced: List[Tuple[str, str]] = []  # (original, modified)


class LCMTransformer:
    """
    Applies the final code transformation based on LCM data-flow results.
    """
    def __init__(self, lcm: LCMFramework):
        self.lcm = lcm
        self.cfg = lcm.cfg
        self.temp_map: Dict[Expression, str] = {}
        self.records: Dict[str, TransformationRecord] = {}

    def _allocate_temp(self, expr: Expression) -> str:
        """Assigns a unique, readable temporary variable for an expression."""
        if expr not in self.temp_map:
            # Create a clean variable name e.g. t_a_add_b or t1, t2
            idx = len(self.temp_map) + 1
            op_names = {
                "+": "add", "-": "sub", "*": "mul", "/": "div", "%": "mod",
                "<": "lt", "<=": "le", ">": "gt", ">=": "ge", "==": "eq", "!=": "ne"
            }
            op_str = op_names.get(expr.op, "op")
            var_name = f"t_{expr.left}_{op_str}_{expr.right}"
            # Ensure valid identifier
            var_name = var_name.replace(" ", "").replace("-", "_neg_")
            self.temp_map[expr] = var_name
        return self.temp_map[expr]

    def transform(self) -> Dict[str, TransformationRecord]:
        """
        Executes the code insertion and replacement phases.
        """
        user_blocks = self.cfg.get_user_blocks()

        # Step 1: Identify which expressions actually have redundancy / motion
        # An expression qualifies if it is inserted in some block or used in multiple places
        qualifying_exprs: Set[Expression] = set()

        for b in user_blocks:
            latest_set = self.lcm.latest[b].to_set()
            used_out_set = self.lcm.used_out[b].to_set()
            e_use_set = self.lcm.locals[b].e_use.to_set()

            # Dragon Book condition for insertion:
            # e in LATEST[B] and (e in USEDOUT[B] or e in e_use[B])
            # If e in LATEST[B] and e in USEDOUT[B], it is computing a value needed downstream.
            for expr in (latest_set & (used_out_set | e_use_set)):
                # If e is inserted where it wasn't originally used, or used downstream
                if expr in used_out_set or expr not in e_use_set:
                    qualifying_exprs.add(expr)

        # Also qualify any expression that appears in multiple blocks
        expr_occurrences: Dict[Expression, int] = {}
        for b in user_blocks:
            for expr in b.get_expressions():
                expr_occurrences[expr] = expr_occurrences.get(expr, 0) + 1
        for expr, count in expr_occurrences.items():
            if count > 1:
                qualifying_exprs.add(expr)

        # Allocate temporaries for qualifying expressions
        for expr in qualifying_exprs:
            self._allocate_temp(expr)

        # Step 2: Insert computations at LATEST points
        for b in user_blocks:
            rec = TransformationRecord(b.name)
            self.records[b.name] = rec

            latest_set = self.lcm.latest[b].to_set()
            used_out_set = self.lcm.used_out[b].to_set()
            e_use_set = self.lcm.locals[b].e_use.to_set()

            # Expressions to insert in this block
            insert_exprs = (latest_set & (used_out_set | e_use_set)) & qualifying_exprs

            if insert_exprs:
                # Find insertion point: after any initial Labels
                insert_idx = 0
                while insert_idx < len(b.instructions) and isinstance(b.instructions[insert_idx], Label):
                    insert_idx += 1

                for expr in sorted(list(insert_exprs), key=lambda e: str(e)):
                    temp_var = self.temp_map[expr]
                    new_inst = BinaryAssign(temp_var, expr)
                    b.instructions.insert(insert_idx, new_inst)
                    rec.inserted.append(str(new_inst))
                    insert_idx += 1

        # Step 3: Replace original evaluations with temporaries
        for b in user_blocks:
            rec = self.records[b.name]
            for inst in b.instructions:
                if isinstance(inst, BinaryAssign):
                    expr = inst.expr
                    # If this expression has a temp allocated and is in USEDOUT or evaluated downstream/inserted
                    if expr in self.temp_map:
                        # Avoid replacing the instruction we just inserted (temp = expr)
                        if inst.target != self.temp_map[expr]:
                            old_str = str(inst)
                            temp_var = self.temp_map[expr]
                            inst.replace_expression(expr, temp_var)
                            rec.replaced.append((old_str, str(inst)))

        return self.records
