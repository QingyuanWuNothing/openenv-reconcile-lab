"""Private, independently tested scheduling redesign; not in the frozen run."""

import random

from .scenarios import Office, overlap


class OfficeChallenge(Office):
    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        rng = random.Random(seed ^ 271828)
        heldout = split == "holdout"
        people = ["lee", "sam", "ari", "jo"] + (["ren", "ash"] if heldout else [])
        names = ["briefing", "review", "approval", "delivery", "archive", "handoff"]
        count = level + (3 if heldout else 2)
        rng.shuffle(names)
        grid = 20 if heldout else 15
        day_end = 720 if heldout else 480
        # Construct only to guarantee feasibility, then discard this witness.
        # Neither checks nor observations refer to a particular reference schedule.
        witness = []
        meetings = []
        for i in range(count):
            start = 60 + i * 100 if heldout else 45 + i * 75
            duration = rng.choice([40, 60, 80] if heldout else [30, 45, 60])
            attendees = rng.sample(
                people,
                (4 if heldout else 3) if level == 3 and rng.random() < 0.5 else 2,
            )
            room = "large" if len(attendees) > 2 or i % 2 else "small"
            witness.append(
                dict(
                    id=names[i],
                    start=start,
                    end=start + duration,
                    room=room,
                    attendees=attendees,
                )
            )
            pad = rng.choice([40, 60, 80] if heldout else [30, 45, 60])
            meetings.append(
                dict(
                    id=names[i],
                    duration=duration,
                    attendees=attendees,
                    earliest=max(0, start - pad),
                    latest=min(day_end, start + duration + pad),
                )
            )
        precedence = [
            [names[i], names[j]]
            for i in range(count)
            for j in range(i + 1, count)
            if rng.random() < (0.25 if level == 1 else 0.45)
        ]
        if count >= 4:
            precedence = list(
                {tuple(edge) for edge in precedence}
                | {(names[0], names[2]), (names[1], names[2]), (names[2], names[3])}
            )
            precedence = [list(edge) for edge in sorted(precedence)]
        busy = []
        for person in people:
            starts = list(range(0, day_end - 2 * grid, grid))
            rng.shuffle(starts)
            for start in starts:
                if sum(b["person"] == person for b in busy) >= level + 1:
                    break
                if not any(
                    person in m["attendees"]
                    and overlap(start, start + 2 * grid, m["start"], m["end"])
                    for m in witness
                ):
                    busy.append(dict(person=person, start=start, end=start + 2 * grid))
        rooms = [
            dict(id="small", capacity=3 if heldout else 2, maintenance=[]),
            dict(id="large", capacity=4 if heldout else 3, maintenance=[]),
        ]
        for room in rooms:
            starts = list(range(0, day_end - 2 * grid, grid))
            rng.shuffle(starts)
            for start in starts:
                if len(room["maintenance"]) >= level:
                    break
                if not any(
                    m["room"] == room["id"]
                    and overlap(start, start + 2 * grid, m["start"], m["end"])
                    for m in witness
                ):
                    room["maintenance"].append(dict(start=start, end=start + 2 * grid))
        rng.shuffle(meetings)
        self.resources = {
            "brief": {
                "meetings": meetings,
                "precedence": precedence,
                "day": [0, day_end],
                "time_grid": grid,
                "requirement": "Schedule all meetings inside their windows, preserve durations and attendee sets, respect every dependency, capacity, busy interval and maintenance interval; dispatch notifications for the final tested schedule. Input order is not dependency order.",
            },
            "rooms": rooms,
            "busy": busy,
            "bookings": [],
        }


class OfficeIncremental(OfficeChallenge):
    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        self.instruction = "Complete this scheduling workflow using short incremental actions. Inspect the brief, rooms and busy calendar. Create or replace one booking per action using patch target booking; inspect bookings and run calendar to find conflicts, then revise a booking if needed. Input order is not dependency order. After all meetings pass calendar checks, run dispatch and commit actual notifications. Reply with one action at a time."
        self.tools["patch"] = {
            "booking": "params={id,start,end,room,attendees}; upserts one meeting, preserving other bookings; returns the current booking and calendar diagnostics",
            "bookings": "params={bookings:[{id,start,end,room,attendees},...]}; optionally replace the full list",
        }

    def patch(self, target, params):
        if target != "booking":
            return super().patch(target, params)
        if set(params) != {"id", "start", "end", "room", "attendees"}:
            raise ValueError("Provide a complete single booking")
        if params["id"] not in {m["id"] for m in self.resources["brief"]["meetings"]}:
            raise ValueError("Use a meeting ID from the brief")
        rows = [r for r in self.resources["bookings"] if r["id"] != params["id"]]
        super().patch("bookings", {"bookings": rows + [params]})
        issues, order = self.diagnostics()
        return {
            "booking": self.inspect("bookings")[-1],
            "issues": issues[:12],
            "ordering_valid": order,
            "version": self.version,
        }
