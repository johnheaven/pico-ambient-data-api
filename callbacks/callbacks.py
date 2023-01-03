class Callbacks:
    def __init__(self, globals):

        self.callbacks = list()
        self._get_globals_dict = globals.get_dict

    def add_callback(self, callback: str, handler, params: dict, globals=None):
        """
        Add a route, handler and parameters i.e. a URL path and the function to be called when it is requested.

        Args:
            route (str): The string representation of the route (e.g. /data)
            handler (Callable): A callable (i.e. function) to be called to handle route
            params (dict, optional): Keywords arguments to be passed to routes in addition to any default params passed by the server. Defaults to {}.
        """

        self.callbacks.append((callback, handler, params, globals))

    def fire_callback(self, event):
        # get the callback function and parameters and fire them, or return nothing
        callbacks = self.get_callbacks(callback=event)
        print('DEBUG: callbacks = ', callbacks)
        if len(callbacks) == 0: return

        # merge in any globals
        callbacks = self.merge_globals(callbacks)

        for callback in callbacks:
            _, handler, params = callback
            handler(**params)
        return callbacks

    def get_callbacks(self, callback: str) -> tuple:
        
        """
        Checks all route/callback definitions for the one that contain this route
        and return handlers and parameters in a tuple

        Args:
            route_or_callback (str): The ID of the route or callback as a string

        Returns:
            tuple: Contains tuples, each with
            * string: the ID of the route of callback,
            * function: the function itself,
            * dict: parameters that needs to be passed into it when calling it, i.e. handler_function(**params)
        """

        # find only the relevant handlers
        handlers = tuple(
            filter(
                lambda handler: True if callback == handler[0] else False,
                self.callbacks
                )
            )
        return handlers

    def merge_globals(self, handlers):
        # expects handlers to be a tuple of (route_name: str, handler: function, params: dict, globals: tuple)
        # add in any globals that are now available by merging them with the existing params (these are present in handler[-1])
        # IMPORTANT: the input is a tuple of tuples, each containing 4 items; the output if a tuple of tuples each containing 3 values.
        handlers = tuple(
            map(
                # both need to be tuples to add them, hence the brackets. This is essentially replacing the last two items (params and globals with a merged dict of the two)
                # ... but with globals now a dictionary with the placeholders filled in
                lambda handler: handler[:-2] + (self._get_globals_dict(keys=handler[-1], merge=handler[-2]),),
                handlers
                )
            )
        return handlers