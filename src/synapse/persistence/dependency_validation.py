"""Validation helpers for task dependency graphs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


class DependencyValidationError(ValueError):
    """Raised when a task dependency graph violates integrity rules."""


def validate_dependency_graph(
    task_objectives: Mapping[str, str],
    dependencies: Mapping[str, Iterable[str]],
) -> None:
    """Validate task references, objective ownership, and acyclicity.

    Args:
        task_objectives: Mapping of each known task ID to its objective ID.
        dependencies: Mapping of task IDs to the IDs they depend on. A task
            may be omitted when it has no dependencies.

    Raises:
        DependencyValidationError: If a task is unknown, a dependency is
            unknown, a dependency crosses objective boundaries, or the graph
            contains a cycle.
    """
    known_tasks = set(task_objectives)

    for task_id, dependency_ids in dependencies.items():
        if task_id not in known_tasks:
            raise DependencyValidationError(
                f"Dependency graph references unknown task {task_id!r}."
            )

        for dependency_id in dependency_ids:
            if dependency_id not in known_tasks:
                raise DependencyValidationError(
                    f"Task {task_id!r} depends on unknown task "
                    f"{dependency_id!r}."
                )
            if task_id == dependency_id:
                raise DependencyValidationError(
                    f"Task {task_id!r} cannot depend on itself."
                )
            if task_objectives[task_id] != task_objectives[dependency_id]:
                raise DependencyValidationError(
                    f"Task {task_id!r} and dependency {dependency_id!r} "
                    "belong to different objectives."
                )

    # Three-color depth-first search detects a back-edge on the active path.
    unvisited = 0
    visiting = 1
    visited = 2
    colors = dict.fromkeys(known_tasks, unvisited)

    def visit(task_id: str) -> None:
        color = colors[task_id]
        if color == visiting:
            raise DependencyValidationError(
                f"Dependency cycle detected at task {task_id!r}."
            )
        if color == visited:
            return

        colors[task_id] = visiting
        for dependency_id in dependencies.get(task_id, ()):
            visit(dependency_id)
        colors[task_id] = visited

    for task_id in known_tasks:
        if colors[task_id] == unvisited:
            visit(task_id)
