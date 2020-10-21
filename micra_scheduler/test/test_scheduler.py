import pytest

from micra_scheduler import Scheduler
from environments import environment

@pytest.fixture
def scheduler():
  yield Scheduler(config=environment)

def test_scheduler(scheduler: Scheduler):
  scheduler.connect()