"""Caption editing and configured SRT/WebVTT production with output inspection."""

import re

from .scenarios import Media


class MediaWorkflow(Media):
    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        format_name = (
            "vtt"
            if split == "holdout" or level > 1 and self.rng.choice([True, False])
            else "srt"
        )
        self.resources["brief"]["delivery_format"] = format_name
        self.resources["rendering"] = {"format": "srt", "fps": 24}
        self.tools["inspect"] = list(self.resources)
        self.tools["patch"]["rendering"] = (
            "params={format:'srt'|'vtt',fps:integer}; choose the brief's format and source frame rate"
        )
        self.instruction = "Repair these captions to the production brief, preserving content and frame windows. Configure the renderer's format and frame rate, render an actual SRT or WebVTT asset, inspect the output and diagnostics, revise and commit. The renderer configuration determines timestamps; source fps and required delivery format are fixed in the brief."

    def patch(self, target, params):
        if target != "rendering":
            return super().patch(target, params)
        if (
            set(params) != {"format", "fps"}
            or params["format"] not in ["srt", "vtt"]
            or type(params["fps"]) is not int
            or not 8 <= params["fps"] <= 60
        ):
            raise ValueError("Set renderer format and integer fps")
        self.resources["rendering"] = dict(params)
        self.version += 1
        return {"rendering": dict(params), "version": self.version}

    def render_stamp(self, frame):
        ms = round(frame * 1000 / self.resources["rendering"]["fps"])
        hours, rest = divmod(ms, 3600000)
        minutes, rest = divmod(rest, 60000)
        seconds, ms = divmod(rest, 1000)
        separator = "," if self.resources["rendering"]["format"] == "srt" else "."
        return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{ms:03}"

    def run(self, target, params):
        if target != "render" or params:
            raise ValueError("Run render with params={}")
        body = (
            "\n\n".join(
                f"{i}\n{self.render_stamp(r['start_frame'])} --> {self.render_stamp(r['end_frame'])}\n{r['text']}"
                for i, r in enumerate(self.resources["segments"], 1)
            )
            + "\n"
        )
        self.artifact = (
            "WEBVTT\n\n" if self.resources["rendering"]["format"] == "vtt" else ""
        ) + body
        self.receipt_version = self.version
        return {
            "asset": self.artifact,
            "diagnostics": self.checks(),
            "version": self.version,
        }

    def checks(self):
        base = super().checks()
        brief = self.resources["brief"]
        fmt = brief["delivery_format"]
        artifact = self.artifact or ""
        body = artifact[8:] if artifact.startswith("WEBVTT\n\n") else artifact
        blocks = body.strip().split("\n\n")
        rows = self.resources["segments"]
        technical = (
            bool(rows)
            and len(blocks) == len(rows)
            and (artifact.startswith("WEBVTT\n\n") == (fmt == "vtt"))
        )
        separator = "," if fmt == "srt" else "."
        for i, row in enumerate(rows):
            lines = blocks[i].splitlines() if i < len(blocks) else []
            wanted = f"{self.timestamp(row['start_frame'])} --> {self.timestamp(row['end_frame'])}".replace(
                ",", separator
            )
            technical &= (
                len(lines) == 3
                and lines[0] == str(i + 1)
                and lines[1] == wanted
                and lines[2] == row["text"]
                and 0 < len(row["text"]) <= brief["max_characters"]
            )
            if len(lines) >= 2:
                technical &= bool(
                    re.fullmatch(
                        r"\d{2}:\d{2}:\d{2}[,.]\d{3} --> \d{2}:\d{2}:\d{2}[,.]\d{3}",
                        lines[1],
                    )
                )
        base["rendered_format_valid"] = bool(technical)
        return base
