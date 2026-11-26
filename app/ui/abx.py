"""An ABX test's trials and its score, for Listen's ABX test (ui\\listen.py, 2026-10-26); nothing of Qt here.

Two versions, A and B. Each trial X is one of them, chosen at random for that trial on its own (not a shuffled half
and half: the last answers can't be worked out from the first ones); you listen to A, B and X as often as you like
and say which X is. At the end: how many were right, and how often guessing alone gets that many or more (the exact
chance, a coin for each trial, counted from the top: the binomial tail). Under 5 % (ENOUGH), you can tell them apart;
over it, that score could be luck. Nothing says whether an answer was right until the end.
"""
import math
import random

TRIALS = (8, 10, 12, 16, 20, 25)  # (how many trials a test can have; 16 to start with)
ENOUGH = 0.05


def chance(k, n):
    """How often guessing alone gets k or more of n trials right."""
    return sum(math.comb(n, i) for i in range(max(0, k), n + 1)) / 2 ** n


def percent(p):
    """A chance as a percentage that says how small it is. No space before "%": the text survey gave "< 0.1%"
    (2026-11-24), and the other values have the same form, as they show in the same place of the sentence."""
    if p < 0.001:
        return "< 0.1%"
    return f"{p * 100:.1f}%" if p < 0.1 else f"{p * 100:.0f}%"


class Abx:
    """One ABX test of the versions a and b (Listen's keys), n trials; rng: the randomness (a test's own, seeded)."""

    def __init__(self, a, b, trials=16, rng=None):
        rng = rng or random.SystemRandom()
        self.a, self.b, self.n = a, b, int(trials)
        self.xs = [rng.choice("AB") for _ in range(self.n)]
        self.answers = []

    @property
    def trial(self):
        return len(self.answers)

    @property
    def done(self):
        return len(self.answers) >= self.n

    def key(self, which):
        """The version heard for "A", "B" or "X" (the trial's own X)."""
        if which == "X":
            which = self.xs[min(self.trial, self.n - 1)]
        return self.a if which == "A" else self.b

    def answer(self, says):
        """X is A (says "A") or B: recorded for this trial, the next one begins. Whether it was right isn't said."""
        if not self.done and says in ("A", "B"):
            self.answers.append(says)

    def correct_count(self):
        return sum(1 for said, x in zip(self.answers, self.xs) if said == x)

    def verdict(self):
        k, n = self.correct_count(), len(self.answers)
        if not n:
            return "No trials completed"
        p = chance(k, n)
        if p < ENOUGH:
            return f"{k} of {n} correct ({percent(p)} chance of scoring {k}+ by guessing). You can hear a difference."
        return (f"{k} of {n} correct ({percent(p)} chance of scoring {k}+ by guessing). No clear audible difference"
                + (" (a longer test may detect small differences)." if n < 16 else "."))
