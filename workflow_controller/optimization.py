"""Dependency-free curriculum optimization with explicit coverage constraints."""

import math


def entropy(probabilities):
    return -sum(p * math.log(p) for p in probabilities if p > 0)


def optimize(cells, target=0.5, floor=0.10, temperature=0.12):
    """Maximize within-cell mixed rewards and entropy at the feasible target mean.

    Family quotas are equal. Each level has a probability floor within its
    family. A Lagrange multiplier tilts entropy-regularized weights towards the
    requested reward mean. Unattainable targets are explicitly marked.
    Input cells must contain empirical/posterior reward means and mixed-reward
    probabilities; neither reward values nor verifier semantics are modified.
    """
    if not cells or not 0 <= target <= 1 or temperature <= 0:
        raise ValueError("Invalid optimization inputs")
    for levels in cells.values():
        if not levels or not 0 <= floor < 1 / len(levels):
            raise ValueError("Coverage floor leaves no allocatable probability")
        for c in levels.values():
            if any(
                not math.isfinite(c[k]) or not 0 <= c[k] <= 1
                for k in ["reward_mean", "mixed_group_probability"]
            ):
                raise ValueError("Unscorable cells cannot enter the optimizer")

    def boundary(family, upper):
        means = [c["reward_mean"] for c in cells[family].values()]
        remainder = 1 - floor * len(means)
        return floor * sum(means) + remainder * (max(means) if upper else min(means))

    low = sum(boundary(f, False) for f in cells) / len(cells)
    high = sum(boundary(f, True) for f in cells) / len(cells)
    feasible_target = min(high, max(low, target))

    def allocation(multiplier):
        weights = {}
        for family, levels in cells.items():
            logits = [
                (c["mixed_group_probability"] - multiplier * c["reward_mean"])
                / temperature
                for c in levels.values()
            ]
            maximum = max(logits)
            values = [math.exp(x - maximum) for x in logits]
            total = sum(values)
            remainder = 1 - len(values) * floor
            weights[family] = dict(
                zip(levels, [floor + remainder * x / total for x in values])
            )
        mean = sum(
            weights[f][level] * c["reward_mean"]
            for f, levels in cells.items()
            for level, c in levels.items()
        ) / len(cells)
        return mean, weights

    left, right = -1.0, 1.0
    while allocation(left)[0] < feasible_target - 1e-10 and abs(left) < 1e8:
        left *= 2
    while allocation(right)[0] > feasible_target + 1e-10 and right < 1e8:
        right *= 2
    for _ in range(100):
        middle = (left + right) / 2
        if allocation(middle)[0] > feasible_target:
            left = middle
        else:
            right = middle
    mean, weights = allocation((left + right) / 2)
    return {
        "target_reward_mean": target,
        "feasible_reward_mean_interval": [low, high],
        "target_feasible": low - 1e-9 <= target <= high + 1e-9,
        "predicted_reward_mean": mean,
        "reward_mean_error": abs(mean - target),
        "predicted_mixed_group_probability": sum(
            weights[f][level] * c["mixed_group_probability"]
            for f, levels in cells.items()
            for level, c in levels.items()
        )
        / len(cells),
        "family_weights": {f: 1 / len(cells) for f in cells},
        "level_weights": weights,
        "within_family_probability_floor": floor,
        "normalized_cell_entropy": entropy(
            [w / len(cells) for levels in weights.values() for w in levels.values()]
        )
        / math.log(sum(len(levels) for levels in cells.values()))
        if sum(len(levels) for levels in cells.values()) > 1
        else 1.0,
        "note": "Prediction from calibration evidence, not a fresh rollout measurement. Mixed-group probabilities assume independent candidates for the same cell.",
    }
