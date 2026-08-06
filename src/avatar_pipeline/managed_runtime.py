"""Load an explicitly configured provider bundle for autonomous managed runs."""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from avatar_pipeline.models import DailyTask, TopicCandidate
from avatar_pipeline.orchestration import ManagedProviders

_RUNTIME_ENV = "AVATAR_PIPELINE_MANAGED_RUNTIME"


@dataclass(frozen=True)
class ManagedRunInput:
    """Verified candidates and provider implementations for one managed day."""

    candidates: Sequence[TopicCandidate]
    providers: ManagedProviders
    max_topic_attempts: int = 5

    def __post_init__(self) -> None:
        if self.max_topic_attempts < 1:
            raise ValueError("max_topic_attempts must be at least 1")


ManagedRuntimeFactory = Callable[[DailyTask], ManagedRunInput]


def load_managed_runtime_factory(spec: str | None = None) -> ManagedRuntimeFactory:
    """Resolve ``module:factory`` only when the operator explicitly configures it."""

    target = (spec if spec is not None else os.environ.get(_RUNTIME_ENV, "")).strip()
    if not target:
        raise ValueError(
            f"managed mode requires {_RUNTIME_ENV}=<python_module>:<factory>; "
            "real providers are not configured by default"
        )
    module_name, separator, attribute_name = target.partition(":")
    if not separator or not module_name.strip() or not attribute_name.strip():
        raise ValueError(f"{_RUNTIME_ENV} must use <python_module>:<factory>")
    module = importlib.import_module(module_name.strip())
    factory = getattr(module, attribute_name.strip(), None)
    if not callable(factory):
        raise ValueError(f"configured managed runtime is not callable: {target}")
    return factory
