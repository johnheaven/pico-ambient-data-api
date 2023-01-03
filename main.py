from phew.phew import server, connect_to_wifi
from phew.phew.template import render_template

from ambient_data.ambient_data import get_ambient_data
from helpers.bits_and_bobs import device_uuid_string, led_notify, RuntimeParams, start_wdt
from helpers import settings_management as sttgs
import handlers
from callbacks.callbacks import Callbacks
import gc, machine, uasyncio

### SETUP ###

# set threshold for garbage collection
gc.threshold(50000)

# an object for notifications via built-in LED
ln = led_notify()

# a common store for runtime parameters (i.e. parameters that are not available when starting the server but become available later)
runtime_params = RuntimeParams()

# a callbacks object for communication between server and other objects. valid kinds are 'route' and 'callback'
callbacks = Callbacks(runtime_params_obj=runtime_params)

### GET SETTINGS ###
# get the UUID of this machine
pico_uuid = device_uuid_string()

settings = sttgs.settings_wrapper()

runtime_params.add_runtime_param('pico_id', settings['pico_id'])
sensor_type = settings['sensor']



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

# add callbacks
callbacks.add_callback(callback='wlan_active', handler=ln.flash_once_on, params={})
callbacks.add_callback(callback='wlan_starting_to_connect', handler=ln.on, params={})
callbacks.add_callback(callback='wlan_connected', handler=ln.off, params={})
callbacks.add_callback(callback='cant_connect', handler=lambda **kwargs: ln.flash_twice_off(), params={})

### START WIFI AND CONNECT TO NETWORK ###
print('IP address: ', connect_to_wifi(settings["ssid"], settings["wifi_pw"]))

### INSTANTIATE THE SERVER AND SET IT UP ###

# add the "404 not found" route


# add all other routes and handlers
# ms.add_route(
#     route='/data',
#     handler=handlers.ambient_data_readings,
#     params={
#         'ambient_data': ambient_data_gen,
#         'get_settings_func': sttgs.settings_wrapper,
#         'pico_uuid': pico_uuid}
#     )

# ms.add_route(
#     route='/find',
#     handler=handlers.identify_myself,
#     runtime_params=('pico_id',)
#     )

# ms.add_route(
#     route='/hard-reset',
#     handler=handlers.hard_reset,
#     params={}
# )

# ms.add_route(
#     route='/',
#     handler=handlers.overview,
#     params={
#         'ambient_data': ambient_data_gen,
#         },
#     runtime_params=('current_ssid', 'pico_id')
# )

# ms.add_route(
#     route='/settings',
#     handler=handlers.settings,
#     params={
#         'get_settings_func': sttgs.settings_wrapper,
#         'write_settings_func': sttgs.write_settings,
#         'possible_sensors': sttgs.possible_sensors
#     },
#     runtime_params=('form_data', 'current_ssid', 'pico_id', 'fire_callback')
# )

# ms._add_runtime_param('pico_id', pico_id)

# # start_wdt()

# ms.start()

# loop = uasyncio.get_event_loop()
# loop.run_forever()

server.run(callbacks=callbacks, runtime_params=runtime_params)