from collections.abc import Callable

from .rules import rules
from .words import WordMatch, normalize, printed_parts, similarity

Equivalent = Callable[[str, str, str | None], bool]


class Alignment:
    def __init__(
        self,
        expected: list[str],
        heard: list[str],
        threshold: float,
        equivalent: Equivalent | None = None,
    ) -> None:
        self.expected = [normalize(word) for word in expected]
        self.heard = [normalize(word) for word in heard]
        self.threshold = threshold
        self.equivalent = equivalent
        self.printed_parts = [printed_parts(word) for word in expected]

    @property
    def join_threshold(self) -> float:
        return max(self.threshold, rules().join_floor)

    def joinable(self, words: list[str]) -> bool:
        return all(words)

    def vouched(self, written: str, said: str, after: str | None) -> bool:
        return self.equivalent is not None and self.equivalent(written, said, after)

    def preceding(self, row: int, back: int) -> str | None:
        return self.expected[row - back] if row >= back else None

    def worth(self, likeness: float, bar: float) -> float:
        return likeness if likeness >= bar else rules().mismatch_penalty

    def straight(self, row: int, column: int) -> float:
        if self.vouched(self.expected[row], self.heard[column], self.preceding(row, 1)):
            return 1.0
        return self.worth(similarity(self.expected[row], self.heard[column]), self.threshold)

    def joined_heard(self, row: int, column: int, span: int) -> float:
        parts = self.heard[column - span + 1 : column + 1]
        if not self.joinable(parts) or not self.expected[row]:
            return rules().mismatch_penalty
        joined = "".join(parts)
        if self.vouched(self.expected[row], joined, self.preceding(row, 1)):
            return 1.0
        return self.worth(similarity(self.expected[row], joined), self.join_threshold)

    def joined_expected(self, row: int, column: int) -> float:
        if not self.joinable(self.expected[row - 1 : row + 1]) or not self.heard[column]:
            return rules().mismatch_penalty
        joined = self.expected[row - 1] + self.expected[row]
        if self.vouched(joined, self.heard[column], self.preceding(row, 2)):
            return 1.0
        return self.worth(similarity(joined, self.heard[column]), self.join_threshold)

    def joined_pair(self, row: int, column: int) -> float:
        pair_written = self.expected[row - 1 : row + 1]
        pair_said = self.heard[column - 1 : column + 1]
        if not self.joinable(pair_written) or not self.joinable(pair_said):
            return rules().mismatch_penalty
        written = "".join(pair_written)
        said = "".join(pair_said)
        if self.vouched(written, said, self.preceding(row, 2)):
            return 1.0
        return self.worth(similarity(written, said), self.join_threshold)

    def spans(self, row: int) -> int:
        return max(2, self.printed_parts[row])

    def scores(self) -> list[list[float]]:
        gap = rules().gap_penalty
        rows, columns = len(self.expected), len(self.heard)
        score = [[0.0] * (columns + 1) for _ in range(rows + 1)]
        for row in range(1, rows + 1):
            score[row][0] = row * gap
        for column in range(1, columns + 1):
            score[0][column] = column * gap

        for row in range(1, rows + 1):
            for column in range(1, columns + 1):
                best = score[row - 1][column - 1] + self.straight(row - 1, column - 1)
                best = max(best, score[row - 1][column] + gap)
                best = max(best, score[row][column - 1] + gap)
                for span in range(2, self.spans(row - 1) + 1):
                    if column >= span:
                        reached = score[row - 1][column - span]
                        best = max(best, reached + self.joined_heard(row - 1, column - 1, span))
                if row >= 2:
                    best = max(best, score[row - 2][column - 1] + self.joined_expected(row - 1, column - 1))
                if row >= 2 and column >= 2:
                    best = max(best, score[row - 2][column - 2] + self.joined_pair(row - 1, column - 1))
                score[row][column] = best
        return score

    def matches(self, score: list[list[float]]) -> list[WordMatch]:
        gap = rules().gap_penalty
        found: list[WordMatch] = []
        row, column = len(self.expected), len(self.heard)
        while row > 0 and column > 0:
            cell = score[row][column]

            straight = self.straight(row - 1, column - 1)
            if cell == score[row - 1][column - 1] + straight:
                if straight >= self.threshold:
                    found.append(WordMatch(range(row - 1, row), range(column - 1, column)))
                row, column = row - 1, column - 1
                continue

            span = self.joined_span(score, cell, row, column)
            if span is not None:
                if self.joined_heard(row - 1, column - 1, span) >= self.join_threshold:
                    found.append(WordMatch(range(row - 1, row), range(column - span, column)))
                row, column = row - 1, column - span
                continue

            if row >= 2 and column >= 2 and cell == score[row - 2][column - 2] + self.joined_pair(row - 1, column - 1):
                if self.joined_pair(row - 1, column - 1) >= self.join_threshold:
                    found.append(WordMatch(range(row - 2, row), range(column - 2, column)))
                row, column = row - 2, column - 2
                continue

            if row >= 2 and cell == score[row - 2][column - 1] + self.joined_expected(row - 1, column - 1):
                if self.joined_expected(row - 1, column - 1) >= self.join_threshold:
                    found.append(WordMatch(range(row - 2, row), range(column - 1, column)))
                row, column = row - 2, column - 1
                continue

            if cell == score[row - 1][column] + gap:
                row -= 1
            else:
                column -= 1
        found.reverse()
        return found

    def joined_span(self, score: list[list[float]], cell: float, row: int, column: int) -> int | None:
        return next(
            (
                span
                for span in range(2, self.spans(row - 1) + 1)
                if column >= span
                and cell == score[row - 1][column - span] + self.joined_heard(row - 1, column - 1, span)
            ),
            None,
        )
