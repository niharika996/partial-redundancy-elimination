"""
Parser for Three-Address Code (TAC).
Reads TAC text files and produces a list of Instruction objects.
"""

import re
from typing import List
from src.ir import Instruction, BinaryAssign, CopyAssign, CondJump, Jump, Label, Return, Expression

# Regular expressions for matching TAC instructions
LABEL_REGEX = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:$")
GOTO_REGEX = re.compile(r"^goto\s+([A-Za-z_][A-Za-z0-9_]*)$")
IF_GOTO_REGEX = re.compile(
    r"^if\s+([A-Za-z0-9_\-]+)\s*(<=|>=|==|!=|<|>)\s*([A-Za-z0-9_\-]+)\s+goto\s+([A-Za-z_][A-Za-z0-9_]*)$"
)
RETURN_REGEX = re.compile(r"^return(?:\s+([A-Za-z0-9_\-]+))?$")
BINARY_ASSIGN_REGEX = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z0-9_\-]+)\s*([\+\-\*/%&\|\^]|==|!=|<=|>=|<|>)\s*([A-Za-z0-9_\-]+)$"
)
COPY_ASSIGN_REGEX = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z0-9_\-]+)$"
)

def parse_line(line: str) -> Instruction:
    """Parses a single line of TAC into an Instruction object."""
    # Strip comments and extra whitespace
    line = re.sub(r"(#|//).*$", "", line).strip()
    if not line:
        return None

    # 1. Label
    m = LABEL_REGEX.match(line)
    if m:
        return Label(m.group(1))

    # 2. Conditional branch
    m = IF_GOTO_REGEX.match(line)
    if m:
        return CondJump(m.group(1), m.group(2), m.group(3), m.group(4))

    # 3. Unconditional jump
    m = GOTO_REGEX.match(line)
    if m:
        return Jump(m.group(1))

    # 4. Return
    m = RETURN_REGEX.match(line)
    if m:
        return Return(m.group(1))

    # 5. Binary assignment: x = y + z
    m = BINARY_ASSIGN_REGEX.match(line)
    if m:
        target, left, op, right = m.groups()
        expr = Expression(op, left, right)
        return BinaryAssign(target, expr)

    # 6. Copy assignment: x = y or x = 5
    m = COPY_ASSIGN_REGEX.match(line)
    if m:
        target, source = m.groups()
        return CopyAssign(target, source)

    raise ValueError(f"Syntax error in TAC instruction: '{line}'")


def parse_tac(text: str) -> List[Instruction]:
    """Parses full TAC source code into a list of instructions."""
    instructions = []
    for line_num, line in enumerate(text.splitlines(), start=1):
        try:
            inst = parse_line(line)
            if inst is not None:
                instructions.append(inst)
        except ValueError as e:
            raise ValueError(f"Line {line_num}: {e}")
    return instructions


def parse_tac_file(filepath: str) -> List[Instruction]:
    """Reads a .tac file from disk and parses it."""
    with open(filepath, "r", encoding="utf-8") as f:
        return parse_tac(f.read())
