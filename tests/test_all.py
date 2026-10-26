"""
tests/test_all.py — Comprehensive unittest suite for the regex2cpu pipeline.

Tests:
  1. DFA accepts() vs CPU simulation — must give identical results for every test string.
  2. (a|b)*abb — exactly 4 DFA states, shortest accepted string = "abb".
  3. Assembler/disassembler round-trip.
  4. Invalid regex raises ValueError.
  5. Coverage over 5 regex patterns, 10+ strings each.
"""

import sys
import os
import unittest

# Ensure the parent directory (regex2cpu/) is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from regex_parser import parse, insert_concat, to_postfix
from nfa import NFA
from dfa import subset_construction
from graph_tools import bfs_reachable, shortest_accepted_string
from compiler import compile_dfa
from cpu import CPU
from isa import assemble, disassemble, OPCODES


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def build(regex: str):
    """Build a (dfa, machine_words) pair for a given regex string."""
    postfix = parse(regex)
    nfa_obj = NFA(postfix)
    dfa_obj = subset_construction(nfa_obj)
    bfs_reachable(dfa_obj)
    _, machine_words = compile_dfa(dfa_obj)
    return dfa_obj, machine_words


def cpu_accepts(machine_words: list[int], s: str) -> bool:
    """Return True if the CPU simulation accepts string *s*."""
    cpu = CPU()
    cpu.load(machine_words)
    result, _ = cpu.run(s, trace=False)
    return result == "ACCEPT"


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestRegexParser(unittest.TestCase):
    """Tests for regex_parser.py"""

    def test_insert_concat_simple(self):
        self.assertEqual(insert_concat("ab"), "a·b")

    def test_insert_concat_star(self):
        self.assertEqual(insert_concat("a*b"), "a*·b")

    def test_insert_concat_parens(self):
        self.assertEqual(insert_concat("(a|b)c"), "(a|b)·c")

    def test_postfix_single(self):
        self.assertEqual(to_postfix("a"), "a")

    def test_postfix_concat(self):
        self.assertEqual(to_postfix("a·b"), "ab·")

    def test_postfix_union(self):
        self.assertEqual(to_postfix("a|b"), "ab|")

    def test_postfix_star(self):
        self.assertEqual(to_postfix("a*"), "a*")

    def test_full_parse_aabb(self):
        # (a|b)*abb → postfix should be valid
        pf = parse("(a|b)*abb")
        self.assertIn("*", pf)
        self.assertIn("|", pf)

    def test_invalid_unbalanced_open(self):
        with self.assertRaises(ValueError):
            parse("(ab")

    def test_invalid_unbalanced_close(self):
        with self.assertRaises(ValueError):
            parse("ab)")

    def test_invalid_empty(self):
        with self.assertRaises(ValueError):
            parse("")

    def test_invalid_unsupported_char(self):
        with self.assertRaises(ValueError):
            parse("a@b")


class TestNFA(unittest.TestCase):
    """Tests for nfa.py"""

    def test_single_literal(self):
        nfa = NFA(parse("a"))
        self.assertGreater(len(nfa.states), 0)
        self.assertIn("a", nfa.alphabet)

    def test_union_alphabet(self):
        nfa = NFA(parse("a|b"))
        self.assertIn("a", nfa.alphabet)
        self.assertIn("b", nfa.alphabet)

    def test_kleene_star(self):
        nfa = NFA(parse("a*"))
        self.assertIn("a", nfa.alphabet)


class TestDFA_AbbPattern(unittest.TestCase):
    """(a|b)*abb — the classic 4-state DFA from Aho/Hopcroft."""

    def setUp(self):
        self.dfa, self.words = build("(a|b)*abb")

    def test_four_states(self):
        """(a|b)*abb must yield exactly 4 DFA states."""
        self.assertEqual(len(self.dfa.states), 4,
                         f"Expected 4 states, got {len(self.dfa.states)}: {self.dfa.states}")

    def test_shortest_accepted(self):
        """Shortest accepted string must be 'abb'."""
        s = shortest_accepted_string(self.dfa)
        self.assertEqual(s, "abb")

    def _assert_consistent(self, s: str, expected: bool):
        """Assert dfa.accepts and CPU agree on string s."""
        dfa_result = self.dfa.accepts(s)
        cpu_result = cpu_accepts(self.words, s)
        self.assertEqual(dfa_result, expected,
                         f"dfa.accepts({s!r}) = {dfa_result}, expected {expected}")
        self.assertEqual(cpu_result, expected,
                         f"CPU({s!r}) = {cpu_result}, expected {expected}")
        self.assertEqual(dfa_result, cpu_result,
                         f"DFA and CPU disagree on {s!r}")

    # Accepting strings
    def test_abb(self):          self._assert_consistent("abb", True)
    def test_aabb(self):         self._assert_consistent("aabb", True)
    def test_babb(self):         self._assert_consistent("babb", True)
    def test_ababb(self):        self._assert_consistent("ababb", True)
    def test_aababb(self):       self._assert_consistent("aababb", True)
    def test_bbbabb(self):       self._assert_consistent("bbbabb", True)
    def test_abbabb(self):       self._assert_consistent("abbabb", True)

    # Rejecting strings
    def test_empty(self):        self._assert_consistent("", False)
    def test_a(self):            self._assert_consistent("a", False)
    def test_ab(self):           self._assert_consistent("ab", False)
    def test_ba(self):           self._assert_consistent("ba", False)
    def test_abba(self):         self._assert_consistent("abba", False)
    def test_aab(self):          self._assert_consistent("aab", False)


