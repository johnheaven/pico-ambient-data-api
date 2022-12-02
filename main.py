from ambient_data.ambient_data import get_ambient_data
from mini_server.mini_server import mini_server
from helpers.bits_and_bobs import device_uuid_string, led_notify, RuntimeParams
from helpers import settings_management as sttgs
from mini_server import handlers
from callbacks.callbacks import Callbacks

### SETUP ###

# an object for notifications via built-in LED
ln = led_notify()

# a common store for runtime parameters (i.e. parameters that are not available when starting the server but become available later)
runtime_params = RuntimeParams()

# a callbacks object for communication between server and other objects. valid kinds are 'route' and 'callback'
callbacks = Callbacks(valid_kinds=('route', 'callback'), runtime_params_obj=runtime_params)

### GET SETTINGS ###
# get the UUID of this machine
pico_uuid = device_uuid_string()

settings = sttgs.settings_wrapper()

pico_id = settings['pico_id']
sensor_type = settings['sensor']

# secrets (wifi password etc.). We build this must be a list for legacy reasons (too lazy to rewrite everything at the moment)
secrets = [{'ssid': settings['ssid'], 'wifi_pw': settings['wifi_pw']}]

# gpio (only relevant for DHT22)
gpio = settings['gpio']

# sda and sdl (BME280 only)
sda_pin, scl_pin = settings['sda'], settings['scl']


### GET SENSOR DATA GENERATOR ###

# get a generator to yield readings one at a time – revert sensor to 'none' if we get an IOError
# and change this in the settings too
try:
    ambient_data_gen = get_ambient_data(iterations=True, sensor_type=sensor_type, gpio=gpio, sda_pin=sda_pin, scl_pin=scl_pin)
except OSError:
    ambient_data_gen = get_ambient_data(iterations=True, sensor_type='none')
    settings['sensor'] = 'none'
    sttgs.write_settings(settings)

### INSTANTIATE THE SERVER AND SET IT UP ###

ms = mini_server(
    secrets=secrets,
    callbacks_obj=callbacks,
    runtime_params_obj=runtime_params
    )

# add callbacks
ms.add_callback(callback_id='wlan_active', handler=ln.flash_once_on)
ms.add_callback(callback_id='wlan_starting_to_connect', handler=ln.on)
ms.add_callback(callback_id='wlan_connected', handler=ln.off)
ms.add_callback(callback_id='cant_connect', handler=lambda **kwargs: ln.flash_twice_off())


# add the "404 not found" route
ms.add_route(
    route='__not_found__',
    handler=handlers.not_found,
    params={'pico_id': pico_id},
    runtime_params=tuple()
    )

# add all other routes and handlers
ms.add_route(
    route='/data',
    handler=handlers.ambient_data_readings,
    params={
        'ambient_data': ambient_data_gen,
        'get_settings_func': sttgs.settings_wrapper,
        'pico_uuid': pico_uuid}
    )

ms.add_route(
    route='/find',
    handler=handlers.identify_myself,
    runtime_params=('pico_id',)
    )

ms.add_route(
    route='/hard-reset',
    handler=handlers.hard_reset,
    params={}
)

ms.add_route(
    route='/',
    handler=handlers.overview,
    params={
        'ambient_data': ambient_data_gen,
        },
    runtime_params=('current_ssid', 'pico_id')
)

ms.add_route(
    route='/settings',
    handler=handlers.settings,
    params={
        'get_settings_func': sttgs.settings_wrapper,
        'write_settings_func': sttgs.write_settings,
        'possible_sensors': sttgs.possible_sensors
    },
    runtime_params=('form_data', 'current_ssid', 'pico_id', 'fire_callback')
)

ms.__add_runtime_param('pico_id', pico_id)

ms.start()
