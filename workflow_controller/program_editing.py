"""Bounded source edits; agent drafts never run until full validation succeeds."""

from .safe_worker import validate


EDIT_TOOL = "params={source:string} OR {source_lines:[strings]} to replace the function; OR {edit:{start:zero-based line index,delete:number of lines,lines:[up to 64 replacement strings]}} to edit a chunk. Keep indentation in each line. Chunk edits may leave temporary syntax errors; run requires a complete valid compute(data). Inspect source after editing."


def edit_source(current, params):
    chunk = False
    if set(params) == {"source"}:
        source = params["source"]
    elif set(params) == {"source_lines"}:
        source = join_lines(params["source_lines"], 300)
    elif set(params) == {"edit"}:
        edit = params["edit"]
        if not isinstance(edit, dict) or set(edit) != {"start", "delete", "lines"}:
            raise ValueError("edit needs start, delete and lines")
        start, delete = edit["start"], edit["delete"]
        lines = current.splitlines()
        if (
            type(start) is not int
            or type(delete) is not int
            or not 0 <= start <= len(lines)
            or not 0 <= delete <= len(lines) - start
        ):
            raise ValueError("Line range is outside the current source")
        replacement = join_lines(edit["lines"], 64).splitlines()
        lines[start : start + delete] = replacement
        source = "\n".join(lines) + "\n"
        chunk = True
    else:
        raise ValueError("Choose exactly one source, source_lines or edit payload")
    if not isinstance(source, str) or len(source) > 7000:
        raise ValueError("Source must be at most 7000 characters")
    try:
        validate(source)
    except ValueError as exc:
        if not chunk or not str(exc).startswith("Invalid Python syntax"):
            raise
        return source, {"ready_to_run": False, "syntax_error": str(exc)}
    return source, {"ready_to_run": True}


def join_lines(lines, maximum):
    if (
        not isinstance(lines, list)
        or len(lines) > maximum
        or any(
            not isinstance(line, str) or "\n" in line or "\r" in line for line in lines
        )
    ):
        raise ValueError(
            f"Provide at most {maximum} strings, one source line per string"
        )
    return "\n".join(lines) + ("\n" if lines else "")