class TestDFA_AStar_B(unittest.TestCase):
    """a*b — accepts any number of 'a's followed by exactly one 'b'."""

    def setUp(self):
        self.dfa, self.words = build("a*b")

    def _check(self, s: str, expected: bool):
        dfa_r = self.dfa.accepts(s)
        cpu_r = cpu_accepts(self.words, s)
        self.assertEqual(dfa_r, expected, f"DFA wrong on {s!r}")
        self.assertEqual(cpu_r, expected, f"CPU wrong on {s!r}")
        self.assertEqual(dfa_r, cpu_r, f"DFA/CPU disagree on {s!r}")

    def test_b(self):            self._check("b", True)
    def test_ab(self):           self._check("ab", True)
    def test_aab(self):          self._check("aab", True)
    def test_aaab(self):         self._check("aaab", True)
    def test_aaaab(self):        self._check("aaaab", True)
    def test_empty(self):        self._check("", False)
    def test_a(self):            self._check("a", False)
    def test_ba(self):           self._check("ba", False)
    def test_bb(self):           self._check("bb", False)
    def test_abb(self):          self._check("abb", False)
    def test_aabb(self):         self._check("aabb", False)


class TestDFA_ABStar(unittest.TestCase):
    """(ab)* — accepts "", "ab", "abab", "ababab", ..."""

    def setUp(self):
        self.dfa, self.words = build("(ab)*")

    def _check(self, s: str, expected: bool):
        dfa_r = self.dfa.accepts(s)
        cpu_r = cpu_accepts(self.words, s)
        self.assertEqual(dfa_r, expected, f"DFA wrong on {s!r}")
        self.assertEqual(cpu_r, expected, f"CPU wrong on {s!r}")
        self.assertEqual(dfa_r, cpu_r, f"DFA/CPU disagree on {s!r}")

    def test_empty(self):        self._check("", True)
    def test_ab(self):           self._check("ab", True)
    def test_abab(self):         self._check("abab", True)
    def test_ababab(self):       self._check("ababab", True)
    def test_a(self):            self._check("a", False)
    def test_b(self):            self._check("b", False)
    def test_ba(self):           self._check("ba", False)
    def test_aba(self):          self._check("aba", False)
    def test_aab(self):          self._check("aab", False)
    def test_abba(self):         self._check("abba", False)
    def test_abb(self):          self._check("abb", False)


class TestDFA_UnionABC(unittest.TestCase):
    """a|b|c — accepts exactly one character: 'a', 'b', or 'c'."""

    def setUp(self):
        self.dfa, self.words = build("a|b|c")

    def _check(self, s: str, expected: bool):
        dfa_r = self.dfa.accepts(s)
        cpu_r = cpu_accepts(self.words, s)
        self.assertEqual(dfa_r, expected, f"DFA wrong on {s!r}")
        self.assertEqual(cpu_r, expected, f"CPU wrong on {s!r}")
        self.assertEqual(dfa_r, cpu_r, f"DFA/CPU disagree on {s!r}")

    def test_a(self):            self._check("a", True)
    def test_b(self):            self._check("b", True)
    def test_c(self):            self._check("c", True)
    def test_empty(self):        self._check("", False)
    def test_ab(self):           self._check("ab", False)
    def test_aa(self):           self._check("aa", False)
    def test_abc(self):          self._check("abc", False)
    def test_d(self):            self._check("d", False)
    def test_bc(self):           self._check("bc", False)
    def test_ca(self):           self._check("ca", False)
    def test_cc(self):           self._check("cc", False)


