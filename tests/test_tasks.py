"""Tests for tasks.py - task definitions and data."""

import pytest

from scripts.lib.tasks import (
    BATCH_SIZE,
    TASK_DEFINITIONS,
    TASK_DEPENDENCIES,
    TASK_IDS,
    TASK_ID_TO_STEP,
    STEP_NAMES,
    TaskDefinition,
)


class TestTaskIdMapping:
    """Tests for TASK_IDS and TASK_ID_TO_STEP mappings."""

    def test_task_ids_has_all_workflow_steps(self):
        expected_steps = {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22}
        actual_steps = set(TASK_IDS.keys())
        assert actual_steps == expected_steps

    def test_task_id_to_step_is_inverse(self):
        for step, task_id in TASK_IDS.items():
            assert TASK_ID_TO_STEP[task_id] == step

    def test_all_task_ids_unique(self):
        task_ids = list(TASK_IDS.values())
        assert len(task_ids) == len(set(task_ids))


class TestDependencyGraph:
    """Tests for TASK_DEPENDENCIES validity."""

    def test_all_dependencies_exist(self):
        all_task_ids = set(TASK_DEFINITIONS.keys()) | set(TASK_DEPENDENCIES.keys())
        for task_id, deps in TASK_DEPENDENCIES.items():
            for dep in deps:
                assert dep in all_task_ids, f"Task {task_id} depends on non-existent task {dep}"

    def test_no_self_dependencies(self):
        for task_id, deps in TASK_DEPENDENCIES.items():
            assert task_id not in deps, f"Task {task_id} depends on itself"

    def test_no_circular_dependencies(self):
        def has_cycle(task_id: str, visited: set, path: set) -> bool:
            if task_id in path:
                return True
            if task_id in visited:
                return False
            visited.add(task_id)
            path.add(task_id)
            for dep in TASK_DEPENDENCIES.get(task_id, []):
                if has_cycle(dep, visited, path):
                    return True
            path.remove(task_id)
            return False

        visited: set[str] = set()
        for task_id in TASK_DEPENDENCIES:
            assert not has_cycle(task_id, visited, set()), f"Circular dependency detected involving {task_id}"

    def test_context_tasks_blocked_by_output_summary(self):
        context_task_ids = [
            "context-plugin-root", "context-planning-dir",
            "context-initial-file", "context-review-mode",
        ]
        for task_id in context_task_ids:
            assert task_id in TASK_DEPENDENCIES
            assert "output-summary" in TASK_DEPENDENCIES[task_id]

    def test_workflow_chain_integrity(self):
        assert TASK_DEPENDENCIES["research-decision"] == []
        assert TASK_DEPENDENCIES["output-summary"] == ["final-verification"]


class TestTaskDefinitions:
    """Tests for TASK_DEFINITIONS completeness."""

    def test_all_workflow_task_ids_have_definitions(self):
        workflow_task_ids = set(TASK_IDS.values())
        defined_tasks = set(TASK_DEFINITIONS.keys())
        assert workflow_task_ids == defined_tasks

    def test_all_definitions_have_required_fields(self):
        for task_id, defn in TASK_DEFINITIONS.items():
            assert isinstance(defn, TaskDefinition)
            assert defn.subject
            assert defn.description
            assert defn.active_form

    def test_task_definition_to_dict(self):
        defn = TaskDefinition(
            subject="Test", description="Test description", active_form="Testing",
        )
        result = defn.to_dict()
        assert result == {"subject": "Test", "description": "Test description", "activeForm": "Testing"}


class TestConstants:
    """Tests for module constants."""

    def test_batch_size_is_seven(self):
        assert BATCH_SIZE == 7

    def test_step_names_covers_all_steps(self):
        assert 0 in STEP_NAMES
        assert 1 in STEP_NAMES
        assert 4 in STEP_NAMES
        for step in TASK_IDS:
            assert step in STEP_NAMES
