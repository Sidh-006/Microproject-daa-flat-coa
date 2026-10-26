"""
isa.py — Instruction Set Architecture definition for the tiny 16-bit CPU.

Course topic: Computer Organization & Architecture
  Defines a minimal ISA with six opcodes. Each instruction is a 16-bit word:

    [15:12] opcode  (4 bits)
    [11: 8] register (4 bits, usually Rx index)
    [ 7: 0] operand  (8 bits, immediate / address)

Opcodes:
  0  LOAD  Rx      — read next input char into Rx (ASCII), 0 at end-of-input
  1  CMP   Rx, imm — compare Rx with immediate; set Zero flag if equal
  2  JEQ   addr    — jump to addr if Zero flag is set
  3  JMP   addr    — unconditional jump to addr
  4  ACCEPT        — halt: input accepted
  5  REJECT        — halt: input rejected

The assembler is two-pass:
  Pass 1: collect label→address mapping.
  Pass 2: encode instructions, resolving label references.

The disassembler decodes 16-bit words back to human-readable mnemonics.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Opcode table
# ---------------------------------------------------------------------------

OPCODES: dict[str, int] = {
    "LOAD":   0,
    "CMP":    1,
    "JEQ":    2,
    "JMP":    3,
    "ACCEPT": 4,
    "REJECT": 5,
}

# Reverse lookup: int → mnemonic
_MNEMONIC: dict[int, str] = {v: k for k, v in OPCODES.items()}

# Register names → index
_REGS: dict[str, int] = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
_REG_NAMES: dict[int, str] = {v: k for k, v in _REGS.items()}


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------


def _encode(opcode: int, reg: int, operand: int) -> int:
    """Pack opcode, register index, and operand into a 16-bit word.

    Bit layout: [15:12]=opcode | [11:8]=reg | [7:0]=operand.

    Args:
        opcode: 4-bit opcode (0-15).
        reg: 4-bit register index (0-15).
        operand: 8-bit immediate or address (0-255).

    Returns:
        16-bit encoded instruction word.
    """
    return ((opcode & 0xF) << 12) | ((reg & 0xF) << 8) | (operand & 0xFF)


def _decode(word: int) -> tuple[int, int, int]:
    """Unpack a 16-bit word into (opcode, reg, operand).

    Args:
        word: 16-bit instruction word.

    Returns:
        Tuple of (opcode, register_index, operand).
    """
    opcode  = (word >> 12) & 0xF
    reg     = (word >>  8) & 0xF
    operand = word & 0xFF
    return opcode, reg, operand


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------


def assemble(lines: list[str]) -> list[int]:
    """Assemble a list of assembly text lines into 16-bit machine words.

    Supports:
      - Labels ending in ':' (on their own line or prefixed before an instruction).
      - Blank lines and comment-only lines (';' starts a comment).
      - Character literals like 'a' as immediates (converted to ASCII).

    Args:
        lines: Assembly source lines.

    Returns:
        List of 16-bit instruction words.

    Raises:
        ValueError: On unknown mnemonics, registers, or unresolved labels.
    """
    # Strip comments and blanks; split labels from instructions
    cleaned: list[tuple[str | None, str | None]] = []  # (label, instruction)
    for raw_line in lines:
        line = raw_line.split(";")[0].strip()  # remove comment
        if not line:
            continue
        # A line may be "LABEL: INSTRUCTION" or just "LABEL:" or just "INSTRUCTION"
        label: str | None = None
        instr: str | None = None
        if ":" in line:
            parts = line.split(":", 1)
            label = parts[0].strip()
            rest = parts[1].strip()
            if rest:
                instr = rest
        else:
            instr = line
        cleaned.append((label, instr))

    # --- Pass 1: assign addresses to labels ---
    labels: dict[str, int] = {}
    addr = 0
    for label, instr in cleaned:
        if label is not None:
            labels[label] = addr
        if instr is not None:
            addr += 1  # each instruction occupies exactly one word

    # --- Pass 2: encode instructions ---
    words: list[int] = []
    for label, instr in cleaned:
        if instr is None:
            continue
        tokens = instr.split()
        mnemonic = tokens[0].upper()
        if mnemonic not in OPCODES:
            raise ValueError(f"Unknown mnemonic {mnemonic!r}.")

        opcode = OPCODES[mnemonic]

        if mnemonic in ("ACCEPT", "REJECT"):
            words.append(_encode(opcode, 0, 0))

        elif mnemonic == "LOAD":
            # LOAD Rx
            reg = _parse_reg(tokens[1])
            words.append(_encode(opcode, reg, 0))

        elif mnemonic == "CMP":
            # CMP Rx, imm   (imm may be a number or 'c' char literal or 0)
            reg_tok, imm_tok = tokens[1].rstrip(","), tokens[2]
            reg = _parse_reg(reg_tok)
            imm = _parse_imm(imm_tok, labels)
            words.append(_encode(opcode, reg, imm))

        elif mnemonic in ("JEQ", "JMP"):
            # JEQ addr / JMP addr
            target = _resolve(tokens[1], labels)
            words.append(_encode(opcode, 0, target))

        else:
            raise ValueError(f"Unhandled mnemonic {mnemonic!r}.")

    return words


def _parse_reg(token: str) -> int:
    """Parse a register token like 'R1' into its index."""
    tok = token.strip().upper()
    if tok not in _REGS:
        raise ValueError(f"Unknown register {token!r}. Expected R0-R3.")
    return _REGS[tok]


def _parse_imm(token: str, labels: dict[str, int]) -> int:
    """Parse an immediate value: integer literal, char literal 'x', or label."""
    tok = token.strip()
    # Character literal e.g. 'a'
    if len(tok) == 3 and tok[0] == "'" and tok[2] == "'":
        return ord(tok[1])
    # Decimal integer
    try:
        return int(tok)
    except ValueError:
        pass
    # Label reference
    return _resolve(tok, labels)


def _resolve(token: str, labels: dict[str, int]) -> int:
    """Resolve a label or integer to an address."""
    tok = token.strip()
    if tok in labels:
        return labels[tok]
    try:
        return int(tok)
    except ValueError:
        raise ValueError(f"Unresolved label {tok!r}.")


# ---------------------------------------------------------------------------
# Disassembler
# ---------------------------------------------------------------------------


def disassemble(words: list[int]) -> list[str]:
    """Decode a list of 16-bit words into human-readable assembly lines.

    Args:
        words: Machine code words to disassemble.

    Returns:
        List of mnemonic strings, one per word.
    """
    result: list[str] = []
    for word in words:
        opcode, reg, operand = _decode(word)
        mnemonic = _MNEMONIC.get(opcode, f"???({opcode})")

        if mnemonic in ("ACCEPT", "REJECT"):
            result.append(mnemonic)
        elif mnemonic == "LOAD":
            result.append(f"LOAD {_REG_NAMES.get(reg, f'R{reg}')}")
        elif mnemonic == "CMP":
            reg_name = _REG_NAMES.get(reg, f"R{reg}")
            # Show printable ASCII as character literal, else as decimal
            if 32 <= operand < 127:
                imm_str = f"'{chr(operand)}'"
            else:
                imm_str = str(operand)
            result.append(f"CMP {reg_name}, {imm_str}")
        elif mnemonic in ("JEQ", "JMP"):
            result.append(f"{mnemonic} {operand}")
        else:
            result.append(f"{mnemonic} R{reg}, {operand}")

    return result
