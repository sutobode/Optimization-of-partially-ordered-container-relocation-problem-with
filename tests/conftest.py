import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATA20 = os.path.join(ROOT, "data_raw", "ex195", "每组前五个（195个）")
DATA00 = os.path.join(ROOT, "data_raw", "exrc", "不同比例RC数据集", "0%RC数据集")


def pytest_configure(config):
    sys.setrecursionlimit(100000)


@pytest.fixture(scope="session")
def data20() -> str:
    if not os.path.isdir(DATA20):
        pytest.skip("published 20 %-RC instances are not available")
    return DATA20


@pytest.fixture(scope="session")
def data00() -> str:
    if not os.path.isdir(DATA00):
        pytest.skip("published 0 %-RC instances are not available")
    return DATA00
