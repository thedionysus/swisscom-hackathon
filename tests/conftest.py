import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="DATABASE_URL not set; integration tests skipped")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
