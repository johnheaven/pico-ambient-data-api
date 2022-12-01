def device_uuid_string():
    """
    Gets the device's UUID as a string.
    Thanks to github.com/JH-87/ for finding out how to do get a string from bytes :)

    Returns:
        str: The string representation of the board's UUID
    """
    import binascii, machine
    return binascii.b2a_base64(machine.unique_id()).decode('utf-8').strip('\n')

class led_notify():
    """
    An object to emit predefined notifications through LED flashes.
    """
    def __init__(self, led='LED'):
        # get internal LED
        self.LED = self.get_led(led)
        
        # define events
        self.wifi_starting_to_connect = lambda: self.LED.on()
        self.wifi_connected = lambda: self.LED.off()
        self.settings_read = lambda: self.flash_led(self.LED, repeats=1, final_state=False)
        self.cant_connect = lambda: self.flash_led(self.LED, repeats=2, final_state=False)

        # define statuses
        self.no_wifi = lambda: self.flash_led(self.LED, repeats=-1, final_state=False)

    def get_led(self, pin='LED'):
        from machine import Pin
        led = Pin(pin, Pin.OUT)
        return led


    def flash_led(self, led, delay=200, repeats=5, final_state=False):
        from utime import sleep_ms
        i = 0
        while i <= repeats * 2 or repeats == -1:
            i = i +1
            led.toggle()
            sleep_ms(delay)
        if final_state:
            led.high()
        else:
            led.low()

def next(iterable, default=None):
    """
    Recreate Python's built-in next function, which allows for a default if the iterable is exhausted.
    """
    from builtins import next as _next
    try:
        return _next(iterable)
    except StopIteration as e:
        if default is not None:
            return default
        else:
            raise e

class RuntimeParams:
    def __init__(self):
        # the dictionary to store params in
        self.runtime_params = {}

    def add_runtime_param(self, key, value):
        self.runtime_params[key] = value
        return self.runtime_params

    def get_runtime_param(self, key):
        """Get a single runtime parameter

        Args:
            key (str): The key of the value to get
        """
        return self.runtime_params.get(key, None)
    
    def get_runtime_params_dict(self, keys: tuple, merge: dict={}) -> dict:
        """
        Get placeholder parameters available at the time this method is called
        and return a dictionary, optionally merged with the dictionary specified 
        as merge.

        This is useful so callbacks and routes can receive arguments that aren't available when they're registered.

        Args:
            keys (tuple): Keys of variables to include
            merge (dict, optional): Optional dictionary to merge with. This takes precedence in case of conflict. Defaults to {}.

        Returns:
            dict: Dictionary with available values
        """

        runtime_params = {key: self.runtime_params.get(key, None) for key in keys}
        runtime_params.update(merge)
        return runtime_params if runtime_params is not None else {}