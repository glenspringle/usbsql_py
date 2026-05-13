import os
import signal
from proj_name.graceful_exiter import GracefulExiter


def test_graceful_exiter():
    flag = GracefulExiter()
    while not flag.exit():
        # Induces GracefulExiter.change_state
        os.kill(os.getpid(), signal.SIGINT)

    assert True
