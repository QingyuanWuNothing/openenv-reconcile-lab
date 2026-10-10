"""Online difficulty selection within fixed, equally represented domain IDs."""

import math
import random
import threading
from .optimization import entropy, optimize


class Curriculum:
    # Fractional baseline and the separate binary candidate use distinct priors.
    # Both reward means start at 1/2. Only binary completion uses Beta(1,1).
    REWARD_PRIOR = (0.5, 0.5, 0.5, 0.5)

    def __init__(
        self,
        families,
        exploration=0.30,
        decay=0.97,
        priors=None,
        reward_mode="fractional",
        group_priors=None,
    ):
        self.families = tuple(families)
        self.exploration, self.decay = exploration, decay
        self.lock = threading.RLock()
        self.bags = {f: [] for f in families}
        self.reward_mode = reward_mode
        self.reward_prior = (
            (1.0, 0.0, 0.0, 1.0) if reward_mode == "binary" else self.REWARD_PRIOR
        )
        self.cells = {
            (f, level): {
                "success": 1.0,
                "failure": 1.0,
                "n": 0,
                "reward_sum": 0.0,
                "reward_counts": list(self.reward_prior),
                "calibration_n": 0,
                "same_instance_groups": 0,
                "mixed_same_instance_groups": 0,
            }
            for f in families
            for level in (1, 2, 3)
        }
        if priors:
            for family, levels in priors.items():
                for level, counts in levels.items():
                    if (
                        not isinstance(counts, list)
                        or len(counts) != 4
                        or any(type(n) is not int or n < 0 for n in counts)
                        or sum(counts) > 10000
                    ):
                        raise ValueError("Invalid calibration reward counts")
                    cell = self.cells[family, int(level)]
                    cell["success"] += counts[3]
                    cell["failure"] += sum(counts[:3])
                    # This projection is exact for joint completion: partial
                    # outcomes failed at least one necessary behavioral check.
                    reward_counts = (
                        [sum(counts[:3]), 0, 0, counts[3]]
                        if reward_mode == "binary"
                        else counts
                    )
                    cell["reward_counts"] = [
                        prior + n for prior, n in zip(self.reward_prior, reward_counts)
                    ]
                    cell["calibration_n"] = sum(counts)
        for family, levels in (group_priors or {}).items():
            for level, counts in levels.items():
                if (
                    not isinstance(counts, list)
                    or len(counts) != 2
                    or any(type(n) is not int or n < 0 for n in counts)
                    or sum(counts) > 10000
                ):
                    raise ValueError("Invalid same-instance group counts")
                cell = self.cells[family, int(level)]
                cell["same_instance_groups"] = sum(counts)
                cell["mixed_same_instance_groups"] = counts[1]

    def observe_group(self, family, level, rewards):
        """Caller must provide four attempts on one identical problem instance."""
        if len(rewards) != 4 or any(
            not math.isfinite(r) or not 0 <= r <= 1 for r in rewards
        ):
            raise ValueError("A group requires four finite rewards")
        with self.lock:
            cell = self.cells[family, level]
            cell["same_instance_groups"] += 1
            cell["mixed_same_instance_groups"] += len(set(rewards)) > 1

    def learnability(self, cell):
        proxy = self.mixed_group_score(cell)
        if not cell["same_instance_groups"]:
            return proxy
        empirical = (1 + cell["mixed_same_instance_groups"]) / (
            2 + cell["same_instance_groups"]
        )
        return math.sqrt(proxy * empirical)

    def observe(self, family, level, reward):
        if not math.isfinite(reward) or not 0 <= reward <= 1:
            raise ValueError("Reward must be finite and bounded")
        with self.lock:
            cell = self.cells[family, level]
            # Discount old evidence as the policy improves; retain a Beta(1,1) prior.
            passed = reward >= 1 - 1e-9
            cell["success"] = 1 + self.decay * (cell["success"] - 1) + passed
            cell["failure"] = 1 + self.decay * (cell["failure"] - 1) + (not passed)
            cell["n"] += 1
            cell["reward_sum"] += reward
            reward_bin = round(3 * reward)
            cell["reward_counts"] = [
                prior + self.decay * (count - prior) + (i == reward_bin)
                for i, (count, prior) in enumerate(
                    zip(cell["reward_counts"], self.reward_prior)
                )
            ]

    @staticmethod
    def mixed_group_score(cell):
        total = sum(cell["reward_counts"])
        # P(non-unanimous actual reward) for four independent candidates. For
        # binary rewards this reduces to 1-p^4-(1-p)^4, maximized at p=1/2.
        return 1 - sum((count / total) ** 4 for count in cell["reward_counts"])

    def optimization(self):
        with self.lock:
            cells = {
                f: {
                    str(level): {
                        "reward_mean": sum(
                            i / 3 * n
                            for i, n in enumerate(self.cells[f, level]["reward_counts"])
                        )
                        / sum(self.cells[f, level]["reward_counts"]),
                        "mixed_group_probability": self.learnability(
                            self.cells[f, level]
                        ),
                    }
                    for level in (1, 2, 3)
                }
                for f in self.families
            }
            per_family = {
                f: optimize({f: levels}, floor=self.exploration / 3, temperature=0.25)
                for f, levels in cells.items()
            }
            weights = {
                f: report["level_weights"][f] for f, report in per_family.items()
            }
            count = len(self.families)
            mean = sum(r["predicted_reward_mean"] for r in per_family.values()) / count
            return {
                "target_reward_mean": 0.5,
                "target_feasible": all(
                    r["target_feasible"] for r in per_family.values()
                ),
                "predicted_reward_mean": mean,
                "reward_mean_error": abs(mean - 0.5),
                "worst_domain_reward_mean_error": max(
                    r["reward_mean_error"] for r in per_family.values()
                ),
                "predicted_mixed_group_probability": sum(
                    r["predicted_mixed_group_probability"] for r in per_family.values()
                )
                / count,
                "family_weights": {f: 1 / count for f in self.families},
                "level_weights": weights,
                "per_family": per_family,
                "within_family_probability_floor": self.exploration / 3,
                "normalized_cell_entropy": entropy(
                    [w / count for levels in weights.values() for w in levels.values()]
                )
                / math.log(3 * count),
                "note": "Each domain targets 0.5 independently; infeasible domains require redesign. Learnability combines a marginal proxy with smoothed same-instance group evidence when available. Predictions require fresh rollouts to validate.",
            }

    def weights(self, family):
        return list(self.optimization()["level_weights"][family].values())

    def choose(self, family, rng: random.Random):
        return rng.choices([1, 2, 3], weights=self.weights(family))[0]

    def choose_balanced(self, family, rng: random.Random, block_size=8):
        """Guarantee all levels in each block of new live problem instances."""
        if block_size < 3:
            raise ValueError("A coverage block needs at least three instances")
        with self.lock:
            if not self.bags[family]:
                expected = [block_size * w for w in self.weights(family)]
                counts = [max(1, int(n)) for n in expected]
                while sum(counts) < block_size:
                    order = list(range(3))
                    rng.shuffle(order)
                    index = max(order, key=lambda i: expected[i] - counts[i])
                    counts[index] += 1
                while sum(counts) > block_size:
                    available = [i for i in range(3) if counts[i] > 1]
                    index = min(available, key=lambda i: expected[i] - counts[i])
                    counts[index] -= 1
                self.bags[family] = [
                    level
                    for level, count in zip([1, 2, 3], counts)
                    for _ in range(count)
                ]
                rng.shuffle(self.bags[family])
            return self.bags[family].pop()

    def snapshot(self):
        with self.lock:
            return {
                f: {
                    str(level): {
                        **self.cells[f, level],
                        "success_rate": self.cells[f, level]["success"]
                        / (
                            self.cells[f, level]["success"]
                            + self.cells[f, level]["failure"]
                        ),
                        "weight": self.weights(f)[level - 1],
                        "posterior_reward_mean": sum(
                            i / 3 * n
                            for i, n in enumerate(self.cells[f, level]["reward_counts"])
                        )
                        / sum(self.cells[f, level]["reward_counts"]),
                        "mixed_reward_group_probability": self.mixed_group_score(
                            self.cells[f, level]
                        ),
                    }
                    for level in (1, 2, 3)
                }
                for f in self.families
            }
