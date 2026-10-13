"""
Intermediate Representation (IR) for Three-Address Code (TAC).
Supports expressions, assignments, branches, jumps, and labels.
"""

from typing import Optional, Set, Tuple

COMMUTATIVE_OPS = {"+", "*", "==", "!=", "&", "|", "^"}

class Expression:
    """Represents a binary expression: left op right (e.g., a + b)."""
    def __init__(self, op: str, left: str, right: str):
        self.op = op
        # Canonicalize commutative operators for consistent subexpression matching
        if op in COMMUTATIVE_OPS and str(left) > str(right):
            self.left = str(right)
            self.right = str(left)
        else:
            self.left = str(left)
            self.right = str(right)

    def operands(self) -> Set[str]:
        res = set()
        if not self.left.lstrip("-").isdigit():
            res.add(self.left)
        if not self.right.lstrip("-").isdigit():
            res.add(self.right)
        return res

    def __str__(self) -> str:
        return f"{self.left} {self.op} {self.right}"

    def __repr__(self) -> str:
        return f"Expr({self})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Expression):
            return False
        return self.op == other.op and self.left == other.left and self.right == other.right

    def __hash__(self) -> int:
        return hash((self.op, self.left, self.right))


class Instruction:
    """Base class for TAC instructions."""
    def get_defined_vars(self) -> Set[str]:
        return set()

    def get_used_vars(self) -> Set[str]:
        return set()

    def get_expressions(self) -> Set[Expression]:
        return set()

    def replace_expression(self, expr: Expression, temp_var: str) -> bool:
        """Replace occurrence of expr with temp_var. Returns True if replaced."""
        return False


class BinaryAssign(Instruction):
    """Instruction of the form: target = left op right"""
    def __init__(self, target: str, expr: Expression):
        self.target = target
        self.expr = expr

    def get_defined_vars(self) -> Set[str]:
        return {self.target}

    def get_used_vars(self) -> Set[str]:
        return self.expr.operands()

    def get_expressions(self) -> Set[Expression]:
        return {self.expr}

    def replace_expression(self, expr: Expression, temp_var: str) -> bool:
        if self.expr == expr:
            # Change this instruction to a CopyAssign: target = temp_var
            self.__class__ = CopyAssign
            self.source = temp_var
            del self.expr
            return True
        return False

    def __str__(self) -> str:
        return f"{self.target} = {self.expr}"

    def __repr__(self) -> str:
        return f"BinaryAssign({self})"


class CopyAssign(Instruction):
    """Instruction of the form: target = source (source is variable or constant)."""
    def __init__(self, target: str, source: str):
        self.target = target
        self.source = str(source)

    def get_defined_vars(self) -> Set[str]:
        return {self.target}

    def get_used_vars(self) -> Set[str]:
        if not self.source.lstrip("-").isdigit():
            return {self.source}
        return set()

    def __str__(self) -> str:
        return f"{self.target} = {self.source}"

    def __repr__(self) -> str:
        return f"CopyAssign({self})"


class CondJump(Instruction):
    """Instruction of the form: if left relop right goto target_label"""
    def __init__(self, left: str, relop: str, right: str, target_label: str):
        self.left = str(left)
        self.relop = relop
        self.right = str(right)
        self.target_label = target_label

    def get_used_vars(self) -> Set[str]:
        res = set()
        if not self.left.lstrip("-").isdigit():
            res.add(self.left)
        if not self.right.lstrip("-").isdigit():
            res.add(self.right)
        return res

    def __str__(self) -> str:
        return f"if {self.left} {self.relop} {self.right} goto {self.target_label}"

    def __repr__(self) -> str:
        return f"CondJump({self})"


class Jump(Instruction):
    """Unconditional jump: goto target_label"""
    def __init__(self, target_label: str):
        self.target_label = target_label

    def __str__(self) -> str:
        return f"goto {self.target_label}"

    def __repr__(self) -> str:
        return f"Jump({self})"


class Label(Instruction):
    """A label definition: label_name:"""
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return f"{self.name}:"

    def __repr__(self) -> str:
        return f"Label({self})"


class Return(Instruction):
    """Return instruction: return [value]"""
    def __init__(self, value: Optional[str] = None):
        self.value = str(value) if value is not None else None

    def get_used_vars(self) -> Set[str]:
        if self.value and not self.value.lstrip("-").isdigit():
            return {self.value}
        return set()

    def __str__(self) -> str:
        if self.value:
            return f"return {self.value}"
        return "return"

    def __repr__(self) -> str:
        return f"Return({self})"
