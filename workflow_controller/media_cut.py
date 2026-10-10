"""Private media redesign: retime captions through a real edit decision list."""

import copy
from fractions import Fraction
from .scenarios import Scenario
from .media_tasks import MediaWorkflow
from .numeric_tools import calculate


def nearest_frame(value):
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


class MediaCut(MediaWorkflow):
    def __init__(self, seed, level, split="train"):
        Scenario.__init__(self, seed, level, split)
        fps = self.rng.choice([24, 30] if split == "train" else [25, 50])
        tokens = (
            "Review the calibration before the next inspection and record every stable reading"
            if split == "train"
            else "Compare external instruments after each adjustment and document all remaining measurement differences"
        ).split()
        media = {}
        for asset in ["cameraA", "cameraB", "cameraC"]:
            source_fps = self.rng.choice([24, 30] if split == "train" else [25, 50])
            if level == 2 and split == "train":
                source_fps = fps
            words = [
                {"text": word, "start_frame": 10 + 18 * i, "end_frame": 20 + 18 * i}
                for i, word in enumerate(tokens)
            ]
            self.rng.shuffle(words)
            media[asset] = {"fps": source_fps, "words": words}
        edits = []
        for index in range((2 if level == 2 else level + 1) + (split == "holdout")):
            asset = self.rng.choice(list(media))
            start = self.rng.randint(0, 3)
            last = start + self.rng.randint(3, 5)
            speed = (
                self.rng.choice([[1, 1], [2, 1], [3, 2], [1, 2]])
                if level == 3
                else [1, 1]
            )
            edits.append(
                {
                    "id": f"cut-{index}",
                    "asset": asset,
                    "in_frame": 10
                    + 18 * start
                    + (5 if level == 3 and index % 2 else -3),
                    "out_frame": 20
                    + 18 * last
                    + (-5 if level == 3 and index % 3 == 1 else 3),
                    "speed": {"num": speed[0], "den": speed[1]},
                    "gap_after_frames": self.rng.randint(0, 8),
                }
            )
        self.rng.shuffle(edits)
        rule = "Create exactly one caption per edit, in edit-list order. Retain source words only when their ENTIRE interval is inside [in_frame,out_frame], and order them by source start. Drop partially cut words. Delivery starts at frame 0. Let ratio=delivery_fps*speed.den/(asset_fps*speed.num). Each edit occupies round_half_up((out_frame-in_frame)*ratio) delivery frames, followed by gap_after_frames. Its caption starts at edit delivery start + round_half_up((first retained word start-in_frame)*ratio), and ends similarly using the last retained word end. Round each relative boundary separately, then add the integer delivery start. Preserve retained words exactly and wrap at spaces into at most two lines, each <=max_characters_per_line. Use cut IDs as caption IDs. Source word order may be shuffled; the edit list order defines delivery. speed=2 means twice as fast. Configure the required format and delivery FPS, render, inspect and commit. Timestamps use nearest milliseconds."
        self.resources = {
            "brief": {
                "rule": rule,
                "fps": fps,
                "delivery_format": self.rng.choice(["srt", "vtt"]),
                "max_characters_per_line": 80 if level == 2 else 40,
                "max_lines": 2,
            },
            "source_media": media,
            "edit_list": edits,
            "segments": [],
            "rendering": {"format": "srt", "fps": 24},
        }
        self.instruction = "Edit a subtitle asset for a reordered and trimmed video timeline. Inspect the production brief, source word timings and edit decisions; retime the retained captions, configure delivery, render and inspect the real asset before committing."
        self.instruction += " First run assemble and inspect the resulting delivery timeline. The edit-list POSITION determines chronology; cut IDs are opaque labels. Assembly is required before final verification."
        self.instruction += " Use preview_cut for each cut to inspect chronological source word cards and full/partial selection; do not infer retained text from a sentence fragment or the shuffled raw word list."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "segment": "params={id,start_frame,end_frame,text}; upsert one caption, using cut ID; text may contain a newline between at most two wrapped lines",
                "rendering": "params={format:'srt'|'vtt',fps:integer}; match the brief",
            },
            "run": {
                "preview_cut": "params={id:cut ID}; inspect this source interval as chronological word cards with full/partial/outside selection status. Does not create a caption or compute delivery boundaries.",
                "assemble": "params={}; execute edit-list assembly and inspect clip order, delivery start, duration, source bounds and exact retiming ratio. List position defines delivery order; cut IDs do not define chronology.",
                "calculate": "params={expression:string,variables:{name:number or {num,den}}}; exact +,-,*,/, abs, ceil, floor, round_half_up; computes supplied numbers only",
                "render": "params={}; serialize captions and inspect technical/content/timeline diagnostics",
            },
        }
        self.resources["timeline"] = []
        self.tools["inspect"] = list(self.resources)

    def run(self, target, params):
        if target == "calculate":
            return calculate(params)
        if target == "preview_cut":
            if set(params) != {"id"}:
                raise ValueError("Preview one cut ID")
            edit = next(
                (r for r in self.resources["edit_list"] if r["id"] == params["id"]),
                None,
            )
            if edit is None:
                raise ValueError("Unknown cut ID")
            asset = self.resources["source_media"][edit["asset"]]
            cards = []
            for word in sorted(asset["words"], key=lambda w: w["start_frame"]):
                inside = (
                    edit["in_frame"] <= word["start_frame"]
                    and word["end_frame"] <= edit["out_frame"]
                )
                overlaps = (
                    word["start_frame"] < edit["out_frame"]
                    and word["end_frame"] > edit["in_frame"]
                )
                cards.append(
                    {
                        **word,
                        "selection": "full"
                        if inside
                        else "partial"
                        if overlaps
                        else "outside",
                    }
                )
            return {
                "id": edit["id"],
                "asset": edit["asset"],
                "source_fps": asset["fps"],
                "word_cards": cards,
                "note": "Source preview only. Keep full words in displayed chronological order; use the assembled timeline and production brief to retime, wrap and edit the caption.",
            }
        if target == "assemble":
            if params:
                raise ValueError("Assemble with empty params")
            position = 0
            timeline = []
            for ordinal, edit in enumerate(self.resources["edit_list"]):
                asset = self.resources["source_media"][edit["asset"]]
                ratio = Fraction(
                    self.resources["brief"]["fps"] * edit["speed"]["den"],
                    asset["fps"] * edit["speed"]["num"],
                )
                duration = nearest_frame((edit["out_frame"] - edit["in_frame"]) * ratio)
                timeline.append(
                    {
                        "list_position": ordinal,
                        "id": edit["id"],
                        "delivery_start_frame": position,
                        "duration_frames": duration,
                        "source_in_frame": edit["in_frame"],
                        "source_out_frame": edit["out_frame"],
                        "retiming_ratio": {
                            "num": ratio.numerator,
                            "den": ratio.denominator,
                        },
                    }
                )
                position += duration + edit["gap_after_frames"]
            self.resources["timeline"] = timeline
            return {
                "timeline": copy.deepcopy(timeline),
                "delivery_frames": position,
                "note": "Actual assembled edit timeline. Derive retained word content and word boundaries from source_media; use this delivery_start_frame for each matching cut ID.",
            }
        return MediaWorkflow.run(self, target, params)

    def patch(self, target, params):
        if target == "rendering":
            return MediaWorkflow.patch(self, target, params)
        if target != "segment" or set(params) != {
            "id",
            "start_frame",
            "end_frame",
            "text",
        }:
            raise ValueError("Upsert one complete caption")
        ids = [r["id"] for r in self.resources["edit_list"]]
        if (
            params["id"] not in ids
            or not isinstance(params["text"], str)
            or len(params["text"]) > 160
            or any(
                type(params[k]) is not int or not 0 <= params[k] <= 100000
                for k in ["start_frame", "end_frame"]
            )
        ):
            raise ValueError("Use a cut ID, integer delivery frames and bounded text")
        rows = {r["id"]: r for r in self.resources["segments"]}
        rows[params["id"]] = dict(params)
        self.resources["segments"] = [rows[i] for i in ids if i in rows]
        self.version += 1
        return {"segment": dict(params), "version": self.version}

    def wanted(self):
        start = 0
        rows = []
        for edit in self.resources["edit_list"]:
            asset = self.resources["source_media"][edit["asset"]]
            ratio = Fraction(
                self.resources["brief"]["fps"] * edit["speed"]["den"],
                asset["fps"] * edit["speed"]["num"],
            )
            words = sorted(
                [
                    w
                    for w in asset["words"]
                    if edit["in_frame"] <= w["start_frame"]
                    and w["end_frame"] <= edit["out_frame"]
                ],
                key=lambda w: w["start_frame"],
            )
            rows.append(
                {
                    "id": edit["id"],
                    "start_frame": start
                    + nearest_frame(
                        (words[0]["start_frame"] - edit["in_frame"]) * ratio
                    ),
                    "end_frame": start
                    + nearest_frame(
                        (words[-1]["end_frame"] - edit["in_frame"]) * ratio
                    ),
                    "words": [w["text"] for w in words],
                }
            )
            start += (
                nearest_frame((edit["out_frame"] - edit["in_frame"]) * ratio)
                + edit["gap_after_frames"]
            )
        return rows

    def checks(self):
        desired = self.wanted()
        rows = self.resources["segments"]
        brief = self.resources["brief"]
        settings = self.resources["rendering"]
        coverage = [r["id"] for r in rows] == [r["id"] for r in desired]
        content = coverage and all(
            row["text"].split() == want["words"] for row, want in zip(rows, desired)
        )
        timing = coverage and all(
            row["start_frame"] == want["start_frame"]
            and row["end_frame"] == want["end_frame"]
            for row, want in zip(rows, desired)
        )
        wrapping = bool(rows) and all(
            1 <= len(r["text"].splitlines()) <= brief["max_lines"]
            and all(
                0 < len(line) <= brief["max_characters_per_line"]
                for line in r["text"].splitlines()
            )
            for r in rows
        )
        config = settings == {"fps": brief["fps"], "format": brief["delivery_format"]}
        timeline = self.resources["timeline"]
        assembled = len(timeline) == len(self.resources["edit_list"])
        position = 0
        for index, edit in enumerate(self.resources["edit_list"]):
            if index >= len(timeline):
                break
            asset_source = self.resources["source_media"][edit["asset"]]
            ratio = Fraction(
                brief["fps"] * edit["speed"]["den"],
                asset_source["fps"] * edit["speed"]["num"],
            )
            length = nearest_frame((edit["out_frame"] - edit["in_frame"]) * ratio)
            expected = {
                "list_position": index,
                "id": edit["id"],
                "delivery_start_frame": position,
                "duration_frames": length,
                "source_in_frame": edit["in_frame"],
                "source_out_frame": edit["out_frame"],
                "retiming_ratio": {"num": ratio.numerator, "den": ratio.denominator},
            }
            assembled &= timeline[index] == expected
            position += length + edit["gap_after_frames"]

        def stamp(frame):
            # Independent integer nearest-ms conversion for artifact validation.
            q, r = divmod(frame * 1000, brief["fps"])
            q += 2 * r > brief["fps"] or 2 * r == brief["fps"] and q % 2 == 1
            h, rest = divmod(q, 3600000)
            m, rest = divmod(rest, 60000)
            s, ms = divmod(rest, 1000)
            sep = "," if brief["delivery_format"] == "srt" else "."
            return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"

        asset = (
            ("WEBVTT\n\n" if brief["delivery_format"] == "vtt" else "")
            + "\n\n".join(
                f"{i}\n{stamp(row['start_frame'])} --> {stamp(row['end_frame'])}\n{row['text']}"
                for i, row in enumerate(rows, 1)
            )
            + "\n"
        )
        return {
            "edit_timeline_assembled": bool(assembled),
            "complete_edit_coverage": bool(coverage),
            "retained_content_matches": bool(content),
            "retimed_boundaries_match": bool(timing),
            "line_wrapping_valid": bool(wrapping),
            "delivery_configuration_matches": bool(config),
            "serialized_asset_matches": bool(config and self.artifact == asset),
        }
