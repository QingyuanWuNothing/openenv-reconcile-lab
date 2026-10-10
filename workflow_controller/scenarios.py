"""Mutable simulated workspaces and outcome predicates, deployed separately."""

import copy
import random
import re


def integer(x):
    return isinstance(x, int) and not isinstance(x, bool)


class Scenario:
    family = ""

    def __init__(self, seed, level, split="train"):
        self.rng = random.Random(seed)
        self.level, self.split = level, split
        self.version, self.receipt_version = 0, -1
        self.artifact = None

    def patch(self, target, params):
        raise NotImplementedError

    def inspect(self, target):
        if target not in self.resources:
            raise ValueError("Unknown resource; inspect a name listed in resources")
        return copy.deepcopy(self.resources[target])

    def fresh(self):
        return self.artifact is not None and self.receipt_version == self.version

    def result(self):
        predicates = self.checks()
        # A fresh process output is a necessary gate, not a bonus for clicking run.
        if not self.fresh():
            predicates = {name: False for name in predicates}
        # All constraints are necessary for a completed workflow. Keep each
        # diagnostic, but reward only a fresh artifact satisfying every one.
        return float(bool(predicates) and all(predicates.values())), predicates


class Industrial(Scenario):
    family = "industrial"

    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        self.base = (
            self.rng.choice([14, 18, 22, 26])
            if split == "train"
            else self.rng.choice([15, 19, 23, 27])
        )
        self.resources = {
            "plant": {
                "rpm": 0.6,
                "bypass": 0.4 if level > 1 else 0.1,
                "filter_resistance": 1.2,
                "cooling": False if level > 2 else True,
            },
            "manual": {
                "pressure": f"{self.base} * rpm^2 * (1-bypass) / (1+filter_resistance)",
                "flow": "12 * rpm * (1-bypass) / (1+filter_resistance)",
                "temperature": "22 + 45*rpm - (20 if cooling else 0)",
                "stress": "At each load, pressure scales by load^pressure_load_exponent; flow scales by load^flow_load_exponent; temperature increases by temperature_load_gain*(load-1). Read this instance's exponents and gain; they vary between cases.",
                "pressure_load_exponent": self.rng.choice([0.7, 1.0])
                if split == "train" and level > 1
                else 1.0
                if split == "train"
                else 0.85,
                "flow_load_exponent": self.rng.choice([0.4, 1.0])
                if split == "train" and level > 1
                else 1.0
                if split == "train"
                else -0.5,
                "temperature_load_gain": self.rng.choice([0, 4])
                if split == "train" and level > 1
                else 0
                if split == "train"
                else 8,
                "limits": {
                    "pressure": [[6, 12], [8, 12], [9, 12]][level - 1],
                    "flow_min": 5 if level == 1 else 6,
                    "temperature_max": [70, 55, 50][level - 1],
                },
                "valid_settings": {
                    "rpm": [0.4, 1.6],
                    "bypass": [0, 0.6],
                    "filter_resistance": [0.1, 2],
                    "cooling": "boolean",
                },
                "load_tests": [0.9, 1.0, 1.1]
                if split == "train"
                else [0.88, 0.97, 1.05, 1.12],
            },
        }
        self.instruction = "Restore this simulated pumping line. Read the manual and plant settings, diagnose low delivery, change settings, then run the line to verify recovery across all specified load tests. Meet pressure, flow and temperature limits without deleting or relaxing requirements. Several repairs are valid. Commit the tested configuration."
        self.tools = {
            "inspect": ["plant", "manual"],
            "patch": {
                "plant": "params is a subset of rpm, bypass, filter_resistance, cooling"
            },
            "run": {
                "plant": "params={} runs all specified load tests; returns pressure, flow and temperature"
            },
        }

    def patch(self, target, params):
        if (
            target != "plant"
            or not params
            or set(params) - set(self.resources["plant"])
        ):
            raise ValueError("Patch plant settings only")
        limits = self.resources["manual"]["valid_settings"]
        for key, value in params.items():
            if key == "cooling":
                if not isinstance(value, bool):
                    raise ValueError("cooling must be boolean")
            elif (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not limits[key][0] <= value <= limits[key][1]
            ):
                raise ValueError("Setting outside its engineering limits")
        self.resources["plant"].update(params)
        self.version += 1
        return self.inspect("plant")

    def run(self, target, params):
        if target != "plant" or params:
            raise ValueError("Run plant with params={}")
        p = self.resources["plant"]
        self.artifact = [
            {
                "load": load,
                "pressure": round(
                    self.base
                    * p["rpm"] ** 2
                    * (1 - p["bypass"])
                    / (1 + p["filter_resistance"])
                    * load ** self.resources["manual"]["pressure_load_exponent"],
                    4,
                ),
                "flow": round(
                    12
                    * p["rpm"]
                    * (1 - p["bypass"])
                    / (1 + p["filter_resistance"])
                    * load ** self.resources["manual"]["flow_load_exponent"],
                    4,
                ),
                "temperature": round(
                    22
                    + 45 * p["rpm"]
                    - (20 if p["cooling"] else 0)
                    + self.resources["manual"]["temperature_load_gain"] * (load - 1),
                    4,
                ),
            }
            for load in self.resources["manual"]["load_tests"]
        ]
        self.receipt_version = self.version
        return {
            "measurements": copy.deepcopy(self.artifact),
            "configuration_version": self.version,
        }

    def checks(self):
        rows = self.artifact or []
        limits = self.resources["manual"]["limits"]
        count = len(self.resources["manual"]["load_tests"])
        return {
            "pressure_recovers": len(rows) == count
            and all(
                limits["pressure"][0] <= r["pressure"] <= limits["pressure"][1]
                for r in rows
            ),
            "delivery_recovers": len(rows) == count
            and all(r["flow"] >= limits["flow_min"] for r in rows),
            "temperature_safe": len(rows) == count
            and all(r["temperature"] <= limits["temperature_max"] for r in rows),
        }


