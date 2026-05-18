"""Tests for one-command workflow checks."""

from src import workflow


def test_run_workflow_check_mode_handles_missing_ollama(monkeypatch):
    monkeypatch.setattr(workflow, "check_dependencies", lambda: True)
    monkeypatch.setattr(workflow, "check_dataset", lambda: True)
    monkeypatch.setattr(workflow, "run_tests", lambda: True)
    monkeypatch.setattr(workflow, "check_ollama", lambda: False)

    assert workflow.run_workflow(launch_ui=False) == 0
