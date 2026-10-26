"""
graph_tools.py — DFA graph analysis using BFS.

Course topic: Design & Analysis of Algorithms
  Treats the DFA as a directed graph and applies BFS for:
    1. Reachability analysis (prune unreachable states).
    2. Finding the shortest accepted string (shortest path to an accept state).

Time complexity of both operations: O(V + E)
  where V = number of DFA states, E = number of transitions.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from dfa import DFA


# ---------------------------------------------------------------------------
# BFS Reachability
# ---------------------------------------------------------------------------


def bfs_reachable(dfa: DFA) -> set[str]:
    """Return the set of DFA states reachable from the start state via BFS.

    Modifies *dfa* in-place: removes unreachable states from dfa.states,
    dfa.transitions, and dfa.accepting.

    Time complexity: O(V + E) — standard BFS.

    Args:
        dfa: The DFA to analyse (modified in-place).

    Returns:
        Set of reachable state names.
    """
    # BFS from start state
    reachable: set[str] = set()
    queue: deque[str] = deque([dfa.start])
    while queue:
        state = queue.popleft()
        if state in reachable:
            continue
        reachable.add(state)
        for symbol in dfa.alphabet:
            nxt = dfa.transitions.get(state, {}).get(symbol)
            if nxt and nxt not in reachable:
                queue.append(nxt)

    # Prune unreachable states from the DFA in-place
    unreachable = set(dfa.states) - reachable
    if unreachable:
        dfa.states = [s for s in dfa.states if s in reachable]
        for state in unreachable:
            dfa.transitions.pop(state, None)
        dfa.accepting -= unreachable

    return reachable


# ---------------------------------------------------------------------------
# Shortest Accepted String
# ---------------------------------------------------------------------------


def shortest_accepted_string(dfa: DFA) -> Optional[str]:
    """Return the lexicographically-shortest string accepted by *dfa*, or None.

    Uses BFS over DFA states, tracking the string accumulated so far.
    Because BFS explores states layer by layer (shortest path first),
    the first accepted state reached gives the minimum-length solution.

    Time complexity: O(V + E) — each state is enqueued at most once.

    Args:
        dfa: The DFA to query.

    Returns:
        The shortest accepted string, or None if the language is empty.
    """
    if not dfa.states:
        return None

    # BFS: queue entries are (current_state, string_so_far)
    # Sort alphabet so we always try symbols in lexicographic order,
    # guaranteeing the lexicographically smallest string of minimum length.
    sorted_alphabet = sorted(dfa.alphabet)

    visited: set[str] = set()
    queue: deque[tuple[str, str]] = deque([(dfa.start, "")])

    while queue:
        state, path = queue.popleft()
        if state in visited:
            continue
        visited.add(state)

        if state in dfa.accepting:
            return path  # shortest accepted string found

        for symbol in sorted_alphabet:
            nxt = dfa.transitions.get(state, {}).get(symbol)
            if nxt and nxt not in visited:
                queue.append((nxt, path + symbol))

    return None  # no accepting state reachable → empty language
