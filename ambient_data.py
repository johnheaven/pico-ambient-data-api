def get_ambient_data(sda_pin=0, scl_pin=1, iterations=1, interval_seconds=2):
    """Get ambient data from bme280

    Args:
        sda_pin (int, optional): The SDA pin. Defaults to 0.
        scl_pin (int, optional): The SCL pin. Defaults to 1.
        iterations (int, optional): Number of total readings for the generator. Defaults to 1.
        interval_seconds (int, optional): (Minimum) interval between readings. Defaults to 2.

    Yields:
        Array of integers: Raw readings temperature, pressure, humidity
    """
    from machine import Pin, I2C
    from utime import sleep

    # bme280 micropython library needs to have been installed, e.g. via Thonny
    import bme280

    #initializing the I2C method 
    i2c = I2C(
        id=0,
        sda=Pin(sda_pin),
        scl=Pin(scl_pin),
        freq=400000
        )
    scan_results = i2c.scan()

    # Checks whether a device can be found (for debugging purposes)
    if len(scan_results) == 0:
        print("No device found.")
        
    bme = bme280.BME280(i2c=i2c)
    
    # Start a loop -> it's infinite if iterations == True. Otherwise stops after max number of iterations reached.
    i = 0
    while True:
        i += 1
        bme = bme280.BME280(i2c=i2c)          #BME280 object created
        yield bme.read_compensated_data()
        # no need to sleep after last iteration
        if i == iterations and iterations is not True: break
        sleep(interval_seconds)

def print_ambient_data(data):
    """Pretty prints ambient data

    Args:
        data Array of integers: An item from generator returned by get_ambient_data function
    """
    t, p, h = tuple(data)
    print("Temp:", t)
    print("Pressure: ", p)
    print("Humidity: ", h)


