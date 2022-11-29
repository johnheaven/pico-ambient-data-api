def device_uuid_string():
    """Gets the device's UUID as a string.
    Thanks to github.com/JH-87/ for finding out how to do get a string from bytes :)

    Returns:
        str: The string representation of the board's UUID
    """
    import binascii, machine
    return binascii.b2a_base64(machine.unique_id()).decode('utf-8').strip('\n')

class led_notify():
    def __init__(self):
        # get internal LED
        self.LED = self.get_led('LED')
        
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