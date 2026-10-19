"""Tests for task dependency graph validation."""

from __future__ import annotations

import pytest

from synapse.persistence.dependency_validation import (
    DependencyValidationError,
    validate_dependency_graph,
)


def test_accepts_valid_acyclic_dependencies() -> None:
    task_objectives = {
        "task-a": "objective-1",
        "task-b": "objective-1",
        "task-c": "objective-1",
        "task-independent": "objective-1",
    }
    dependencies = {
        "task-b": ["task-a"],
        "task-c": ["task-b"],
    }

    validate_dependency_graph(task_objectives, dependencies)


def test_rejects_direct_self_dependency() -> None:
    with pytest.raises(DependencyValidationError, match="cannot depend on itself"):
        validate_dependency_graph(
            {"task-a": "objective-1"},
            {"task-a": ["task-a"]},
        )


def test_rejects_indirect_dependency_cycle() -> None:
    task_objectives = {
        "task-a": "objective-1",
        "task-b": "objective-1",
        "task-c": "objective-1",
    }
    dependencies = {
        "task-a": ["task-c"],
        "task-b": ["task-a"],
        "task-c": ["task-b"],
    }

    with pytest.raises(DependencyValidationError, match="cycle"):
        validate_dependency_graph(task_objectives, dependencies)


def test_rejects_dependency_across_objectives() -> None:
    task_objectives = {
        "task-a": "objective-1",
        "task-b": "objective-2",
    }

    with pytest.raises(DependencyValidationError, match="different objectives"):
        validate_dependency_graph(task_objectives, {"task-a": ["task-b"]})


def test_rejects_unknown_task_in_dependency_mapping() -> None:
    with pytest.raises(DependencyValidationError, match="unknown task"):
        validate_dependency_graph(
            {"task-a": "objective-1"},
            {"task-missing": []},
        )


def test_rejects_unknown_dependency_reference() -> None:
    with pytest.raises(DependencyValidationError, match="unknown task"):
        validate_dependency_graph(
            {"task-a": "objective-1"},
            {"task-a": ["task-missing"]},
        )


def test_accepts_multiple_dependencies_without_a_cycle() -> None:
    task_objectives = {
        "task-a": "objective-1",
        "task-b": "objective-1",
        "task-c": "objective-1",
        "task-d": "objective-1",
    }
    dependencies = {
        "task-b": ["task-a"],
        "task-c": ["task-a"],
        "task-d": ["task-b", "task-c"],
    }

    validate_dependency_graph(task_objectives, dependencies)
