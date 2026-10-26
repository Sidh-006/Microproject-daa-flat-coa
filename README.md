# regex2cpu

A Python 3.10+ pipeline that takes a regular expression and compiles it all
the way down to machine code running on a simulated CPU — touching three
core Computer Science topics in one project.

```
regex  -->  NFA  -->  DFA  -->  graph analysis  -->  assembly  -->  CPU simulation
```

---

## Quick Start

```bash
# No dependencies beyond Python 3.10+
cd regex2cpu

# Run the acceptance example
python main.py "(a|b)*abb" "babb" --trace --show-asm

# Run all tests
python -m unittest discover tests
```

---

## Pipeline Overview

```
regex_parser.py   Insert explicit concatenation, convert infix -> postfix
      |
      v
nfa.py            Thompson's construction: postfix -> NFA with epsilon transitions
      |
      v
dfa.py            Subset construction + Hopcroft minimization: NFA -> minimal DFA
      |
      v
graph_tools.py    BFS: prune unreachable states, find shortest accepted string
      |
      v
compiler.py       DFA -> assembly source (one block per state)
      |
      v
isa.py            Two-pass assembler: assembly source -> 16-bit machine words
      |
      v
cpu.py            Fetch-Decode-Execute simulator: runs machine code on input string
```

---

## Module-to-Course Mapping

| Module | Course Topic | Key Algorithm / Concept |
|--------|--------------|------------------------|
| `regex_parser.py` | Formal Languages & Automata Theory (FLAT) | Shunting-yard algorithm, operator precedence |
| `nfa.py` | Formal Languages & Automata Theory (FLAT) | Thompson's construction, epsilon-closure |
| `dfa.py` | Formal Languages & Automata Theory (FLAT) | Subset (powerset) construction, Hopcroft minimization |
| `graph_tools.py` | Design & Analysis of Algorithms (DAA) | BFS reachability, shortest-path BFS, O(V+E) |
| `isa.py` | Computer Organization & Architecture (COA) | Instruction encoding/decoding, two-pass assembler |
| `compiler.py` | Computer Organization & Architecture (COA) | Code generation, label resolution |
| `cpu.py` | Computer Organization & Architecture (COA) | Fetch-Decode-Execute cycle, register file, flags |

---

## CLI Usage

```
python main.py "<regex>" "<input_string>" [--trace] [--show-asm] [--dot]
```

| Flag | Description |
|------|-------------|
| `--trace` | Print one line per CPU cycle |
| `--show-asm` | Print the generated assembly and machine words |
| `--dot` | Write `DFA.dot` (Graphviz format, no install needed) |

---

## Example Output

```
python main.py "(a|b)*abb" "babb" --trace --show-asm
```

```
============================================================
1. AUTOMATA SUMMARY
============================================================
   Regex   : (a|b)*abb
   Postfix : ab|*a.b.b.
   NFA states : 14
   DFA states : 4
   Alphabet   : {a, b}

============================================================
2. GRAPH ANALYSIS (BFS)
============================================================
   No unreachable states detected.
   Shortest accepted string : 'abb'

============================================================
3. GENERATED ASSEMBLY
============================================================
   ; --- DFA compiled from 4 states ---
   JMP S0         ; enter DFA at start state
   ; --- State S0  ---
   S0:
       LOAD R1            ; fetch next input char
       CMP  R1, 0         ; end of input?
       JEQ  S0_END        ; if yes -> accept/reject
       CMP  R1, 'a'       ; is input 'a'?
       JEQ  S1            ; yes -> go to S1
       CMP  R1, 'b'       ; is input 'b'?
       JEQ  S0            ; yes -> go to S0
       JMP  REJECT_ALL    ; no transition -> reject
   S0_END:
       REJECT             ; S0 is not accepting
   ...
   S3_END:
       ACCEPT             ; S3 is accepting
   REJECT_ALL:
       REJECT

   Machine code (38 words):
   [000] 0x3001
   ...

============================================================
4. CPU EXECUTION
============================================================
   Input string : 'babb'

cycle=0001 PC=001 IR=0x3001 JMP 1    | R0=0 R1=0  R2=0 R3=0 Z=0
cycle=0002 PC=002 IR=0x0100 LOAD R1  | R0=0 R1=98 R2=0 R3=0 Z=0
...
cycle=0031 PC=037 IR=0x4000 ACCEPT   | R0=0 R1=0  R2=0 R3=0 Z=1

============================================================
5. FINAL RESULT
============================================================
   Result : ACCEPT
   Cycles : 31
============================================================
```

---

## Instruction Set Architecture

16-bit instruction format: `[15:12] opcode | [11:8] register | [7:0] operand`

| Opcode | Mnemonic | Description |
|--------|----------|-------------|
| 0 | `LOAD Rx` | Read next input char (ASCII) into Rx; 0 at EOF |
| 1 | `CMP Rx, imm` | Set Zero flag if Rx == imm |
| 2 | `JEQ addr` | Jump to addr if Zero flag set |
| 3 | `JMP addr` | Unconditional jump |
| 4 | `ACCEPT` | Halt: input accepted |
| 5 | `REJECT` | Halt: input rejected |

---

## Supported Regex Syntax

| Syntax | Meaning |
|--------|---------|
| `a`–`z`, `0`–`9` | Literal character |
| `\|` | Union (alternation) |
| `*` | Kleene star (zero or more) |
| `( )` | Grouping |
| `ab` | Implicit concatenation |

---

## Running Tests

```bash
python -m unittest discover tests -v
```

Expected: **90 tests, 0 failures**

Tests cover:
- `(a|b)*abb` — 13 strings, 4-state DFA check, shortest-string check
- `a*b` — 11 strings
- `(ab)*` — 11 strings
- `a|b|c` — 11 strings
- `ab*c` — 12 strings
- Assembler/disassembler round-trip (6 tests)
- Invalid regex `ValueError` (6 tests)
- NFA and parser unit tests (10 tests)

Each DFA test asserts that `dfa.accepts()` and the **CPU simulator** return identical results.

---

## Design Decisions

- **No explicit dead/trap state**: Missing transitions are treated as immediate
  reject by both `dfa.accepts()` and the CPU (via `JMP REJECT_ALL`). This
  keeps the DFA table minimal.
- **Hopcroft minimization**: Run after subset construction so that equivalent
  NFA states (e.g. the two `b→S0` states in `(a|b)*abb`) are merged into the
  canonical minimal DFA.
- **Partial alphabet in assembly**: Only symbols with actual transitions emit
  `CMP/JEQ` pairs, keeping the generated code tight.
- **Standard library only**: `graphviz` is optional and not required for any
  functionality; `.dot` output is generated as plain text.
