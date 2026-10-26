"""
main.py — CLI entry point for the regex2cpu pipeline.

Usage:
    python main.py "<regex>" "<input_string>" [--trace] [--show-asm] [--dot]

Options:
    --trace     Print the CPU execution trace (one line per cycle).
    --show-asm  Print the generated assembly before running.
    --dot       Write a Graphviz .dot file of the DFA (no graphviz install needed).

Pipeline:
    1. Parse regex → postfix      (regex_parser)
    2. Postfix → NFA              (nfa)
    3. NFA → DFA                  (dfa)
    4. Prune unreachable states   (graph_tools)
    5. Find shortest accepted str (graph_tools)
    6. Compile DFA → assembly     (compiler)
    7. Assemble → machine code    (isa)
    8. Run on CPU simulator       (cpu)
"""

from __future__ import annotations

import argparse
import sys
import io

# Reconfigure stdout to UTF-8 so the middle-dot concatenation operator
# and other non-ASCII characters display correctly on all platforms.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from regex_parser import parse
from nfa import NFA
from dfa import subset_construction
from graph_tools import bfs_reachable, shortest_accepted_string
from compiler import compile_dfa
from cpu import CPU


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------


def build_pipeline(regex: str) -> tuple:
    """Run the regex → NFA → DFA → analysis pipeline.

    Args:
        regex: Raw infix regular expression string.

    Returns:
        Tuple of (postfix, nfa_obj, dfa_obj, removed_states, shortest_str,
                  asm_lines, machine_words).
    """
    postfix = parse(regex)
    nfa_obj = NFA(postfix)
    dfa_obj = subset_construction(nfa_obj)

    # --- Graph analysis ---
    all_states_before = set(dfa_obj.states)
    reachable = bfs_reachable(dfa_obj)
    removed = all_states_before - reachable

    shortest = shortest_accepted_string(dfa_obj)

    # --- Compile ---
    asm_lines, machine_words = compile_dfa(dfa_obj)

    return postfix, nfa_obj, dfa_obj, removed, shortest, asm_lines, machine_words


def run_cpu(machine_words: list[int], input_str: str, trace: bool) -> tuple[str, int]:
    """Load machine code into the CPU and run it on *input_str*.

    Args:
        machine_words: Assembled 16-bit instruction words.
        input_str: Input string to test.
        trace: Whether to print a cycle-by-cycle trace.

    Returns:
        Tuple of (result, cycle_count).
    """
    cpu = CPU()
    cpu.load(machine_words)
    return cpu.run(input_str, trace=trace)


def write_dot(dfa_obj, path: str) -> None:
    """Write a Graphviz .dot file representing the DFA.

    Written as plain text — graphviz installation not required.

    Args:
        dfa_obj: The DFA to visualise.
        path: Output file path.
    """
    lines = ["digraph DFA {", '    rankdir=LR;', '    node [shape=circle];']
    # Double-circle for accepting states
    if dfa_obj.accepting:
        accepting_str = " ".join(dfa_obj.accepting)
        lines.append(f'    node [shape=doublecircle]; {accepting_str};')
        lines.append('    node [shape=circle];')
    # Invisible start arrow
    lines.append(f'    __start [shape=none label=""];')
    lines.append(f'    __start -> {dfa_obj.start};')
    # Transitions
    for state, sym_map in sorted(dfa_obj.transitions.items()):
        for symbol, target in sorted(sym_map.items()):
            lines.append(f'    {state} -> {target} [label="{symbol}"];')
    lines.append("}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and run the full pipeline, printing labeled sections."""
    parser = argparse.ArgumentParser(
        description="regex2cpu: regex → NFA → DFA → assembly → CPU simulation"
    )
    parser.add_argument("regex", help="Regular expression (e.g. '(a|b)*abb')")
    parser.add_argument("input_string", help="Input string to test")
    parser.add_argument("--trace", action="store_true", help="Print CPU execution trace")
    parser.add_argument("--show-asm", action="store_true", help="Print generated assembly")
    parser.add_argument("--dot", action="store_true", help="Write DFA.dot file")
    args = parser.parse_args()

    sep = "=" * 60

    try:
        postfix, nfa_obj, dfa_obj, removed, shortest, asm_lines, machine_words = \
            build_pipeline(args.regex)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    # --- Section 1: State counts ---
    print(sep)
    print("1. AUTOMATA SUMMARY")
    print(sep)
    print(f"   Regex   : {args.regex}")
    print(f"   Postfix : {postfix.replace(chr(183), '.')}")  # middle-dot -> plain dot
    print(f"   NFA states : {len(nfa_obj.states)}")
    print(f"   DFA states : {len(dfa_obj.states)}")
    print(f"   Alphabet   : {{{', '.join(sorted(dfa_obj.alphabet))}}}")

    # --- Section 2: Unreachable states ---
    print()
    print(sep)
    print("2. GRAPH ANALYSIS (BFS)")
    print(sep)
    if removed:
        print(f"   Removed unreachable states: {sorted(removed)}")
    else:
        print("   No unreachable states detected.")
    print(f"   Shortest accepted string : {shortest!r}")

    # --- Section 3: Assembly ---
    if args.show_asm:
        print()
        print(sep)
        print("3. GENERATED ASSEMBLY")
        print(sep)
        for i, line in enumerate(asm_lines):
            print(f"   {line}")
        print()
        print(f"   Machine code ({len(machine_words)} words):")
        for i, word in enumerate(machine_words):
            print(f"   [{i:03d}] 0x{word:04X}")

    # --- Section 4: CPU execution ---
    print()
    print(sep)
    print("4. CPU EXECUTION")
    print(sep)
    print(f"   Input string : {args.input_string!r}")
    if args.trace:
        print()

    try:
        result, cycles = run_cpu(machine_words, args.input_string, trace=args.trace)
    except RuntimeError as e:
        print(f"[ERROR] CPU error: {e}", file=sys.stderr)
        sys.exit(1)

    print()
    print(sep)
    print("5. FINAL RESULT")
    print(sep)
    print(f"   Result : {result}")
    print(f"   Cycles : {cycles}")
    print(sep)

    # --- Optional: .dot file ---
    if args.dot:
        dot_path = "DFA.dot"
        write_dot(dfa_obj, dot_path)
        print(f"\n   DFA dot file written to: {dot_path}")


if __name__ == "__main__":
    main()
