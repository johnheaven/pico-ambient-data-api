class ambient_data_reader:
    def __init__(self, sda_pin=0, scl_pin=1, gpio=0, sensor_type='none'):
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
        try:
            bme_data = self.bme280_sensor.read_compensated_data()
        except Exception as e:
            print('ERROR: Couldn\'t get BME280 reading.')
            return None, None, None
        else:
            #temp, pressure, humidity
            return bme_data[0] / 100, bme_data[1] / 10000, bme_data[2] / 1000
    
    def __init_bme280(self):
        from machine import I2C, Pin
        # bme280 micropython library needs to have been installed, e.g. via Thonny
        try: 
            import bme280 #type: ignore
        except ImportError as e:
            print('ERROR: BME280 library not found.')
            return False

        try:
            #initializing the I2C method 
            i2c = I2C(
                id=0,
                sda=Pin(self.sda_pin),
                scl=Pin(self.scl_pin),
                freq=400000
                ) #type: ignore
            scan_results = i2c.scan()
        except:
            print('ERROR: Couldn\'t initiate BME280')
            return False

        # Checks whether a device can be found and prints error message if not
        if len(scan_results) == 0:
            print(f'ERROR: No device found with SDA {self.sda_pin}, SCL {self.scl_pin}.')
            return False
            
        self.bme280_sensor = bme280.BME280(i2c=i2c)
        print('initiated bme280')
        return True

    def __get_dht22_reading(self):
        try:
            self.dht22_sensor.measure()
        except Exception as e:
            print('ERROR: Got exception when trying to read DHT22 sensor')
            return None, None, None
        else:
            return self.dht22_sensor.temperature(), None, self.dht22_sensor.humidity()

    def __init_dht22(self):
        from machine import Pin
        from dht import DHT22

        try:
            self.dht22_sensor = DHT22(Pin(self.gpio)) #type: ignore
        except:
            print(f'ERROR: Got error when trying to initiate DHT22 on pin {self.gpio}')
            return False
        else:
            print('initiated dht22')
            return True

    def __no_sensor_reading(self):
        return None, None, None

    def __init_no_sensor(self):
        print('No sensor configured')
        return True

def get_ambient_data(sda_pin=0, scl_pin=1, iterations=1, interval_seconds=2, gpio=0, sensor_type='none'):
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
    
    adr = ambient_data_reader(sensor_type=sensor_type, gpio=gpio, sda_pin=sda_pin, scl_pin=scl_pin)
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


