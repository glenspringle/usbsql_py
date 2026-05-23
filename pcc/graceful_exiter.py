import signal

class GracefulExiter():
    """CTRL+C Interrupt Handler.
    Allows us to gently exit a while loop.
    Ex:

    flag = GracefulExiter()
    while not flag.exit():
    ...
    """

    def __init__(self):
        """Initialize class and setup function call on SIGINT."""
        self.state = False
        signal.signal(signal.SIGINT, self.change_state)
        signal.signal(signal.SIGTERM, self.change_state)

    def change_state(self, signum, frame):
        """"Release function pointer, and set state to true when SIGINT is caught."""
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.state = True

    def flag_for_exit(self):
        self.state = True

    def ready_to_exit(self):
        """Repeatedly call this to see if SIGINT has occurred."""
        return self.state
