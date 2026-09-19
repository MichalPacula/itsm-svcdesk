# ai-generated: 90% - Claude Code wrote this fixture; reviewed and accepted as-is
"""Gives every integration test a fresh SQLite file and test-clock mode enabled."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from svcdesk.main import app


@pytest.fixture()
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # let the app's startup hook create it fresh
    monkeypatch.setenv("SVCDESK_DB", path)
    monkeypatch.setenv("SVCDESK_TEST_CLOCK", "1")
    with TestClient(app) as c:
        yield c
    if os.path.exists(path):
        os.remove(path)
