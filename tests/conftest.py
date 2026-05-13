from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture() -> Any:
    def _load(name: str) -> Any:
        return json.loads((FIXTURES / f"{name}.json").read_text())

    return _load


@pytest.fixture
def api_key() -> str:
    return "pk_test_key"


@pytest.fixture
def base_url() -> str:
    return "https://public.heypocketai.com/api/v1"