class TestDFA_ABStarC(unittest.TestCase):
    """ab*c — 'a' followed by zero or more 'b's followed by 'c'."""

    def setUp(self):
        self.dfa, self.words = build("ab*c")

    def _check(self, s: str, expected: bool):
        dfa_r = self.dfa.accepts(s)
        cpu_r = cpu_accepts(self.words, s)
        self.assertEqual(dfa_r, expected, f"DFA wrong on {s!r}")
        self.assertEqual(cpu_r, expected, f"CPU wrong on {s!r}")
        self.assertEqual(dfa_r, cpu_r, f"DFA/CPU disagree on {s!r}")

    def test_ac(self):           self._check("ac", True)
    def test_abc(self):          self._check("abc", True)
    def test_abbc(self):         self._check("abbc", True)
    def test_abbbc(self):        self._check("abbbc", True)
    def test_abbbbc(self):       self._check("abbbbc", True)
    def test_empty(self):        self._check("", False)
    def test_a(self):            self._check("a", False)
    def test_b(self):            self._check("b", False)
    def test_c(self):            self._check("c", False)
    def test_ab(self):           self._check("ab", False)
    def test_bc(self):           self._check("bc", False)
    def test_acc(self):          self._check("acc", False)


class TestAssemblerDisassembler(unittest.TestCase):
    """Round-trip: assemble then disassemble should be stable."""

    def test_round_trip_basic(self):
        """A simple program should survive assemble → disassemble."""
        asm_in = [
            "START: LOAD R1",
            "       CMP  R1, 0",
            "       JEQ  DONE",
            "       JMP  START",
            "DONE:  ACCEPT",
        ]
        words = assemble(asm_in)
        self.assertEqual(len(words), 5)

        lines = disassemble(words)
        self.assertEqual(lines[0], "LOAD R1")
        self.assertEqual(lines[1], "CMP R1, '\\x00'".replace("'\\x00'", "0"))
        self.assertIn("JEQ", lines[2])
        self.assertIn("JMP", lines[3])
        self.assertEqual(lines[4], "ACCEPT")

    def test_round_trip_char_literal(self):
        """CMP with a character literal should encode/decode correctly."""
        asm_in = ["CMP R1, 'a'"]
        words = assemble(asm_in)
        self.assertEqual(len(words), 1)
        lines = disassemble(words)
        self.assertIn("'a'", lines[0])

    def test_reject_instruction(self):
        """REJECT should encode and disassemble correctly."""
        words = assemble(["REJECT"])
        lines = disassemble(words)
        self.assertEqual(lines[0], "REJECT")

    def test_label_resolution(self):
        """Labels should resolve to correct addresses."""
        asm_in = [
            "JMP END",    # addr 0 → jumps to 1
            "END: ACCEPT",
        ]
        words = assemble(asm_in)
        # JMP END → operand should be 1 (address of ACCEPT)
        self.assertEqual(words[0] & 0xFF, 1)

    def test_unknown_mnemonic_raises(self):
        """Unknown mnemonic should raise ValueError."""
        with self.assertRaises(ValueError):
            assemble(["FOO R1"])

    def test_unknown_register_raises(self):
        """Unknown register should raise ValueError."""
        with self.assertRaises(ValueError):
            assemble(["LOAD R9"])


class TestGraphTools(unittest.TestCase):
    """Tests for graph_tools.py"""

    def test_bfs_reachable_no_pruning(self):
        """For (a|b)*abb all states should be reachable."""
        dfa, _ = build("(a|b)*abb")
        # Already pruned in build(); states should still be 4
        self.assertEqual(len(dfa.states), 4)

    def test_shortest_string_abb(self):
        """(a|b)*abb → shortest accepted string is 'abb'."""
        postfix = parse("(a|b)*abb")
        nfa_obj = NFA(postfix)
        dfa_obj = subset_construction(nfa_obj)
        bfs_reachable(dfa_obj)
        s = shortest_accepted_string(dfa_obj)
        self.assertEqual(s, "abb")

    def test_shortest_string_astar_b(self):
        """a*b → shortest is 'b'."""
        postfix = parse("a*b")
        nfa_obj = NFA(postfix)
        dfa_obj = subset_construction(nfa_obj)
        bfs_reachable(dfa_obj)
        s = shortest_accepted_string(dfa_obj)
        self.assertEqual(s, "b")


class TestInvalidRegex(unittest.TestCase):
    """Tests that invalid regexes raise ValueError."""

    def test_unbalanced_open_paren(self):
        with self.assertRaises(ValueError):
            parse("(ab")

    def test_unbalanced_close_paren(self):
        with self.assertRaises(ValueError):
            parse("ab)")

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            parse("")

    def test_unsupported_character(self):
        with self.assertRaises(ValueError):
            parse("a.b")

    def test_double_star(self):
        # "a**" is degenerate but should not crash — it's valid postfix-wise
        # (a* then * again), so we only test truly invalid cases
        with self.assertRaises(ValueError):
            parse("*")

    def test_dangling_union(self):
        with self.assertRaises(ValueError):
            parse("a|")


if __name__ == "__main__":
    unittest.main(verbosity=2)
