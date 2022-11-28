from ambient_data.ambient_data import get_ambient_data
from mini_server.mini_server import mini_server
from settings import global_settings
from helpers.helpers import device_uuid_string
#from flash_led import flash_led
from routes import *
# get the UUID of this machine
my_uuid = device_uuid_string()
# give this Pico an id so it can be found over the network
pico_id = global_settings[my_uuid]['pico_id']
# determine the sensor type to use
sensor_type = global_settings[my_uuid]['sensor_type']
# get gpio pin if present
try:
    gpio = global_settings[my_uuid]['gpio']
except KeyError:
    # guess 22 if not present... not relevant for bme280
    gpio = 22

# secrets (wifi password etc.)
secrets = global_settings[my_uuid]['secrets']

# get a generator to yield readings one at a time
ambient_data = get_ambient_data(iterations=True, sensor_type=sensor_type, gpio=gpio)

ms = mini_server(secrets=secrets, rp2=rp2, not_found_response=wrap_route(not_found, pico_id=pico_id))
ms.connect_to_wifi()

# add routes and handlers
ms.add_route(('data',), wrap_route(ambient_data_readings, ambient_data=ambient_data, pico_id=pico_id, sensor_type=sensor_type, pico_uuid=my_uuid))
ms.add_route(('find',), wrap_route(identify_myself, pico_id=pico_id))

# start listening
ms.listen()
