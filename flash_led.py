def flash_led(led, delay=50, repeats=5, final_state=False):
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
