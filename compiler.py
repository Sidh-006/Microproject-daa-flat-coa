"""
compiler.py — Compile a DFA to assembly and machine code.

Course topic: Computer Organization & Architecture
  Translates the DFA transition table into a linear sequence of instructions
  for the tiny 16-bit ISA defined in isa.py.

Code generation strategy (per DFA state Sx):
    Sx:
        LOAD R1               ; fetch next input character
        CMP  R1, 0            ; 0 = end-of-input sentinel
        JEQ  Sx_END           ; if end-of-input, check if accepting
        CMP  R1, 'a'          ; for each symbol in the alphabet...
        JEQ  <target>         ;   jump to target state if matched
        ...
        JMP  REJECT_ALL       ; no transition matched -> reject
    Sx_END:
        ACCEPT / REJECT       ; depending on whether Sx is accepting

A shared REJECT_ALL label holds a single REJECT instruction.
"""

from __future__ import annotations

from dfa import DFA
from isa import assemble


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compile_dfa(dfa: DFA) -> tuple[list[str], list[int]]:
    """Compile *dfa* to assembly source and machine code.

    Args:
        dfa: The DFA to compile (must have states in sorted order, start=S0).

    Returns:
        A tuple (asm_lines, machine_words) where:
          - asm_lines is the list of assembly source lines (with comments).
          - machine_words is the list of 16-bit encoded instruction words.
    """
    asm: list[str] = []
    sorted_alphabet = sorted(dfa.alphabet)

    # ------------------------------------------------------------------
    # Entry point: jump to the start state
    # ------------------------------------------------------------------
    asm.append(f"; --- DFA compiled from {len(dfa.states)} states ---")
    asm.append(f"JMP {dfa.start}         ; enter DFA at start state")

    # ------------------------------------------------------------------
    # One block per DFA state
    # ------------------------------------------------------------------
    for state in dfa.states:
        asm.append(f"; --- State {state} {'(accepting)' if state in dfa.accepting else ''} ---")
        asm.append(f"{state}:")
        asm.append(f"    LOAD R1            ; fetch next input char")
        asm.append(f"    CMP  R1, 0         ; end of input?")
        asm.append(f"    JEQ  {state}_END   ; if yes -> accept/reject")

        # Emit one CMP+JEQ pair per symbol that has a transition
        for symbol in sorted_alphabet:
            target = dfa.transitions.get(state, {}).get(symbol)
            if target is not None:
                asm.append(f"    CMP  R1, '{symbol}'  ; is input '{symbol}'?")
                asm.append(f"    JEQ  {target}        ; yes -> go to {target}")

        asm.append(f"    JMP  REJECT_ALL    ; no transition -> reject")

        # End-of-input landing pad
        asm.append(f"{state}_END:")
        if state in dfa.accepting:
            asm.append(f"    ACCEPT             ; {state} is accepting")
        else:
            asm.append(f"    REJECT             ; {state} is not accepting")

    # ------------------------------------------------------------------
    # Shared reject handler
    # ------------------------------------------------------------------
    asm.append("; --- Shared reject handler ---")
    asm.append("REJECT_ALL:")
    asm.append("    REJECT")

    # ------------------------------------------------------------------
    # Assemble to machine code
    # ------------------------------------------------------------------
    machine_words = assemble(asm)
    return asm, machine_words
