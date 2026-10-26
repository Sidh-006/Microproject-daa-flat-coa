"""
dfa.py — Deterministic Finite Automaton via subset construction.

Course topic: Formal Languages & Automata Theory
  Subset construction (powerset construction) converts an NFA to an
  equivalent DFA. Each DFA state represents a *frozenset* of NFA states.

Design note on dead/trap state:
  We do NOT add an explicit dead state. Transitions for unrecognised symbols
  simply remain absent from the transition table. The simulator (cpu.py) and
  the accepts() method both treat a missing transition as an immediate reject.
  This keeps the DFA minimal for simple regexes and avoids O(|Sigma|) extra
  transitions per state.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from nfa import NFA, NFAState, epsilon_closure, move


# ---------------------------------------------------------------------------
# DFA Data Structure
# ---------------------------------------------------------------------------


@dataclass
class DFA:
    """A Deterministic Finite Automaton produced by subset construction.

    Attributes:
        states: Ordered list of state names (e.g. ["S0", "S1", ...]).
        alphabet: Set of symbols the DFA recognises.
        transitions: transitions[state][symbol] = next_state  (partial map).
        start: Name of the start state (always "S0").
        accepting: Set of accepting state names.
    """

    states: list[str]
    alphabet: set[str]
    transitions: dict[str, dict[str, str]]
    start: str
    accepting: set[str]

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def accepts(self, string: str) -> bool:
        """Return True if *string* is accepted by this DFA.

        Pure-Python simulation -- used for verification against the CPU.

        Args:
            string: Input string to test.

        Returns:
            True if the DFA accepts *string*, False otherwise.
        """
        current = self.start
        for ch in string:
            nxt = self.transitions.get(current, {}).get(ch)
            if nxt is None:
                return False  # missing transition -> reject (no dead state)
            current = nxt
        return current in self.accepting


# ---------------------------------------------------------------------------
# Subset Construction
# ---------------------------------------------------------------------------


def subset_construction(nfa: NFA) -> "DFA":
    """Convert *nfa* to an equivalent minimal DFA using subset construction.

    Algorithm (powerset construction):
      1. Start DFA state = epsilon-closure({nfa.start}).
      2. For each unmarked DFA state T and each symbol a in Sigma:
           U = epsilon-closure(move(T, a))
           If U is non-empty, add transition T --a--> U.
      3. A DFA state is accepting iff it contains nfa.accept.

    After subset construction, Hopcroft's minimization is applied to merge
    equivalent (indistinguishable) states, producing the minimal DFA.

    Time complexity: O(2^n * |Sigma|) worst case, O(n * |Sigma|) typical.

    Args:
        nfa: NFA produced by Thompson's construction.

    Returns:
        Equivalent minimal DFA with states named S0, S1, ...
    """
    alphabet: set[str] = nfa.alphabet

    # Map from frozenset-of-NFA-states -> DFA state name
    state_map: dict[frozenset, str] = {}
    # transitions[dfa_name][symbol] = dfa_name
    transitions: dict[str, dict[str, str]] = {}
    accepting: set[str] = set()

    def _name_for(nfa_set: frozenset) -> str:
        """Return the DFA state name for *nfa_set*, creating one if needed."""
        if nfa_set not in state_map:
            name = f"S{len(state_map)}"
            state_map[nfa_set] = name
            transitions[name] = {}
            # A DFA state is accepting iff it contains the NFA accept state
            if nfa.accept in nfa_set:
                accepting.add(name)
        return state_map[nfa_set]

    # BFS over DFA states
    start_set = epsilon_closure({nfa.start})
    start_name = _name_for(start_set)

    queue: deque = deque([start_set])
    visited: set = set()

    while queue:
        current_set = queue.popleft()
        if current_set in visited:
            continue
        visited.add(current_set)
        current_name = state_map[current_set]

        for symbol in sorted(alphabet):  # sorted for deterministic output
            moved = move(current_set, symbol)
            if not moved:
                continue  # no transition on this symbol (implicit dead state)
            target_set = epsilon_closure(moved)
            if not target_set:
                continue
            target_name = _name_for(target_set)
            transitions[current_name][symbol] = target_name
            if target_set not in visited:
                queue.append(target_set)

    # Build ordered state list (S0 first, rest in numeric order)
    states = sorted(state_map.values(), key=lambda s: int(s[1:]))

    raw_dfa = DFA(
        states=states,
        alphabet=alphabet,
        transitions=transitions,
        start=start_name,
        accepting=accepting,
    )
    return minimize(raw_dfa)


# ---------------------------------------------------------------------------
# DFA Minimization (Hopcroft's partition-refinement algorithm)
# ---------------------------------------------------------------------------


def minimize(dfa: "DFA") -> "DFA":
    """Return the minimal DFA equivalent to *dfa* using Hopcroft's algorithm.

    Hopcroft's algorithm partitions DFA states into equivalence classes of
    indistinguishable states, then merges each class into a single state.

    Course topic: Formal Languages & Automata Theory
      Minimization ensures the DFA has no redundant states -- two states are
      equivalent (and therefore merged) iff they have identical behaviour for
      every possible input string.

    Time complexity: O(n * |Sigma| * log n) where n = number of DFA states.

    Args:
        dfa: A (possibly non-minimal) DFA.

    Returns:
        An equivalent minimal DFA with states re-named S0, S1, ...
    """
    states = dfa.states
    alphabet = sorted(dfa.alphabet)

    if not states:
        return dfa

    # Initial partition: accepting vs non-accepting
    accepting_set = frozenset(dfa.accepting)
    non_accepting = frozenset(s for s in states if s not in accepting_set)

    # Build initial partitions (drop empty sets)
    partitions: list[frozenset] = []
    if accepting_set:
        partitions.append(accepting_set)
    if non_accepting:
        partitions.append(non_accepting)

    # Worklist: partitions to use as splitters
    worklist: list[frozenset] = list(partitions)

    while worklist:
        splitter = worklist.pop()
        for symbol in alphabet:
            # X = set of states that transition on symbol into splitter
            X: set[str] = set()
            for s in states:
                target = dfa.transitions.get(s, {}).get(symbol)
                if target in splitter:
                    X.add(s)
            if not X:
                continue

            new_partitions: list[frozenset] = []
            for part in partitions:
                inter = part & X
                diff  = part - X
                if inter and diff:
                    # Split this partition into two groups
                    new_partitions.append(inter)
                    new_partitions.append(diff)
                    if part in worklist:
                        worklist.remove(part)
                        worklist.append(inter)
                        worklist.append(diff)
                    else:
                        # Add the smaller half to minimise work
                        worklist.append(inter if len(inter) <= len(diff) else diff)
                else:
                    new_partitions.append(part)
            partitions = new_partitions

    # Build mapping: old_state -> canonical representative of its partition
    # (lexicographically smallest state name in the partition)
    rep: dict[str, str] = {}
    for part in partitions:
        canonical = min(part)  # pick smallest as representative
        for s in part:
            rep[s] = canonical

    # Collect unique representatives
    new_states_set = set(rep.values())
    new_start_rep = rep[dfa.start]

    # Rename: start state becomes S0, rest get S1, S2, ... in sorted order
    ordered = sorted(new_states_set,
                     key=lambda s: (0 if s == new_start_rep else 1, s))
    rename: dict[str, str] = {old: f"S{i}" for i, old in enumerate(ordered)}

    # Build new transition table
    new_transitions: dict[str, dict[str, str]] = {}
    for old_rep in new_states_set:
        new_name = rename[old_rep]
        new_transitions[new_name] = {}
        for symbol in alphabet:
            target = dfa.transitions.get(old_rep, {}).get(symbol)
            if target is not None:
                new_target_rep = rep[target]
                new_transitions[new_name][symbol] = rename[new_target_rep]

    new_accepting = {
        rename[rep[s]] for s in dfa.accepting if rep[s] in new_states_set
    }
    new_states = sorted(new_transitions.keys(), key=lambda s: int(s[1:]))

    return DFA(
        states=new_states,
        alphabet=dfa.alphabet,
        transitions=new_transitions,
        start=rename[new_start_rep],
        accepting=new_accepting,
    )
