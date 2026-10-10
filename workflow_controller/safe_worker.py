"""Restricted pure-Python worker with CPU/memory limits and no grading state."""

import ast
import json
import itertools
import math
import resource
import sys


METHODS = {
    "get",
    "items",
    "keys",
    "values",
    "strip",
    "lower",
    "upper",
    "split",
    "replace",
    "startswith",
    "endswith",
    "append",
    "extend",
    "sort",
    "count",
    "index",
    "pop",
    "remove",
    "add",
    "discard",
    "copy",
    "update",
    "setdefault",
    "clear",
    "insert",
    "reverse",
    "intersection",
    "union",
    "difference",
    "symmetric_difference",
    "issubset",
    "issuperset",
    "isdisjoint",
    "join",
    "lstrip",
    "rstrip",
    "isdigit",
    "isalpha",
}
FUNCTIONS = {
    "combinations",
    "product",
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
    "len",
    "list",
    "max",
    "min",
    "range",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
    "reversed",
    "divmod",
    "pow",
}
NODES = {
    ast.Module,
    ast.FunctionDef,
    ast.Delete,
    ast.Del,
    ast.Starred,
    ast.Yield,
    ast.YieldFrom,
    ast.JoinedStr,
    ast.FormattedValue,
    ast.Assert,
    ast.While,
    ast.Nonlocal,
    ast.Pow,
    ast.LShift,
    ast.RShift,
    ast.BitAnd,
    ast.BitOr,
    ast.BitXor,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.Assign,
    ast.AugAssign,
    ast.For,
    ast.If,
    ast.IfExp,
    ast.Expr,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Subscript,
    ast.Slice,
    ast.Attribute,
    ast.Call,
    ast.keyword,
    ast.ListComp,
    ast.DictComp,
    ast.SetComp,
    ast.GeneratorExp,
    ast.comprehension,
    ast.Lambda,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.USub,
    ast.UAdd,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
}


def validate(source):
    if not isinstance(source, str) or len(source) > 7000:
        raise ValueError("Source must be at most 7000 characters")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(
            f"Invalid Python syntax at line {exc.lineno}: {exc.msg}"
        ) from None
    if (
        len(tree.body) != 1
        or not isinstance(tree.body[0], ast.FunctionDef)
        or tree.body[0].name != "compute"
    ):
        raise ValueError("Provide exactly one function: def compute(data): ...")
    function = tree.body[0]
    if (
        [a.arg for a in function.args.args] != ["data"]
        or function.decorator_list
        or function.args.defaults
        or function.args.vararg
        or function.args.kwarg
        or function.args.kwonlyargs
        or function.returns
    ):
        raise ValueError(
            "Use the plain signature compute(data) without decorators or annotations"
        )
    helpers = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and (
            node.name.startswith("__") or node.decorator_list or node.returns
        ):
            raise ValueError(
                "Use plain local helper functions without private names, decorators or annotations"
            )
        if isinstance(node, ast.Nonlocal) and any(
            name.startswith("__") for name in node.names
        ):
            raise ValueError("Private names are unavailable")
        if type(node) not in NODES:
            raise ValueError(f"Unsupported Python construct: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("Private names are unavailable")
        if isinstance(node, ast.arg) and node.arg.startswith("__"):
            raise ValueError("Private names are unavailable")
        if isinstance(node, ast.Attribute) and node.attr not in METHODS:
            raise ValueError("Only documented collection/string methods are available")
        if isinstance(node, ast.Attribute) and isinstance(
            node.ctx, (ast.Store, ast.Del)
        ):
            raise ValueError(
                "Attribute assignment is unavailable; mutate local collections only"
            )
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id not in FUNCTIONS | helpers
            ):
                raise ValueError("Call only the documented pure builtins")
            if not isinstance(node.func, (ast.Name, ast.Attribute)):
                raise ValueError("Indirect calls are unavailable")
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and len(node.value) > 7000
        ):
            raise ValueError("Literal is too large")
    return tree


def bounded_range(*args):
    result = range(*args)
    if len(result) > 5000:
        raise ValueError("range is limited to 5000 values")
    return result


def bounded_combinations(values, count):
    values = list(values)
    if (
        type(count) is not int
        or not 0 <= count <= len(values)
        or len(values) > 16
        or math.comb(len(values), count) > 5000
    ):
        raise ValueError("Combinations are limited to 5000 choices")
    return itertools.combinations(values, count)


def bounded_product(*pools):
    pools = [list(pool) for pool in pools]
    if len(pools) > 16 or math.prod(len(pool) for pool in pools) > 5000:
        raise ValueError("Product is limited to 5000 choices")
    return itertools.product(*pools)


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    body = json.loads(sys.stdin.read(150000))
    try:
        tree = validate(body["source"])
        builtins = {
            name: getattr(__import__("builtins"), name)
            for name in FUNCTIONS - {"combinations", "product"}
        }
        builtins["combinations"] = bounded_combinations
        builtins["product"] = bounded_product
        builtins["range"] = bounded_range
        namespace = {"__builtins__": builtins}
        exec(compile(tree, "<workspace>", "exec"), namespace)
        results = [namespace["compute"](data) for data in body["inputs"]]
        encoded = json.dumps({"outputs": results}, allow_nan=False)
        if len(encoded) > 40000:
            raise ValueError("Output too large")
        print(encoded)
    except Exception as exc:
        # User code also runs on additional regression inputs. Exception text
        # can deliberately contain those records; only expose the error class.
        print(json.dumps({"error": type(exc).__name__}))


if __name__ == "__main__":
    main()
