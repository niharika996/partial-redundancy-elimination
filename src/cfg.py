"""
Control Flow Graph (CFG) Construction and Critical Edge Splitting.
Constructs basic blocks from TAC instructions and maintains predecessors/successors.
"""

from typing import List, Dict, Set, Optional
from src.ir import Instruction, BinaryAssign, CopyAssign, CondJump, Jump, Label, Return, Expression


class BasicBlock:
    """Represents a basic block in the Control Flow Graph."""
    def __init__(self, name: str):
        self.name = name
        self.instructions: List[Instruction] = []
        self.preds: List['BasicBlock'] = []
        self.succs: List['BasicBlock'] = []

    def add_instruction(self, inst: Instruction):
        self.instructions.append(inst)

    def get_labels(self) -> List[str]:
        return [inst.name for inst in self.instructions if isinstance(inst, Label)]

    def get_expressions(self) -> Set[Expression]:
        res = set()
        for inst in self.instructions:
            res.update(inst.get_expressions())
        return res

    def __str__(self) -> str:
        lines = [f"[{self.name}]"]
        for inst in self.instructions:
            lines.append(f"  {inst}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"Block({self.name})"


class CFG:
    """Represents the complete Control Flow Graph."""
    def __init__(self):
        self.entry: BasicBlock = BasicBlock("ENTRY")
        self.exit: BasicBlock = BasicBlock("EXIT")
        self.blocks: List[BasicBlock] = []
        self.split_counter = 0

    def add_block(self, block: BasicBlock):
        if block not in self.blocks:
            self.blocks.append(block)

    def add_edge(self, u: BasicBlock, v: BasicBlock):
        if v not in u.succs:
            u.succs.append(v)
        if u not in v.preds:
            v.preds.append(u)

    def remove_edge(self, u: BasicBlock, v: BasicBlock):
        if v in u.succs:
            u.succs.remove(v)
        if u in v.preds:
            v.preds.remove(u)

    def get_all_blocks(self) -> List[BasicBlock]:
        """Returns all blocks including ENTRY and EXIT."""
        return [self.entry] + self.blocks + [self.exit]

    def get_user_blocks(self) -> List[BasicBlock]:
        """Returns program blocks (excluding ENTRY and EXIT)."""
        return self.blocks

    def get_all_expressions(self) -> Set[Expression]:
        """Collects all unique expressions appearing in the program."""
        exprs = set()
        for b in self.blocks:
            exprs.update(b.get_expressions())
        return exprs

    def split_critical_edges(self) -> List[str]:
        """
        Identifies and splits all critical edges:
        A critical edge is an edge U -> V where out_degree(U) > 1 and in_degree(V) > 1.
        Splitting introduces an empty synthetic block between U and V.
        Returns a list of descriptions of edges that were split.
        """
        critical_edges = []
        # Find critical edges among all blocks (excluding entry/exit edges)
        for u in self.get_all_blocks():
            if len(u.succs) > 1:
                for v in u.succs:
                    if v != self.exit and len(v.preds) > 1:
                        critical_edges.append((u, v))

        split_logs = []
        for u, v in critical_edges:
            self.split_counter += 1
            split_name = f"B_split_{self.split_counter}"
            split_block = BasicBlock(split_name)

            # Insert split block into blocks list right after u
            idx = self.blocks.index(u) if u in self.blocks else len(self.blocks)
            self.blocks.insert(idx + 1, split_block)

            # Rewire edges
            self.remove_edge(u, v)
            self.add_edge(u, split_block)
            self.add_edge(split_block, v)

            # Fix jumps/labels in instructions
            # Find the target label of v
            v_labels = v.get_labels()
            v_label_name = v_labels[0] if v_labels else f"L_{v.name}"
            if not v_labels:
                # Add label to v if it had none
                v.instructions.insert(0, Label(v_label_name))

            split_label_name = f"L_split_{self.split_counter}"
            split_block.instructions.append(Label(split_label_name))
            split_block.instructions.append(Jump(v_label_name))

            # Update u's branch instruction if it jumped to v
            if u.instructions:
                last_inst = u.instructions[-1]
                if isinstance(last_inst, CondJump) and last_inst.target_label in v_labels:
                    last_inst.target_label = split_label_name
                elif isinstance(last_inst, Jump) and last_inst.target_label in v_labels:
                    last_inst.target_label = split_label_name

            split_logs.append(f"Split critical edge: {u.name} -> {v.name} via {split_name}")

        return split_logs


def build_cfg(instructions: List[Instruction]) -> CFG:
    """
    Constructs a CFG from a flat list of TAC instructions.
    Identifies basic block leaders and creates block boundaries.
    """
    if not instructions:
        cfg = CFG()
        cfg.add_edge(cfg.entry, cfg.exit)
        return cfg

    # 1. Identify leader indices
    n = len(instructions)
    leaders = set()
    leaders.add(0)  # First instruction is always a leader

    # Map label names to their instruction index
    label_indices: Dict[str, int] = {}
    for idx, inst in enumerate(instructions):
        if isinstance(inst, Label):
            label_indices[inst.name] = idx

    for idx, inst in enumerate(instructions):
        if isinstance(inst, (CondJump, Jump)):
            # Target of jump is a leader
            if inst.target_label in label_indices:
                leaders.add(label_indices[inst.target_label])
            # Instruction following jump is a leader
            if idx + 1 < n:
                leaders.add(idx + 1)
        elif isinstance(inst, Return):
            if idx + 1 < n:
                leaders.add(idx + 1)
        elif isinstance(inst, Label):
            leaders.add(idx)

    sorted_leaders = sorted(leaders)

    # 2. Slice instructions into basic blocks
    cfg = CFG()
    block_map: Dict[int, BasicBlock] = {}
    label_to_block: Dict[str, BasicBlock] = {}

    for i, start_idx in enumerate(sorted_leaders):
        end_idx = sorted_leaders[i + 1] if i + 1 < len(sorted_leaders) else n
        block_instructions = instructions[start_idx:end_idx]

        b_name = f"B{i + 1}"
        block = BasicBlock(b_name)
        for inst in block_instructions:
            block.add_instruction(inst)
            if isinstance(inst, Label):
                label_to_block[inst.name] = block

        block_map[start_idx] = block
        cfg.add_block(block)

    # 3. Connect ENTRY block
    cfg.add_edge(cfg.entry, cfg.blocks[0])

    # 4. Connect CFG edges based on branch instructions
    for i, start_idx in enumerate(sorted_leaders):
        curr_block = block_map[start_idx]
        next_block = cfg.blocks[i + 1] if i + 1 < len(cfg.blocks) else None

        if not curr_block.instructions:
            if next_block:
                cfg.add_edge(curr_block, next_block)
            else:
                cfg.add_edge(curr_block, cfg.exit)
            continue

        last_inst = curr_block.instructions[-1]

        if isinstance(last_inst, Jump):
            target = label_to_block.get(last_inst.target_label)
            if target:
                cfg.add_edge(curr_block, target)
        elif isinstance(last_inst, CondJump):
            target = label_to_block.get(last_inst.target_label)
            if target:
                cfg.add_edge(curr_block, target)
            if next_block:
                cfg.add_edge(curr_block, next_block)
            else:
                cfg.add_edge(curr_block, cfg.exit)
        elif isinstance(last_inst, Return):
            cfg.add_edge(curr_block, cfg.exit)
        else:
            # Fallthrough
            if next_block:
                cfg.add_edge(curr_block, next_block)
            else:
                cfg.add_edge(curr_block, cfg.exit)

    return cfg
