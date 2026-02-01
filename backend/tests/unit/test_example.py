"""Example test suite to validate pytest setup."""

import pytest


@pytest.mark.unit
def test_basic_assertion():
    """Test basic assertion."""
    assert 1 + 1 == 2


@pytest.mark.unit
async def test_async_function():
    """Test async function support."""

    async def fetch_data():
        return {"status": "ok"}

    result = await fetch_data()
    assert result["status"] == "ok"
