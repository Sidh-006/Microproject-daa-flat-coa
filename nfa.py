"""
nfa.py — Non-deterministic Finite Automaton via Thompson's construction.

Course topic: Formal Languages & Automata Theory
  Thompson's construction inductively builds an NFA from a postfix regex.
  Each operator (literal, |, ·, *) maps to a small NFA fragment connected
  by epsilon transitions.

Key operations:
  epsilon_closure(states) — set of states reachable via epsilon only
  move(states, symbol)    — set of states reachable on a single symbol
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# NFA State
# ---------------------------------------------------------------------------


@dataclass
class NFAState:
    """A single NFA state.

    Attributes:
        sid: Unique integer identifier.
        transitions: Map from input symbol to set of target states.
        epsilon: Set of states reachable via epsilon (ε) transitions.
        is_accept: True if this is an accepting state.
    """

    sid: int
    transitions: dict[str, set["NFAState"]] = field(default_factory=dict)
    epsilon: set["NFAState"] = field(default_factory=set)
    is_accept: bool = False

    def __hash__(self) -> int:  # noqa: D105
        return hash(self.sid)

    def __eq__(self, other: object) -> bool:  # noqa: D105
        return isinstance(other, NFAState) and self.sid == other.sid

    def __repr__(self) -> str:  # noqa: D105
        return f"NFAState({self.sid})"


# ---------------------------------------------------------------------------
# NFA Fragment (used during Thompson's construction)
# ---------------------------------------------------------------------------


@dataclass
class _NFAFragment:
    """A partial NFA with exactly one start and one accept state.

    Thompson's construction treats each sub-regex as a fragment that
    can be connected to other fragments.
    """

    start: NFAState
    accept: NFAState


# ---------------------------------------------------------------------------
# Thompson's Construction
# ---------------------------------------------------------------------------


class NFA:
    """Full NFA built from a postfix regex string via Thompson's construction.

    Attributes:
        start: The start state.
        accept: The single accepting state.
        states: All states in the NFA.
        alphabet: Set of literal symbols used.
    """

    def __init__(self, postfix: str) -> None:
        """Build the NFA from a postfix regex.

        Args:
            postfix: Postfix regex string (from regex_parser.to_postfix).

        Raises:
            ValueError: If the postfix expression is invalid.
        """
        self._counter = 0
        self.alphabet: set[str] = set()
        fragment = self._build(postfix)
        self.start: NFAState = fragment.start
        self.accept: NFAState = fragment.accept
        self.accept.is_accept = True
        # Collect all states via BFS
        self.states: list[NFAState] = self._collect_states()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _new_state(self) -> NFAState:
        """Create and return a fresh NFA state with a unique id."""
        state = NFAState(self._counter)
        self._counter += 1
        return state

    def _build(self, postfix: str) -> _NFAFragment:
        """Core Thompson's construction — process postfix token by token.

        Stack invariant: each item on the stack is an _NFAFragment.
        """
        stack: list[_NFAFragment] = []

        for ch in postfix:
            if ch not in ("|", "·", "*"):
                # --- Literal ---
                # Fragment: s0 --ch--> s1
                s0, s1 = self._new_state(), self._new_state()
                s0.transitions[ch] = {s1}
                self.alphabet.add(ch)
                stack.append(_NFAFragment(s0, s1))

            elif ch == "*":
                # --- Kleene Star ---
                # New start s0 epsilon→ inner.start and inner.accept epsilon→ s0
                # (allows zero or more repetitions)
                inner = stack.pop()
                s0, s1 = self._new_state(), self._new_state()
                s0.epsilon |= {inner.start, s1}  # zero: skip inner; one+: enter
                inner.accept.epsilon |= {inner.start, s1}  # loop or exit
                stack.append(_NFAFragment(s0, s1))

            elif ch == "·":
                # --- Concatenation ---
                # frag1.accept ε→ frag2.start
                frag2 = stack.pop()
                frag1 = stack.pop()
                frag1.accept.epsilon.add(frag2.start)
                stack.append(_NFAFragment(frag1.start, frag2.accept))

            elif ch == "|":
                # --- Union / Alternation ---
                # New s0 ε→ {frag1.start, frag2.start}
                # frag1.accept, frag2.accept ε→ new s1
                frag2 = stack.pop()
                frag1 = stack.pop()
                s0, s1 = self._new_state(), self._new_state()
                s0.epsilon |= {frag1.start, frag2.start}
                frag1.accept.epsilon.add(s1)
                frag2.accept.epsilon.add(s1)
                stack.append(_NFAFragment(s0, s1))

        if len(stack) != 1:
            raise ValueError(
                f"Invalid postfix expression: stack has {len(stack)} items at end."
            )
        return stack[0]

    def _collect_states(self) -> list[NFAState]:
        """Return all NFA states reachable from self.start (BFS)."""
        visited: set[NFAState] = set()
        queue = [self.start]
        while queue:
            state = queue.pop(0)
            if state in visited:
                continue
            visited.add(state)
            for targets in state.transitions.values():
                queue.extend(targets)
            queue.extend(state.epsilon)
        return list(visited)


# ---------------------------------------------------------------------------
# Public operations used by subset construction (dfa.py)
# ---------------------------------------------------------------------------


def epsilon_closure(states: set[NFAState]) -> frozenset[NFAState]:
    """Return the epsilon-closure of a set of NFA states.

    The epsilon-closure of S is the set of all states reachable from any
    state in S via zero or more epsilon transitions.

    Time complexity: O(V + E) where V = states, E = epsilon edges.

    Args:
        states: Starting set of NFA states.

    Returns:
        Frozenset of all states reachable via epsilon (including *states*).
    """
    closure = set(states)
    stack = list(states)
    while stack:
        state = stack.pop()
        for eps_state in state.epsilon:
            if eps_state not in closure:
                closure.add(eps_state)
                stack.append(eps_state)
    return frozenset(closure)


def move(states: frozenset[NFAState], symbol: str) -> set[NFAState]:
    """Return the set of NFA states reachable from *states* on *symbol*.

    This is the standard 'move' function used in subset construction.

    Args:
        states: Current set of NFA states.
        symbol: Input character.

    Returns:
        Set of NFA states reachable by consuming exactly *symbol*.
    """
    result: set[NFAState] = set()
    for state in states:
        result |= state.transitions.get(symbol, set())
    return result
