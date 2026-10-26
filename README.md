<div align="center">

# ⚡ regex2cpu

### *A complete pipeline from Regular Expression → CPU Simulation*

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-regex2cpu.onrender.com-7c3aed?style=for-the-badge)](https://regex2cpu.onrender.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-90_passed-10b981?style=for-the-badge)](#running-tests)

**regex2cpu** is an interactive micro-project that takes a regular expression and runs it through a complete theoretical computer science pipeline — converting it to an NFA, then a DFA, analyzing it with graph algorithms, compiling it to a custom 16-bit assembly language, and finally simulating it on a virtual CPU.

```
Regex  ──►  NFA  ──►  DFA  ──►  BFS Analysis  ──►  Assembly  ──►  CPU Simulation
 FLAT         FLAT      FLAT          DAA               COA               COA
```

</div>

---

## 🌐 Live Demo

> **Try it now — no installation needed!**
>
> ### 👉 [https://regex2cpu.onrender.com/](https://regex2cpu.onrender.com/)

---

## 🎯 What It Does

Enter any regular expression (using lowercase letters/digits) and a test string. The pipeline will:

1. **Parse** the regex into postfix notation (Shunting-yard algorithm)
2. **Build an NFA** using Thompson's construction with epsilon transitions
3. **Convert to a minimal DFA** via subset construction + Hopcroft minimization
4. **Analyze the DFA** as a directed graph using BFS to find unreachable states and the shortest accepted string
5. **Compile the DFA** into 16-bit assembly for a custom ISA
6. **Simulate the CPU** with a fetch-decode-execute cycle and tell you if the input is **ACCEPT** or **REJECT**

---

## 🖥️ How to Use the Web App

### Step 1 — Open the Live App
Go to **[https://regex2cpu.onrender.com/](https://regex2cpu.onrender.com/)**

### Step 2 — Enter a Regular Expression
Type your regex in the **"Regular Expression"** box.

**Supported syntax:**

| Syntax | Meaning | Example |
|--------|---------|---------|
| `a`–`z`, `0`–`9` | Literal character | `a`, `b`, `3` |
| `\|` | Union — match either side | `a\|b` matches `a` or `b` |
| `*` | Kleene star — zero or more | `a*` matches `""`, `a`, `aa`, ... |
| `( )` | Grouping | `(ab)*` matches `""`, `ab`, `abab`, ... |
| Adjacency | Implicit concatenation | `ab` means `a` then `b` |

> ⚠️ **Not supported:** uppercase letters, `.` (dot), `+`, `?`, `^`, `$`

### Step 3 — Enter a Test String
Type the string you want to test against your regex in the **"Input String"** box.

### Step 4 — Toggle Options

| Toggle | What it shows |
|--------|--------------|
| 📋 **Show Assembly** | The generated 16-bit assembly listing + machine code hex words |
| 🔄 **CPU Trace** | Every fetch-decode-execute cycle the CPU runs, step by step |
| 🕸️ **DFA Graph (.dot)** | Graphviz source you can paste into [GraphvizOnline](https://dreampuf.github.io/GraphvizOnline/) to visualize the DFA |

### Step 5 — Click ▶ Run Pipeline
Results appear instantly in the right panel, organized into collapsible sections:
- 🏁 **Final Result** — ACCEPT ✅ or REJECT ❌ with cycle count
- 🤖 **Automata Summary** — NFA states, DFA states, alphabet
- 🕸️ **Graph Analysis (BFS)** — unreachable states removed, shortest accepted string
- 📋 **Generated Assembly** — syntax-highlighted ISA listing (if enabled)
- 🔄 **CPU Execution Trace** — per-cycle register dump (if enabled)
- 🕸️ **DFA Graph (.dot)** — copyable Graphviz source (if enabled)

### ⌨️ Keyboard Shortcut
Press **`Ctrl + Enter`** to run the pipeline without clicking the button.

---

## 🚀 Quick Examples

Click any chip in the **Quick Examples** section of the web app, or try these manually:

| Regex | Test String | Expected |
|-------|------------|----------|
| `(a\|b)*abb` | `babb` | ✅ ACCEPT |
| `(a\|b)*abb` | `ab` | ❌ REJECT |
| `a*b` | `aaab` | ✅ ACCEPT |
| `a*b` | `aa` | ❌ REJECT |
| `(ab)*` | `abab` | ✅ ACCEPT |
| `a\|b\|c` | `c` | ✅ ACCEPT |
| `ab*c` | `abbbc` | ✅ ACCEPT |

---

## 🏗️ Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          regex2cpu Pipeline                         │
├──────────────────┬──────────────────────────────────────────────────┤
│  regex_parser.py │  Inserts explicit concatenation operator '·'     │
│  FLAT            │  Converts infix regex → postfix (Shunting-yard)  │
├──────────────────┼──────────────────────────────────────────────────┤
│  nfa.py          │  Thompson's construction: postfix → NFA          │
│  FLAT            │  Supports literals, union |, concat ·, star *    │
│                  │  Provides epsilon_closure() and move()           │
├──────────────────┼──────────────────────────────────────────────────┤
│  dfa.py          │  Subset (powerset) construction: NFA → DFA       │
│  FLAT            │  Hopcroft minimization merges equivalent states  │
│                  │  dfa.accepts(string) for pure-Python simulation  │
├──────────────────┼──────────────────────────────────────────────────┤
│  graph_tools.py  │  BFS reachability: prune unreachable states      │
│  DAA             │  BFS shortest path: find shortest accepted str   │
│                  │  Time complexity: O(V + E)                       │
├──────────────────┼──────────────────────────────────────────────────┤
│  compiler.py     │  DFA transition table → assembly source          │
│  COA             │  One code block per DFA state                    │
├──────────────────┼──────────────────────────────────────────────────┤
│  isa.py          │  16-bit ISA definition, two-pass assembler       │
│  COA             │  Assembler + disassembler with label resolution  │
├──────────────────┼──────────────────────────────────────────────────┤
│  cpu.py          │  Fetch → Decode → Execute simulator              │
│  COA             │  Registers R0-R3, PC, IR, Zero flag              │
└──────────────────┴──────────────────────────────────────────────────┘
```

---

## 📚 Module → Course Topic Mapping

| Module | Course | Key Concept |
|--------|--------|-------------|
| `regex_parser.py` | **FLAT** — Formal Languages & Automata Theory | Shunting-yard algorithm, operator precedence |
| `nfa.py` | **FLAT** — Formal Languages & Automata Theory | Thompson's construction, ε-closure, move() |
| `dfa.py` | **FLAT** — Formal Languages & Automata Theory | Subset construction, Hopcroft minimization |
| `graph_tools.py` | **DAA** — Design & Analysis of Algorithms | BFS on directed graphs, O(V+E) traversal |
| `isa.py` | **COA** — Computer Organization & Architecture | 16-bit ISA encoding, two-pass assembler |
| `compiler.py` | **COA** — Computer Organization & Architecture | Code generation, label resolution |
| `cpu.py` | **COA** — Computer Organization & Architecture | Fetch-Decode-Execute cycle, register file |

---

## 🔧 Instruction Set Architecture (16-bit)

Instruction format: `[15:12] opcode | [11:8] register | [7:0] operand`

| Opcode | Mnemonic | Description |
|--------|----------|-------------|
| `0` | `LOAD Rx` | Read next input character (ASCII) into register Rx; loads 0 at end-of-input |
| `1` | `CMP Rx, imm` | Compare Rx with immediate value; sets Zero flag if equal |
| `2` | `JEQ addr` | Jump to address if Zero flag is set |
| `3` | `JMP addr` | Unconditional jump to address |
| `4` | `ACCEPT` | Halt — input string is **accepted** |
| `5` | `REJECT` | Halt — input string is **rejected** |

---

## 💻 Run Locally (CLI)

### Prerequisites
- Python 3.10 or higher
- No external dependencies (standard library only)

### Install & Run

```bash
# Clone the repository
git clone https://github.com/Sidh-006/Microproject-daa-flat-coa.git
cd Microproject-daa-flat-coa

# Run the acceptance example
python main.py "(a|b)*abb" "babb" --trace --show-asm
```

### CLI Flags

```
python main.py "<regex>" "<input_string>" [--trace] [--show-asm] [--dot]
```

| Flag | Description |
|------|-------------|
| `--trace` | Print one line per CPU cycle (fetch-decode-execute trace) |
| `--show-asm` | Print generated assembly source + hex machine words |
| `--dot` | Write `DFA.dot` Graphviz file (no graphviz install needed) |

### Run the Web Server Locally

```bash
pip install flask gunicorn
python app.py
# Open http://localhost:5000
```

---

## 🧪 Running Tests

```bash
python -m unittest discover tests -v
```

**Expected output: 90 tests, 0 failures**

Test coverage includes:
- **5 regex patterns** × 10+ strings each — `dfa.accepts()` and CPU simulator must agree on every string
- `(a|b)*abb` — exactly 4-state minimal DFA, shortest accepted string = `"abb"`
- **Assembler/disassembler round-trip** — encode then decode must return original
- **Invalid regex** — unbalanced parens, dangling operators raise `ValueError`

---

## 📁 Project Structure

```
regex2cpu/
├── regex_parser.py     # Regex → postfix (shunting-yard)
├── nfa.py              # Thompson's construction + ε-closure
├── dfa.py              # Subset construction + Hopcroft minimization
├── graph_tools.py      # BFS reachability + shortest accepted string
├── isa.py              # 16-bit ISA encode/decode + two-pass assembler
├── compiler.py         # DFA → assembly → machine code
├── cpu.py              # CPU simulator with fetch-decode-execute cycle
├── main.py             # CLI entry point
├── app.py              # Flask web API
├── static/
│   └── index.html      # Single-page web frontend
├── tests/
│   └── test_all.py     # 90 unittest test cases
├── requirements.txt    # Flask + gunicorn
├── Procfile            # Render/Heroku process definition
├── render.yaml         # Render infrastructure-as-code config
└── README.md           # This file
```

---

## ✍️ Author

**Sidhanth S** — S70  
Micro Project covering DAA · FLAT · COA

---

<div align="center">

**🚀 [Try the Live App](https://regex2cpu.onrender.com/) · [View Source](https://github.com/Sidh-006/Microproject-daa-flat-coa)**

*Built with Python 3 · Standard library only · Deployed on Render*

</div>
