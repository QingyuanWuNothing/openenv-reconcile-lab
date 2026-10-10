"""Private ergonomic caption editing without changing any outcome constraints."""

from .media_tasks import MediaWorkflow


class MediaIncremental(MediaWorkflow):
    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        self.tools["patch"]["segment"] = (
            "params={id,start_frame,end_frame,text}; replace one existing caption, preserving every other caption and their order"
        )
        self.instruction += " Prefer short incremental actions: patch target segment edits one caption. Its reply reports the actual character count and frame window. Match renderer format/fps to the fixed production brief before rendering."

    def patch(self, target, params):
        if target != "segment":
            return super().patch(target, params)
        if (
            set(params) != {"id", "start_frame", "end_frame", "text"}
            or params["id"] not in self.resources["source_text"]
        ):
            raise ValueError("Replace one existing caption using its complete fields")
        rows = [
            dict(params) if r["id"] == params["id"] else r
            for r in self.resources["segments"]
        ]
        super().patch("segments", {"segments": rows})
        return {
            "segment": dict(params),
            "characters": len(params["text"]),
            "maximum_characters": self.resources["brief"]["max_characters"],
            "frame_window": self.resources["brief"]["cue_windows"].get(
                params["id"], [0, self.resources["brief"]["duration_frames"]]
            ),
            "version": self.version,
        }
