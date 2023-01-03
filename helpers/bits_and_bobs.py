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
        self.on = lambda **kwargs: self.LED.on()
        self.off = lambda **kwargs: self.LED.off()
        self.flash_once_off = lambda **kwargs: self.flash_led(self.LED, repeats=0, final_state=False)
        self.flash_once_on = lambda **kwargs: self.flash_led(self.LED, repeats=0, final_state=True)
        self.flash_twice_off = lambda **kwargs: self.flash_led(self.LED, repeats=2, final_state=False)

        # define statuses
        self.no_wifi = lambda: self.flash_led(self.LED, repeats=-1, final_state=False)

    def get_led(self, pin='LED'):
        from machine import Pin
        led = Pin(pin, Pin.OUT)
        return led


    def flash_led(self, led, delay=200, repeats=5, final_state=False, **kwargs):
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

class Globals:
    def __init__(self):
        # the dictionary to store globals in
        self.globals = {}

    def add(self, key, value):
        self.globals[key] = value
        return self.globals

    def get(self, key):
        """Get a single global

        Args:
            key (str): The key of the value to get
        """
        return self.globals.get(key, None)
    
    def get_dict(self, keys: tuple, merge: dict={}) -> dict:
        """
        Get globals available at the time this method is called
        and return a dictionary, optionally merged with the dictionary specified 
        as merge.

        This is useful so callbacks and routes can receive arguments that aren't available when they're registered.

        Args:
            keys (tuple): Keys of variables to include
            merge (dict, optional): Optional dictionary to merge with. This takes precedence in case of conflict. Defaults to {}.

        Returns:
            dict: Dictionary with available values
        """

        globals = {key: self.globals.get(key, None) for key in keys}
        globals.update(merge)
        return globals if globals is not None else {}

### Watchdog Timer ###

def start_wdt():
    import uasyncio, machine
    loop = uasyncio.get_event_loop()
    #wdt = machine.WDT(timeout=8000)
    wdt = None
    loop.create_task(ping_wdt(2000, wdt))

async def ping_wdt(ping_freq, wdt):
    import uasyncio
    while True:
        await uasyncio.sleep_ms(ping_freq)
        #wdt.feed()
        print('DEBUG: wdt.feed()')