class Security(Scenario):
    family = "security"

    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        teams = ["birch", "cedar"] if split == "train" else ["maple", "willow", "ash"]
        principals = [
            {"name": f"staff_{team}", "role": "staff", "team": team} for team in teams
        ] + [
            {"name": "visitor", "role": "guest", "team": "none"},
            {"name": "auditor", "role": "auditor", "team": "none"},
        ]
        resources = [
            {"name": f"notes_{team}", "kind": "private", "team": team} for team in teams
        ] + [
            {"name": "homepage", "kind": "public", "team": "none"},
            {"name": "audit_log", "kind": "audit", "team": "none"},
        ]
        if level == 3:
            resources += [{"name": "quarantine", "kind": "sealed", "team": teams[0]}]
        for p in principals:
            p["active"] = True
            p["write_approved"] = level < 3 or self.rng.choice([True, False])
            p["device_trusted"] = level < 3 or self.rng.choice([True, False])
            p["clearance"] = 3 if level == 1 else self.rng.randrange(4)
        for r in resources:
            r["classification"] = (
                0 if level == 1 else self.rng.randrange(3 if split == "train" else 4)
            )
        if level >= 2:
            principals.append(
                {
                    "name": "suspended",
                    "role": "staff",
                    "team": teams[0],
                    "active": False,
                    "write_approved": True,
                    "device_trusted": True,
                    "clearance": 3,
                }
            )
            if split == "holdout":
                principals += [
                    {
                        "name": "inactive_auditor",
                        "role": "auditor",
                        "team": "none",
                        "active": False,
                        "write_approved": True,
                        "device_trusted": True,
                        "clearance": 3,
                    },
                    {
                        "name": "external_staff",
                        "role": "staff",
                        "team": "external",
                        "active": True,
                        "write_approved": True,
                        "device_trusted": True,
                        "clearance": 3,
                    },
                ]
        public_roles = ["staff", "guest", "auditor"]
        if level > 1:
            public_roles.remove(self.rng.choice(["guest", "auditor"]))
        self.resources = {
            "principals": principals,
            "resources": resources,
            "policy": [{"role": "*", "kind": "*", "method": "*", "effect": "allow"}],
            "requirements": {
                "public_read_roles": public_roles,
                "staff": "May read/write private resources of their own team only, and only if principal clearance >= resource classification.",
                "guest": "Public read only if guest is listed in public_read_roles.",
                "auditor": "May read audit resources. Public read only if auditor is listed in public_read_roles.",
                "all": "Public read is permitted exactly for the roles in public_read_roles. Inactive principals must be denied every request. Private writes additionally require write_approved=true AND device_trusted=true. Every other request must be denied, including sealed resources and public writes.",
                "evaluation": "First matching rule wins; unmatched requests are denied. Fields: role, kind, method, effect (allow/deny), optional own_team, active, write_approved, device_trusted and clearance_ok booleans. active/write_approved/device_trusted match principal attributes; own_team=true requires matching teams; clearance_ok=true requires principal clearance >= resource classification (false requires the opposite). '*' is a wildcard.",
            },
        }
        self.instruction = "Repair this deliberately vulnerable access-policy sandbox. Inspect principals, resources and requirements. Replace the overbroad policy while preserving required access. Run requests to inspect allowed and denied traffic, revise if needed, and commit a freshly tested policy."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "policy": "params={rules:[{role,kind,method,effect,own_team?,active?,write_approved?,device_trusted?,clearance_ok?},...]}; at most 12 rules"
            },
            "run": {
                "requests": "params={} exercises the complete principal/resource/method matrix, returning observed decisions"
            },
        }

    def patch(self, target, params):
        rules = params.get("rules")
        if (
            target != "policy"
            or set(params) != {"rules"}
            or not isinstance(rules, list)
            or not 1 <= len(rules) <= 12
        ):
            raise ValueError("Replace policy with 1–12 rules")
        for r in rules:
            if (
                not isinstance(r, dict)
                or not {"role", "kind", "method", "effect"} <= set(r)
                or set(r)
                - {
                    "role",
                    "kind",
                    "method",
                    "effect",
                    "own_team",
                    "active",
                    "write_approved",
                    "device_trusted",
                    "clearance_ok",
                }
            ):
                raise ValueError("Malformed policy rule")
            if (
                r["role"] not in ["*", "staff", "guest", "auditor"]
                or r["kind"] not in ["*", "private", "public", "audit", "sealed"]
                or r["method"] not in ["*", "read", "write"]
                or r["effect"] not in ["allow", "deny"]
                or any(
                    k in r and not isinstance(r[k], bool)
                    for k in [
                        "own_team",
                        "active",
                        "write_approved",
                        "device_trusted",
                        "clearance_ok",
                    ]
                )
            ):
                raise ValueError("Unknown rule value")
        self.resources["policy"] = copy.deepcopy(rules)
        self.version += 1
        return {"rules": len(rules), "version": self.version}

    def allowed(self, principal, resource, method):
        for r in self.resources["policy"]:
            if (
                r["role"] not in ["*", principal["role"]]
                or r["kind"] not in ["*", resource["kind"]]
                or r["method"] not in ["*", method]
            ):
                continue
            if r.get("own_team") and principal["team"] != resource["team"]:
                continue
            if any(
                k in r and r[k] != principal[k]
                for k in ["active", "write_approved", "device_trusted"]
            ):
                continue
            if "clearance_ok" in r and r["clearance_ok"] != (
                principal["clearance"] >= resource["classification"]
            ):
                continue
            return r["effect"] == "allow"
        return False

    def required(self, p, r, method):
        if not p["active"]:
            return False
        if r["kind"] == "private" and p["clearance"] < r["classification"]:
            return False
        if (
            r["kind"] == "private"
            and method == "write"
            and (not p["write_approved"] or not p["device_trusted"])
        ):
            return False
        return (
            (
                r["kind"] == "public"
                and method == "read"
                and p["role"] in self.resources["requirements"]["public_read_roles"]
            )
            or (
                p["role"] == "staff"
                and r["kind"] == "private"
                and p["team"] == r["team"]
            )
            or (p["role"] == "auditor" and r["kind"] == "audit" and method == "read")
        )

    def run(self, target, params):
        if target != "requests" or params:
            raise ValueError("Run requests with params={}")
        self.artifact = [
            {
                "principal": p["name"],
                "resource": r["name"],
                "method": m,
                "allowed": self.allowed(p, r, m),
            }
            for p in self.resources["principals"]
            for r in self.resources["resources"]
            for m in ["read", "write"]
        ]
        self.receipt_version = self.version
        # Summarize per category so observation budgets stay bounded.
        return {
            "decisions": self.artifact[:24],
            "total_requests": len(self.artifact),
            "truncated": len(self.artifact) > 24,
            "note": "Run reflects actual policy decisions; inspect policy/requirements to audit other combinations.",
        }

    def checks(self):
        checks = {
            "required_access_preserved": True,
            "unauthorized_access_blocked": True,
            "writes_restricted": True,
        }
        for p in self.resources["principals"]:
            for r in self.resources["resources"]:
                for m in ["read", "write"]:
                    actual, wanted = self.allowed(p, r, m), self.required(p, r, m)
                    if wanted and not actual:
                        checks["required_access_preserved"] = False
                    if not wanted and actual:
                        checks["unauthorized_access_blocked"] = False
                    if m == "write" and actual != wanted:
                        checks["writes_restricted"] = False
        return checks


