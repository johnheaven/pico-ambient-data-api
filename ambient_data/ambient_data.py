class ambient_data_reader:
    def __init__(self, sda_pin=0, scl_pin=1, gpio=20, sensor_type='none'):
        self.sda_pin = sda_pin
        self.scl_pin = scl_pin
        self.gpio = gpio

        # set the get_reading and initiate_sensor methods according to the sensor specified in sensor_type
        sensors_methods_dict = {
            'bme280': [self.__get_bme280_reading, self.__init_bme280],
            'dht22': [self.__get_dht22_reading, self.__init_dht22],
            'none': [self.__no_sensor_reading, self.__init_no_sensor]
            }
        try:
            self.get_reading = sensors_methods_dict[sensor_type][0] #type: ignore
            self.initiate_sensor = sensors_methods_dict[sensor_type][1] #type: ignore
        except KeyError:
            # raise an error if the sensor_type isn't supported
            raise ValueError(
                f'Received sensor_type {sensor_type} but expected one of {tuple(sensors_methods_dict.keys())} '
                )
    
    def __get_bme280_reading(self):
        bme_data = self.bme280_sensor.read_compensated_data()
        #temp, pressure, humidity
        return bme_data[0] / 100, bme_data[1] / 10000, bme_data[2] / 1000
    
    def __init_bme280(self):
        from machine import I2C, Pin
        # bme280 micropython library needs to have been installed, e.g. via Thonny
        import bme280 #type: ignore

        #initializing the I2C method 
        i2c = I2C(
            id=0,
            sda=Pin(self.sda_pin),
            scl=Pin(self.scl_pin),
            freq=400000
            ) #type: ignore
        scan_results = i2c.scan()

        # Checks whether a device can be found and raises error if not
        if len(scan_results) == 0:
            raise IOError("No device found.")
            
        self.bme280_sensor = bme280.BME280(i2c=i2c)
        print('initiated bme280')

    def __get_dht22_reading(self):
        self.dht22_sensor.measure()
        return self.dht22_sensor.temperature(), None, self.dht22_sensor.humidity()

    def __init_dht22(self):
        from machine import Pin
        from dht import DHT22

        self.dht22_sensor = DHT22(Pin(self.gpio)) #type: ignore
        print('initiated dht22')

    def __no_sensor_reading(self):
        return None, None, None

    def __init_no_sensor(self):
        print('No sensor configured')

def get_ambient_data(sda_pin=0, scl_pin=1, iterations=1, interval_seconds=2, sensor_type='none'):
    """Get ambient data from specified device

    Args:
        sda_pin (int, optional): The SDA pin. Defaults to 0.
        scl_pin (int, optional): The SCL pin. Defaults to 1.
        iterations (int, optional): Number of total readings for the generator. Defaults to 1.
        interval_seconds (int, optional): (Minimum) interval between readings. Defaults to 2.

    Yields:
        Array of integers: Raw readings temperature, pressure, humidity
    """
    
    from utime import sleep
    
    adr = ambient_data_reader(sensor_type=sensor_type, gpio=22)
    adr.initiate_sensor()

    # Start a loop -> it's infinite if iterations == True. Otherwise stops after max number of iterations reached.
    i = 0
    while True:
        i += 1
        yield adr.get_reading()
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


