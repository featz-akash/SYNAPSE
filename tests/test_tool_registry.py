
import pytest

from synapse.execution.tool_registry import (
    DuplicateToolError,
    ToolRegistry,
    UnknownToolError,
)


def test_registered_tool_can_be_invoked():
    registry = ToolRegistry()
    registry.register(
        "read_source",
        lambda parameters: parameters["source"],
    )

    result = registry.invoke(
        "read_source",
        (("source", "document-1"),),
    )

    assert result == "document-1"


def test_unknown_tool_is_not_invoked():
    registry = ToolRegistry()

    with pytest.raises(UnknownToolError):
        registry.invoke("unregistered_tool", ())


def test_duplicate_registration_is_rejected():
    registry = ToolRegistry()
    registry.register("read_source", lambda _: "first")

    with pytest.raises(DuplicateToolError):
        registry.register("read_source", lambda _: "second")


def test_handler_cannot_mutate_parameter_mapping():
    registry = ToolRegistry()

    def handler(parameters):
        parameters["source"] = "changed"
        return "unexpected"

    registry.register("read_source", handler)

    with pytest.raises(TypeError):
        registry.invoke("read_source", (("source", "original"),))


def test_invalid_duplicate_parameters_are_rejected():
    registry = ToolRegistry()
    registry.register("read_source", lambda parameters: parameters)

    with pytest.raises(ValueError, match="Duplicate parameter"):
        registry.invoke(
            "read_source",
            (("source", "first"), ("source", "second")),
        )