def overlap(a, b, c, d):
    return max(a, c) < min(b, d)


class Office(Scenario):
    family = "office"

    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        names = (
            ["prepare", "review", "handoff", "archive"]
            if split == "train"
            else ["draft", "approve", "publish", "close"]
        )
        meetings = [
            {
                "id": names[i],
                "duration": self.rng.choice([30, 60] if split == "train" else [45, 60]),
                "attendees": self.rng.sample(
                    ["lee", "sam", "ari"],
                    3 if level == 3 and self.rng.random() < 0.5 else 2,
                ),
                "earliest": i * 120 if level > 1 else 0,
                "latest": (i + 1) * 120 if level > 1 else 480,
            }
            for i in range(level + 1)
        ]
        busy = []
        for person in ["lee", "sam", "ari"]:
            for start in [90, 270, 390]:
                # Reference-free feasibility: leave broad known windows, not a stored schedule.
                if self.rng.random() < 0.6:
                    busy.append({"person": person, "start": start, "end": start + 30})
        self.resources = {
            "brief": {
                "meetings": meetings,
                "precedence": [
                    [meetings[i]["id"], meetings[i + 1]["id"]]
                    for i in range(len(meetings) - 1)
                ],
                "day": [0, 480],
                "time_grid": 30 if split == "train" else 15,
                "requirement": "Schedule all meetings inside each earliest/latest window, preserve duration and attendee set, avoid room/attendee overlaps, participant busy intervals and room maintenance, then dispatch notifications for the tested schedule.",
            },
            "rooms": [
                {"id": "small", "capacity": 2, "maintenance": []},
                {
                    "id": "large",
                    "capacity": 4 if split == "train" else 3,
                    "maintenance": [
                        {"start": x, "end": x + 30} for x in [0, 150, 240, 360]
                    ]
                    if level == 3
                    else [],
                },
            ],
            "busy": busy,
            "bookings": [],
        }
        if split == "holdout" and level == 3:
            # A branching dependency graph and shuffled input order are new
            # structures; solving a memorized chronological chain is insufficient.
            meetings[0]["latest"] = 240
            meetings[1]["earliest"] = 0
            self.resources["brief"]["precedence"] = [
                [names[0], names[2]],
                [names[1], names[2]],
                [names[2], names[3]],
            ]
            self.rng.shuffle(meetings)
        self.instruction = "Complete the meeting workflow from the brief and calendars. Inspect the inputs, write bookings, run calendar checks, fix violations, then dispatch actual notifications. Commit the resulting calendar and notifications. Merely creating a bookings list is insufficient."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "bookings": "params={bookings:[{id,start,end,room,attendees},...]}; minutes are integers"
            },
            "run": {
                "calendar": "params={} checks overlaps, durations, capacities and ordering",
                "dispatch": "params={} creates notification records for the current bookings",
            },
        }

    def patch(self, target, params):
        rows = params.get("bookings")
        if (
            target != "bookings"
            or set(params) != {"bookings"}
            or not isinstance(rows, list)
            or len(rows) > 8
        ):
            raise ValueError("Patch bookings only")
        for r in rows:
            if (
                not isinstance(r, dict)
                or set(r) != {"id", "start", "end", "room", "attendees"}
                or not integer(r["start"])
                or not integer(r["end"])
                or not isinstance(r["attendees"], list)
                or any(not isinstance(x, str) for x in r["attendees"])
                or not isinstance(r["id"], str)
                or not isinstance(r["room"], str)
            ):
                raise ValueError("Malformed booking")
        self.resources["bookings"] = copy.deepcopy(rows)
        self.version += 1
        return {"bookings": len(rows), "version": self.version}

    def diagnostics(self):
        rows = self.resources["bookings"]
        brief = self.resources["brief"]
        expected = {m["id"]: m for m in brief["meetings"]}
        rooms = {r["id"]: r["capacity"] for r in self.resources["rooms"]}
        maintenance = {r["id"]: r["maintenance"] for r in self.resources["rooms"]}
        issues = []
        if len(rows) != len(expected) or {r["id"] for r in rows} != set(expected):
            issues.append("meeting coverage or duplicate IDs")
        for r in rows:
            m = expected.get(r["id"])
            if (
                not m
                or r["end"] - r["start"] != m["duration"]
                or set(r["attendees"]) != set(m["attendees"])
                or len(r["attendees"]) != len(set(r["attendees"]))
                or (m and not m["earliest"] <= r["start"] < r["end"] <= m["latest"])
            ):
                issues.append("meeting requirements: " + r["id"])
            if (
                r["room"] not in rooms
                or len(r["attendees"]) > rooms.get(r["room"], 0)
                or not brief["day"][0] <= r["start"] < r["end"] <= brief["day"][1]
                or r["start"] % brief["time_grid"]
                or r["end"] % brief["time_grid"]
            ):
                issues.append("room/time constraints: " + r["id"])
            if any(
                overlap(r["start"], r["end"], b["start"], b["end"])
                for b in maintenance.get(r["room"], [])
            ):
                issues.append("room maintenance: " + r["id"])
            for b in self.resources["busy"]:
                if b["person"] in r["attendees"] and overlap(
                    r["start"], r["end"], b["start"], b["end"]
                ):
                    issues.append("busy attendee: " + r["id"])
        for i, a in enumerate(rows):
            for b in rows[i + 1 :]:
                if (
                    a["room"] == b["room"] or set(a["attendees"]) & set(b["attendees"])
                ) and overlap(a["start"], a["end"], b["start"], b["end"]):
                    issues.append("booking overlap")
        mapping = {r["id"]: r for r in rows}
        order = all(
            a in mapping and b in mapping and mapping[a]["end"] <= mapping[b]["start"]
            for a, b in brief["precedence"]
        )
        if not order:
            issues.append("precedence")
        return issues, order

    def run(self, target, params):
        if params or target not in ["calendar", "dispatch"]:
            raise ValueError("Run calendar or dispatch with params={}")
        issues, order = self.diagnostics()
        if target == "dispatch":
            self.artifact = {
                "calendar": copy.deepcopy(self.resources["bookings"]),
                "notifications": [
                    {
                        "meeting": r["id"],
                        "recipient": p,
                        "start": r["start"],
                        "end": r["end"],
                    }
                    for r in self.resources["bookings"]
                    for p in r["attendees"]
                ],
            }
            self.receipt_version = self.version
        return {
            "issues": issues[:12],
            "ordering_valid": order,
            "dispatched": target == "dispatch",
            "version": self.version,
        }

    def checks(self):
        issues, order = self.diagnostics()
        artifact = self.artifact or {}
        rows = self.resources["bookings"]
        wanted = [
            {"meeting": r["id"], "recipient": p, "start": r["start"], "end": r["end"]}
            for r in rows
            for p in r["attendees"]
        ]
        return {
            "calendar_feasible": not any(i != "precedence" for i in issues),
            "precedence_respected": order and bool(rows),
            "notifications_match": bool(rows)
            and artifact.get("calendar") == rows
            and artifact.get("notifications") == wanted,
        }


