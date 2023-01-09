class Callbacks:
    def __init__(self):
        self.callbacks = list()

    def add_callback(self, callback: str, handler):
        # add a new callback
        self.callbacks.append((callback, handler))

    def fire_callback(self, event):
        # get the callback function and parameters and fire them, or return nothing
        callbacks = self.get_callbacks(callback=event)
        if len(callbacks) == 0: return

        for callback in callbacks:
            _, handler = callback
            handler()
        return callbacks

    def get_callbacks(self, callback: str) -> tuple:
        # Checks all callback definitions for the ones that contain this callback
        # and return handlers and parameters in a tuple

        # find only the relevant handlers
        handlers = tuple(
            filter(
                lambda handler: True if callback == handler[0] else False,
                self.callbacks
                )
            )
        return handlers
