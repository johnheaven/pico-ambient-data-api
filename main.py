from ambient_data.ambient_data import get_ambient_data
from mini_server.mini_server import mini_server
from helpers.bits_and_bobs import device_uuid_string
from helpers import settings_management as sttgs
from mini_server.handlers import *

# get the UUID of this machine
my_uuid = device_uuid_string()
# give this Pico an id so it can be found over the network

settings = sttgs.settings_wrapper()

pico_id = settings['pico_id']
# determine the sensor type to use
sensor_type = settings['sensor_type']
# secrets (wifi password etc.)
secrets = settings['secrets']

# get a generator to yield readings one at a time
ambient_data = get_ambient_data(iterations=True, sensor_type=sensor_type)

ms = mini_server(
    secrets=secrets,
    not_found_response=('_placeholder_', not_found, {'pico_id': pico_id})
    )
    
# add routes and handlers
ms.add_route(
    route='/data',
    handler=ambient_data_readings,
    params={
        'ambient_data': ambient_data,
        'pico_id': pico_id,
        'sensor_type': sensor_type,
        'pico_uuid': my_uuid}
    )

ms.add_route(
    route='/find',
    handler=identify_myself,
    params={'pico_id': pico_id}
    )

ms.add_route(
    route='/update',
    handler=update_settings_form,
    params={
        'pico_name':'test name',
        'ssid_name': 'blah blah',
        'wifi_pass': 'testpass',
        'bme280_checked': 'checked',
        'dht22_checked': ''}
)

ms.add_route(
    route='/save-settings',
    handler=save_settings,
    params={}
)

ms.connect_to_wifi()

# start listening
ms.listen()
