

"""Explicit registry of tools available to the SYNAPSE executor.

Registration does not authorize execution. Policy and approval checks
must happen independently before a registered tool is invoked.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import TypeAlias


ToolHandler: TypeAlias = Callable[[Mapping[str, str]], object]


class ToolRegistryError(Exception):
    """Base exception for tool-registry failures."""


class DuplicateToolError(ToolRegistryError):
    """Raised when a tool name is already registered."""


class UnknownToolError(ToolRegistryError):
    """Raised when a requested tool has not been registered."""


class ToolRegistry:
    """Explicit allowlist of callable tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolHandler] = {}

    def register(self, name: str, handler: ToolHandler) -> None:
        """Register a tool without granting permission to invoke it."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Tool name must be a nonblank string.")

        if not callable(handler):
            raise TypeError("Tool handler must be callable.")

        if name in self._tools:
            raise DuplicateToolError(f"Tool already registered: {name}")

        self._tools[name] = handler

    def resolve(self, name: str) -> ToolHandler:
        """Return a registered handler without invoking it."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownToolError(
                f"Tool is not registered: {name}"
            ) from exc

    def contains(self, name: str) -> bool:
        """Return whether a tool name is registered."""
        return name in self._tools

    @property
    def registered_names(self) -> tuple[str, ...]:
        """Return registered names without exposing the mutable registry."""
        return tuple(sorted(self._tools))

    def invoke(
        self,
        name: str,
        parameters: tuple[tuple[str, str], ...],
    ) -> object:
        """Invoke a registered handler with validated string parameters."""
        if not isinstance(parameters, tuple):
            raise TypeError("Parameters must be a tuple of pairs.")

        values: dict[str, str] = {}

        for item in parameters:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("Each parameter must be a (name, value) pair.")

            key, value = item

            if not isinstance(key, str) or not key.strip():
                raise ValueError("Parameter names must be nonblank strings.")

            if not isinstance(value, str):
                raise TypeError("Parameter values must be strings.")

            if key in values:
                raise ValueError(f"Duplicate parameter: {key}")

            values[key] = value

        handler = self.resolve(name)
        return handler(MappingProxyType(values))
