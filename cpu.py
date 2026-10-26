"""
cpu.py — Simulated CPU with fetch-decode-execute cycle.

Course topic: Computer Organization & Architecture
  Implements a simple Von Neumann-style CPU:
    - Registers: PC (program counter), IR (instruction register),
                 R0-R3 (general purpose), Zero flag, input pointer.
    - Memory: flat list of 16-bit instruction words (Harvard-style: no
              separate data memory — input is accessed via LOAD).
    - Cycle: FETCH → DECODE → EXECUTE

Instruction execution:
  LOAD Rx      — copy input[ip] (or 0 at EOF) into Rx; advance ip
  CMP  Rx, imm — set Zero flag iff Rx == imm
  JEQ  addr    — if Zero: PC = addr
  JMP  addr    — PC = addr (unconditional)
  ACCEPT       — halt with "ACCEPT"
  REJECT       — halt with "REJECT"
"""

from __future__ import annotations

from isa import OPCODES, _decode, _REG_NAMES


# Opcode constants for fast comparison
_OP_LOAD   = OPCODES["LOAD"]
_OP_CMP    = OPCODES["CMP"]
_OP_JEQ    = OPCODES["JEQ"]
_OP_JMP    = OPCODES["JMP"]
_OP_ACCEPT = OPCODES["ACCEPT"]
_OP_REJECT = OPCODES["REJECT"]

# Safety limit: prevent infinite loops in malformed programs
_MAX_CYCLES = 100_000


class CPU:
    """Simulated 16-bit CPU.

    Attributes:
        memory: Loaded program as a list of 16-bit words.
        regs: General-purpose registers R0-R3.
        pc: Program counter.
        ir: Instruction register (current instruction word).
        zero: Zero flag (bool).
        ip: Input pointer into the input string.
        input_data: Current input string (as ASCII ordinals).
        cycles: Number of cycles executed so far.
        trace: If True, print one line per cycle to stdout.
    """

    def __init__(self) -> None:
        """Initialise CPU with zeroed state."""
        self.memory: list[int] = []
        self.regs: list[int] = [0, 0, 0, 0]   # R0-R3
        self.pc: int = 0
        self.ir: int = 0
        self.zero: bool = False
        self.ip: int = 0
        self.input_data: list[int] = []
        self.cycles: int = 0
        self.trace: bool = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self, program: list[int]) -> None:
        """Load a machine-code program into memory.

        Args:
            program: List of 16-bit instruction words.
        """
        self.memory = list(program)

    def run(self, input_str: str, trace: bool = False) -> tuple[str, int]:
        """Run the loaded program on *input_str*.

        Args:
            input_str: The string to test (fed character by character via LOAD).
            trace: If True, print a trace line for each cycle.

        Returns:
            Tuple of (result, cycle_count) where result is "ACCEPT" or "REJECT".

        Raises:
            RuntimeError: If the CPU exceeds the maximum cycle limit or
                          encounters an invalid instruction.
        """
        # --- Reset state ---
        self.regs = [0, 0, 0, 0]
        self.pc = 0
        self.ir = 0
        self.zero = False
        self.ip = 0
        self.cycles = 0
        self.trace = trace
        # Append a NUL sentinel so LOAD always has something to read
        self.input_data = [ord(ch) for ch in input_str] + [0]

        while self.cycles < _MAX_CYCLES:
            # ---- FETCH ----
            if self.pc >= len(self.memory):
                raise RuntimeError(
                    f"PC={self.pc} is out of memory bounds "
                    f"(program has {len(self.memory)} words)."
                )
            self.ir = self.memory[self.pc]
            self.pc += 1

            # ---- DECODE ----
            opcode, reg, operand = _decode(self.ir)

            # ---- EXECUTE ----
            result = self._execute(opcode, reg, operand)
            self.cycles += 1

            if result is not None:
                if self.trace:
                    print(
                        f"cycle={self.cycles:04d} PC={self.pc:03d} "
                        f"IR=0x{self.ir:04X} {result} | "
                        f"{self._regs_str()} Z={int(self.zero)}"
                    )
                return result, self.cycles

            if self.trace:
                opcode2, reg2, operand2 = _decode(self.ir)
                mnemonic = self._mnemonic_str(opcode2, reg2, operand2)
                print(
                    f"cycle={self.cycles:04d} PC={self.pc:03d} "
                    f"IR=0x{self.ir:04X} {mnemonic} | "
                    f"{self._regs_str()} Z={int(self.zero)}"
                )

        raise RuntimeError(
            f"CPU exceeded maximum cycle limit ({_MAX_CYCLES}). "
            "Possible infinite loop in the compiled DFA."
        )

    # ------------------------------------------------------------------
    # Execute one instruction; return "ACCEPT"/"REJECT" on halt, else None
    # ------------------------------------------------------------------

    def _execute(self, opcode: int, reg: int, operand: int) -> str | None:
        """Execute a single decoded instruction.

        Args:
            opcode: 4-bit opcode.
            reg: 4-bit register index.
            operand: 8-bit immediate / address.

        Returns:
            "ACCEPT" or "REJECT" on halting instructions, None otherwise.
        """
        if opcode == _OP_LOAD:
            # Read next input byte (ASCII), or 0 at end-of-input
            value = self.input_data[self.ip] if self.ip < len(self.input_data) else 0
            self.regs[reg] = value
            self.ip += 1

        elif opcode == _OP_CMP:
            # Set Zero flag iff register equals immediate
            self.zero = (self.regs[reg] == operand)

        elif opcode == _OP_JEQ:
            # Conditional jump: branch only if Zero flag is set
            if self.zero:
                self.pc = operand

        elif opcode == _OP_JMP:
            # Unconditional jump
            self.pc = operand

        elif opcode == _OP_ACCEPT:
            return "ACCEPT"

        elif opcode == _OP_REJECT:
            return "REJECT"

        else:
            raise RuntimeError(f"Unknown opcode {opcode} in instruction 0x{self.ir:04X}.")

        return None

    # ------------------------------------------------------------------
    # Helpers for trace output
    # ------------------------------------------------------------------

    def _regs_str(self) -> str:
        """Return a compact register dump string."""
        return " ".join(f"R{i}={self.regs[i]}" for i in range(4))

    def _mnemonic_str(self, opcode: int, reg: int, operand: int) -> str:
        """Return a human-readable mnemonic for a decoded instruction."""
        names = {
            _OP_LOAD:   lambda r, o: f"LOAD {_REG_NAMES.get(r, f'R{r}')}",
            _OP_CMP:    lambda r, o: (
                f"CMP {_REG_NAMES.get(r, f'R{r}')},'{chr(o)}'" if 32 <= o < 127
                else f"CMP {_REG_NAMES.get(r, f'R{r}')},{o}"
            ),
            _OP_JEQ:    lambda r, o: f"JEQ {o}",
            _OP_JMP:    lambda r, o: f"JMP {o}",
            _OP_ACCEPT: lambda r, o: "ACCEPT",
            _OP_REJECT: lambda r, o: "REJECT",
        }
        fn = names.get(opcode)
        return fn(reg, operand) if fn else f"???(0x{opcode:X})"
