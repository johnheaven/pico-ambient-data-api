from ambient_data.ambient_data import get_ambient_data
from mini_server.mini_server import mini_server
from helpers.bits_and_bobs import device_uuid_string
from helpers import settings_management as sttgs
from mini_server.handlers import *

# get the UUID of this machine
pico_uuid = device_uuid_string()
# give this Pico an id so it can be found over the network

settings = sttgs.settings_wrapper()

pico_id = settings['pico_id']
# determine the sensor type to use
sensor_type = settings['sensor']
# secrets (wifi password etc.). We build this as a list for legacy reasons (too lazy to rewrite everything at the moment)
secrets = [{'ssid': settings['ssid'], 'wifi_pw': settings['wifi_pw']}]

# get a generator to yield readings one at a time – revert sensor to 'none' if we get an IOError
# and change this in the settings too
try:
    ambient_data = get_ambient_data(iterations=True, sensor_type=sensor_type)
except IOError:
    ambient_data = get_ambient_data(iterations=True, sensor_type='none')
    settings['sensor'] = 'none'
    sttgs.write_settings(settings)

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
        'get_settings_func': sttgs.settings_wrapper,
        'pico_uuid': pico_uuid}
    )

ms.add_route(
    route='/find',
    handler=identify_myself,
    params={'pico_id': pico_id}
    )

ms.add_route(
    route='/',
    handler=overview,
    params={
        'ambient_data': ambient_data,
        'get_settings_func': sttgs.settings_wrapper,
        'possible_sensors': sttgs.possible_sensors
        }
)

ms.add_route(
    route='/save-settings',
    handler=save_settings,
    params={
        'get_settings_func': sttgs.settings_wrapper,
        'write_settings_func': sttgs.write_settings
    }
)

ms.connect()
