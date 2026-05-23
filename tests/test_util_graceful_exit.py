import os
import signal
from pcc.graceful_exiter import GracefulExiter


def test_graceful_exiter():
    flag = GracefulExiter()
    while not flag.ready_to_exit():
        # Induces GracefulExiter.change_state
        os.kill(os.getpid(), signal.SIGINT)

    assert True
