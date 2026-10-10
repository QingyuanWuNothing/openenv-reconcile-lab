FAMILIES = ("code", "industrial", "science", "office", "finance", "math", "security", "media")
TRAIN_TASKS = [
    {"task_id": f"{f}-adaptive", "family": f, "split": "train"} for f in FAMILIES
]
CALIBRATION_TASKS = [
    {"task_id": f"{f}-l{level}", "family": f, "level": level}
    for f in FAMILIES
    for level in (1, 2, 3)
]
