import pytest
import IPython

from micra_scheduler import Scheduler
from environments import environment

@pytest.fixture
def scheduler():
  yield Scheduler(config=environment)

def test_subscription(scheduler: Scheduler):
  scheduler.connect()

  IPython.terminal.embed.InteractiveShellEmbed().mainloop()