class Media(Scenario):
    family = "media"

    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        subjects = (
            ["The orchard team", "The river crew", "The gallery staff"]
            if split == "train"
            else ["The workshop team", "The garden crew", "The museum staff"]
        )
        fps = self.rng.choice([24, 30] if split == "train" else [25, 50])
        segments = []
        anchors = {}
        for i in range(1, level + 2):
            subject = self.rng.choice(subjects)
            core = subject + " opens the new exhibition for local artists today"
            text = core + " today today" if level > 1 else core
            start = (i - 1) * 5 * fps
            end = start + 4 * fps
            segments.append(
                {
                    "id": f"c{i}",
                    "start_frame": start - (fps if i == 1 else 0),
                    "end_frame": end + (3 * fps if level > 2 else 0),
                    "text": text,
                }
            )
            anchors[f"c{i}"] = [subject.split()[1], "opens", "exhibition", "artists"]
        self.resources = {
            "brief": {
                "fps": fps,
                "duration_frames": (level + 1) * 5 * fps,
                "max_characters": [76, 58, 49][level - 1],
                "min_duration_frames": fps,
                "max_duration_frames": 5 * fps,
                "required_words": anchors,
                "cue_windows": {
                    r["id"]: [
                        (i * 5 * fps + (fps + 1) // 2),
                        (i * 5 + 4) * fps + fps // 2,
                    ]
                    for i, r in enumerate(segments)
                }
                if level > 1
                else {},
                "editing": "Preserve at least 70% of each source caption's DISTINCT words, including all required words. Text must be an ordered subsequence of the source words: trim repetitions or optional words, never reorder or add words. Keep caption IDs and order. Captions must be non-overlapping and inside the media duration. If cue_windows is nonempty, each caption must be wholly inside its own frame window.",
            },
            "segments": segments,
            "source_text": {r["id"]: r["text"] for r in segments},
        }
        if split == "holdout" and level > 1:
            # Nonuniform cue windows break the training set's five-second stride.
            for i, segment in enumerate(segments):
                lo = i * 5 * fps + self.rng.choice([fps, 3 * fps // 2, 2 * fps])
                hi = lo + self.rng.choice([fps, 2 * fps])
                self.resources["brief"]["cue_windows"][segment["id"]] = [lo, hi]
        self.instruction = "Repair this caption asset to the production brief. Inspect source and segments, fix time ranges and trim text without changing the facts, then render an actual SRT artifact and inspect its diagnostics. Commit the rendered asset. Changing metadata alone or skipping render earns no reward."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "segments": "params={segments:[{id,start_frame,end_frame,text},...]}; replace the full list"
            },
            "run": {
                "render": "params={} serializes caption text and timestamps into SRT and checks the result"
            },
        }

    def patch(self, target, params):
        rows = params.get("segments")
        if (
            target != "segments"
            or set(params) != {"segments"}
            or not isinstance(rows, list)
            or len(rows) > 8
        ):
            raise ValueError("Patch segments only")
        for r in rows:
            if (
                not isinstance(r, dict)
                or set(r) != {"id", "start_frame", "end_frame", "text"}
                or not integer(r["start_frame"])
                or not integer(r["end_frame"])
                or not isinstance(r["text"], str)
                or not isinstance(r["id"], str)
                or len(r["text"]) > 200
            ):
                raise ValueError("Malformed caption")
        self.resources["segments"] = copy.deepcopy(rows)
        self.version += 1
        return {"segments": len(rows), "version": self.version}

    def timestamp(self, frame):
        ms = round(frame * 1000 / self.resources["brief"]["fps"])
        h, rest = divmod(ms, 3600000)
        m, rest = divmod(rest, 60000)
        sec, ms = divmod(rest, 1000)
        return f"{h:02}:{m:02}:{sec:02},{ms:03}"

    def run(self, target, params):
        if target != "render" or params:
            raise ValueError("Run render with params={}")
        self.artifact = (
            "\n\n".join(
                f"{i}\n{self.timestamp(r['start_frame'])} --> {self.timestamp(r['end_frame'])}\n{r['text']}"
                for i, r in enumerate(self.resources["segments"], 1)
            )
            + "\n"
        )
        self.receipt_version = self.version
        return {"srt": self.artifact, "checks": self.checks(), "version": self.version}

    def checks(self):
        rows = self.resources["segments"]
        brief = self.resources["brief"]
        source = self.resources["source_text"]
        ids = [r["id"] for r in rows]
        expected = list(source)
        timing = ids == expected
        content = ids == expected
        technical = ids == expected and bool(self.artifact)
        previous = 0
        for r in rows:
            start, end = r["start_frame"], r["end_frame"]
            timing &= (
                0 <= start < end <= brief["duration_frames"]
                and start >= previous
                and brief["min_duration_frames"]
                <= end - start
                <= brief["max_duration_frames"]
            )
            previous = end
            if r["id"] in brief["cue_windows"]:
                lo, hi = brief["cue_windows"][r["id"]]
                timing &= lo <= start < end <= hi
            tokens = set(re.findall(r"\w+", r["text"].lower()))
            words = re.findall(r"\w+", r["text"].lower())
            source_words = iter(re.findall(r"\w+", source.get(r["id"], "").lower()))
            ordered = all(
                any(original_word == word for original_word in source_words)
                for word in words
            )
            original = set(re.findall(r"\w+", source.get(r["id"], "").lower()))
            content &= (
                bool(original)
                and ordered
                and tokens <= original
                and len(tokens) >= 0.7 * len(original)
                and all(
                    w.lower() in tokens
                    for w in brief["required_words"].get(r["id"], [])
                )
            )
            technical &= (
                0 < len(r["text"]) <= brief["max_characters"]
                and "\n" not in r["text"]
                and "\r" not in r["text"]
            )
        if self.artifact:
            blocks = self.artifact.strip().split("\n\n")
            technical &= len(blocks) == len(rows) and all(
                len(b.splitlines()) == 3
                and re.fullmatch(
                    r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}",
                    b.splitlines()[1],
                )
                for b in blocks
            )
        return {
            "timeline_valid": bool(timing),
            "content_preserved": bool(content),
            "rendered_format_valid": bool(technical),
        }


SCENARIOS = {c.family: c for c in [Industrial, Security, Office, Media]}
