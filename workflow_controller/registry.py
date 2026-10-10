"""Private next candidate; preserves easy anchors and adds measured redesigns."""

from .scenarios import Industrial
from .office_tasks import OfficeIncremental
from .finance_tasks import Finance
from .code_tasks import Software
from .science_tasks import Science
from .math_tasks import Mathematics
from .code_scheduling import CodeScheduling
from .media_incremental import MediaIncremental
from .security_incremental import SecurityIncremental
from .release_variants import ScienceEfficient, MathBridge, MediaBridge


def code(seed, level, split="train"):
    return (Software if level == 1 else CodeScheduling)(seed, level, split)


def science(seed, level, split="train"):
    return (Science if level == 1 else ScienceEfficient)(seed, level, split)


def mathematics(seed, level, split="train"):
    return (Mathematics if level == 1 else MathBridge)(seed, level, split)


def media(seed, level, split="train"):
    return (MediaIncremental if level == 1 else MediaBridge)(seed, level, split)


SCENARIOS = {
    "industrial": Industrial,
    "office": OfficeIncremental,
    "finance": Finance,
    "code": code,
    "science": science,
    "math": mathematics,
    "media": media,
    "security": SecurityIncremental,
}
