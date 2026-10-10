"""Exact arithmetic on agent-supplied numbers, with no environment-state access."""

import ast
import math
from fractions import Fraction
from .math_tasks import rational, encoded


def calculate(params):
    if (
        set(params) != {"expression", "variables"}
        or not isinstance(params["expression"], str)
        or len(params["expression"]) > 512
        or not isinstance(params["variables"], dict)
        or len(params["variables"]) > 24
    ):
        raise ValueError("Supply a bounded arithmetic expression and numeric variables")
    try:
        tree = ast.parse(params["expression"], mode="eval")
    except SyntaxError:
        raise ValueError("Invalid arithmetic expression") from None
    if len(list(ast.walk(tree))) > 128:
        raise ValueError("Expression too large")
    variables = {name: rational(value) for name, value in params["variables"].items()}

    def eval_node(node):
        if isinstance(node, ast.Constant) and type(node.value) in [int, float]:
            result = rational(node.value)
        elif isinstance(node, ast.Name) and node.id in variables:
            result = variables[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.USub, ast.UAdd)
        ):
            result = eval_node(node.operand) * (
                -1 if isinstance(node.op, ast.USub) else 1
            )
        elif isinstance(node, ast.BinOp):
            a, b = eval_node(node.left), eval_node(node.right)
            if isinstance(node.op, ast.Add):
                result = a + b
            elif isinstance(node.op, ast.Sub):
                result = a - b
            elif isinstance(node.op, ast.Mult):
                result = a * b
            elif isinstance(node.op, ast.Div) and b:
                result = a / b
            elif isinstance(node.op, ast.Pow) and b.denominator == 1 and 0 <= b <= 8:
                result = a ** int(b)
            else:
                raise ValueError("Unsupported arithmetic operation")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in ["ceil", "floor", "round_half_up", "abs"]
            and len(node.args) == 1
            and not node.keywords
        ):
            value = eval_node(node.args[0])
            name = node.func.id
            result = Fraction(
                math.ceil(value)
                if name == "ceil"
                else math.floor(value)
                if name == "floor"
                else math.floor(value + Fraction(1, 2))
                if name == "round_half_up"
                else abs(value)
            )
        else:
            raise ValueError(
                "Use only numbers, supplied variables and documented arithmetic"
            )
        return rational(encoded(result))

    value = eval_node(tree.body)
    return {
        "exact": encoded(value),
        "approximate": float(value),
        "note": "Computed from the supplied expression and variables only.",
    }
