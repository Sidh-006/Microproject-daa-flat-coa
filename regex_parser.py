"""
regex_parser.py — Regular expression parser.

Course topic: Formal Languages & Automata Theory
  Converts infix regex to postfix (Reverse Polish Notation) so that
  Thompson's construction can be applied token-by-token.

Supported syntax:
  - Lowercase letters a-z and digits 0-9
  - | (union / alternation)
  - * (Kleene star)
  - ( )  — grouping
  - Implicit concatenation (e.g. "ab" means "a then b")
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Operator precedence (higher = binds tighter)
_PRECEDENCE: dict[str, int] = {"|": 1, "·": 2, "*": 3}

_OPERAND_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789")
_OPERATORS = set("|·*()")


def _is_operand(ch: str) -> bool:
    """Return True if *ch* is a literal character (operand)."""
    return ch in _OPERAND_CHARS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def insert_concat(expr: str) -> str:
    """Insert explicit concatenation operator '·' between adjacent tokens.

    A concatenation is needed between two consecutive tokens when:
      - operand followed by operand   (ab  → a·b)
      - operand followed by '('       (a(  → a·()
      - ')' followed by operand       ()a  → )·a)
      - ')' followed by '('           ()() → )·()
      - '*' followed by operand       (a*b → a*·b)
      - '*' followed by '('           (a*( → a*·()

    Args:
        expr: Raw infix regex string.

    Returns:
        String with '·' inserted at every implicit concatenation point.

    Raises:
        ValueError: If the expression contains unsupported characters.
    """
    result: list[str] = []
    for i, ch in enumerate(expr):
        if ch not in _OPERAND_CHARS and ch not in _OPERATORS:
            raise ValueError(
                f"Unsupported character {ch!r} at position {i}. "
                "Only a-z, 0-9, |, *, (, ) are allowed."
            )
        result.append(ch)
        if i + 1 < len(expr):
            nxt = expr[i + 1]
            # Insert '·' if current token can end a sub-expression ...
            curr_can_end = ch == "*" or ch == ")" or _is_operand(ch)
            # ... and next token can start a sub-expression.
            next_can_start = nxt == "(" or _is_operand(nxt)
            if curr_can_end and next_can_start:
                result.append("·")
    return "".join(result)


def to_postfix(expr: str) -> str:
    """Convert an infix regex to postfix using the shunting-yard algorithm.

    Precondition: *expr* has already had explicit concatenation operators
    inserted (via :func:`insert_concat`).

    Operator precedence: * > · > |
    All operators are left-associative except * which is unary postfix.

    Args:
        expr: Infix regex with explicit '·' concatenation operators.

    Returns:
        Postfix string where each character is a token.

    Raises:
        ValueError: On unbalanced parentheses or dangling operators.
    """
    output: list[str] = []
    op_stack: list[str] = []

    for ch in expr:
        if _is_operand(ch):
            output.append(ch)
        elif ch == "(":
            op_stack.append(ch)
        elif ch == ")":
            # Pop until matching '('
            while op_stack and op_stack[-1] != "(":
                output.append(op_stack.pop())
            if not op_stack:
                raise ValueError(
                    "Unbalanced parentheses: found ')' without matching '('."
                )
            op_stack.pop()  # discard '('
        elif ch in _PRECEDENCE:
            # Pop operators with higher-or-equal precedence (left-assoc)
            while (
                op_stack
                and op_stack[-1] != "("
                and op_stack[-1] in _PRECEDENCE
                and _PRECEDENCE[op_stack[-1]] >= _PRECEDENCE[ch]
            ):
                output.append(op_stack.pop())
            op_stack.append(ch)
        else:
            raise ValueError(f"Unexpected token {ch!r} in expression.")

    # Drain the operator stack
    while op_stack:
        top = op_stack.pop()
        if top == "(":
            raise ValueError(
                "Unbalanced parentheses: found '(' without matching ')'."
            )
        output.append(top)

    postfix = "".join(output)
    _validate_postfix(postfix)
    return postfix


def _validate_postfix(postfix: str) -> None:
    """Validate a postfix expression by simulating a stack machine.

    Raises:
        ValueError: If the postfix expression is malformed (e.g. dangling
            binary operator with only one operand, or empty expression).
    """
    if not postfix:
        raise ValueError("Empty regex is not supported.")
    stack_depth = 0
    for ch in postfix:
        if _is_operand(ch):
            stack_depth += 1
        elif ch == "*":  # unary
            if stack_depth < 1:
                raise ValueError(
                    f"Dangling unary operator '*' in postfix {postfix!r}."
                )
            # stack_depth stays the same (consume 1, produce 1)
        elif ch in ("|", "·"):  # binary
            if stack_depth < 2:
                raise ValueError(
                    f"Dangling binary operator {ch!r} in postfix {postfix!r}."
                )
            stack_depth -= 1  # consume 2, produce 1
    if stack_depth != 1:
        raise ValueError(
            f"Malformed regex: postfix {postfix!r} leaves {stack_depth} items on stack."
        )


def parse(regex: str) -> str:
    """Full pipeline: raw regex string → postfix string.

    Args:
        regex: Raw infix regular expression.

    Returns:
        Postfix representation of the regex.

    Raises:
        ValueError: On any syntax error.
    """
    with_concat = insert_concat(regex)
    return to_postfix(with_concat)
