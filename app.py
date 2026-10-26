"""
app.py — Flask web frontend for regex2cpu.

Exposes a single POST /run endpoint that runs the full pipeline and
returns JSON. The static index.html is served at /.
"""

from __future__ import annotations

import io
import sys
import json
import traceback
from flask import Flask, request, jsonify, send_from_directory

# ── make sure the pipeline modules are importable ──────────────────────────
sys.path.insert(0, ".")

from regex_parser import parse
from nfa import NFA
from dfa import subset_construction
from graph_tools import bfs_reachable, shortest_accepted_string
from compiler import compile_dfa
from cpu import CPU
from isa import disassemble

app = Flask(__name__, static_folder="static", static_url_path="")


# ---------------------------------------------------------------------------
# Serve the SPA
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the main single-page application."""
    return send_from_directory("static", "index.html")


# ---------------------------------------------------------------------------
# Pipeline endpoint
# ---------------------------------------------------------------------------

@app.route("/run", methods=["POST"])
def run_pipeline():
    """Run the regex2cpu pipeline and return results as JSON.

    Request body (JSON):
        regex        (str)  — regular expression
        input_string (str)  — string to test
        show_asm     (bool) — include assembly listing
        show_trace   (bool) — include CPU trace
        show_dot     (bool) — include .dot source

    Response (JSON):
        ok           (bool)
        error        (str | null)
        nfa_states   (int)
        dfa_states   (int)
        alphabet     (str)
        removed      (list[str])
        shortest     (str | null)
        asm_lines    (list[str] | null)
        machine_words (list[str] | null)   — hex strings
        trace        (list[str] | null)
        result       (str)  — "ACCEPT" | "REJECT"
        cycles       (int)
        dot          (str | null)
        postfix      (str)
    """
    data = request.get_json(force=True)
    regex: str = data.get("regex", "").strip()
    input_string: str = data.get("input_string", "")
    show_asm: bool = bool(data.get("show_asm", False))
    show_trace: bool = bool(data.get("show_trace", False))
    show_dot: bool = bool(data.get("show_dot", False))

    if not regex:
        return jsonify(ok=False, error="Regex must not be empty."), 400

    try:
        # ── 1. Parse ─────────────────────────────────────────────────────
        postfix = parse(regex)

        # ── 2. NFA ───────────────────────────────────────────────────────
        nfa_obj = NFA(postfix)

        # ── 3. DFA ───────────────────────────────────────────────────────
        dfa_obj = subset_construction(nfa_obj)

        # ── 4. Graph analysis ─────────────────────────────────────────────
        all_before = set(dfa_obj.states)
        reachable = bfs_reachable(dfa_obj)
        removed = sorted(all_before - reachable)
        shortest = shortest_accepted_string(dfa_obj)

        # ── 5. Compile ────────────────────────────────────────────────────
        asm_lines, machine_words = compile_dfa(dfa_obj)

        # ── 6. CPU (with optional trace capture) ──────────────────────────
        trace_lines: list[str] = []
        if show_trace:
            # Redirect stdout to capture trace
            buf = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = buf
            try:
                cpu = CPU()
                cpu.load(machine_words)
                result, cycles = cpu.run(input_string, trace=True)
            finally:
                sys.stdout = old_stdout
            trace_lines = buf.getvalue().splitlines()
        else:
            cpu = CPU()
            cpu.load(machine_words)
            result, cycles = cpu.run(input_string, trace=False)

        # ── 7. Optional .dot ──────────────────────────────────────────────
        dot_src: str | None = None
        if show_dot:
            dot_src = _build_dot(dfa_obj)

        return jsonify(
            ok=True,
            error=None,
            postfix=postfix.replace("\u00b7", "."),  # middle-dot -> plain dot
            nfa_states=len(nfa_obj.states),
            dfa_states=len(dfa_obj.states),
            alphabet=", ".join(sorted(dfa_obj.alphabet)),
            removed=removed,
            shortest=shortest,
            asm_lines=asm_lines if show_asm else None,
            machine_words=[f"0x{w:04X}" for w in machine_words] if show_asm else None,
            trace=trace_lines if show_trace else None,
            result=result,
            cycles=cycles,
            dot=dot_src,
        )

    except ValueError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    except Exception as exc:
        return jsonify(ok=False, error=f"Internal error: {exc}\n{traceback.format_exc()}"), 500


# ---------------------------------------------------------------------------
# Helper: build .dot source
# ---------------------------------------------------------------------------

def _build_dot(dfa_obj) -> str:
    """Return a Graphviz .dot string for the DFA."""
    lines = ["digraph DFA {", '    rankdir=LR;', '    node [shape=circle];']
    if dfa_obj.accepting:
        accepting_str = " ".join(sorted(dfa_obj.accepting))
        lines.append(f'    node [shape=doublecircle]; {accepting_str};')
        lines.append('    node [shape=circle];')
    lines.append('    __start [shape=none label=""];')
    lines.append(f'    __start -> {dfa_obj.start};')
    for state, sym_map in sorted(dfa_obj.transitions.items()):
        for symbol, target in sorted(sym_map.items()):
            lines.append(f'    {state} -> {target} [label="{symbol}"];')
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
