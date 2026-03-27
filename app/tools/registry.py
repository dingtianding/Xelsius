from typing import Any, Callable

from app.models import Diff, ToolName, Transaction

ToolFn = Callable[[list[Transaction], dict[str, Any]], Diff]

_REGISTRY: dict[ToolName, ToolFn] = {}


def register(name: ToolName) -> Callable[[ToolFn], ToolFn]:
    def decorator(fn: ToolFn) -> ToolFn:
        _REGISTRY[name] = fn
        return fn
    return decorator


def execute(name: ToolName, transactions: list[Transaction], args: dict[str, Any]) -> Diff:
    fn = _REGISTRY.get(name)
    if fn is None:
        raise ValueError(f"Unknown tool: {name!r}")
    return fn(transactions, args)
