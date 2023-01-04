from phew.phew import server, connect_to_wifi
from phew.phew import logging


from ambient_data.ambient_data import get_ambient_data
from helpers.bits_and_bobs import device_uuid_string, led_notify
import helpers.state as state
from helpers import settings_management as sttgs
import handlers
from callbacks.callbacks import Callbacks
import gc, machine, uasyncio

### SETUP ###

# an object for notifications via built-in LED
ln = led_notify()

# a callbacks object for communication between various objects
callbacks = Callbacks()

### GET SETTINGS ###
# get the UUID of this machine
pico_uuid = device_uuid_string()

settings = sttgs.settings_wrapper()
logging.debug(f'Settings: {settings}')

### GET SENSOR DATA GENERATOR ###

# get a generator to yield readings one at a time – revert sensor to 'none' if we get an IOError
# and change this in the settings too
try:
    ambient_data_gen = get_ambient_data(iterations=True, sensor_type=settings['sensor'], gpio=settings['gpio'], sda_pin=settings['sda'], scl_pin=settings['scl'])
except Exception as e:
    if isinstance(e, OSError):
        ambient_data_gen = get_ambient_data(iterations=True, sensor_type='none')
        settings['sensor'] = 'none'
        sttgs.write_settings(settings)
    elif isinstance(e, KeyError):
        print(e)
    else:
        raise(e)

state.state['ambient_data_gen'] = ambient_data_gen

# this is a function so we can re-call it when settings get updated
def update_state_from_settings():
    logging.info('Updating state from settings')
    state.state['pico_id'] = settings['pico_id']
    state.state['wifi_pw'] = settings['wifi_pw']

# add callbacks
callbacks.add_callback(callback='wlan_active', handler=ln.flash_once_on)
callbacks.add_callback(callback='wlan_starting_to_connect', handler=ln.on)
callbacks.add_callback(callback='wlan_connected', handler=ln.off)
callbacks.add_callback(callback='cant_connect', handler=lambda **kwargs: ln.flash_twice_off())
callbacks.add_callback(callback='save_settings', handler=update_state_from_settings)

# update state. ssid only updated once on startup
state.state['ssid'] = settings['ssid']
update_state_from_settings()

state.state['pico_uuid'] = pico_uuid
state.state['get_settings_func'] = sttgs.settings_wrapper
state.state['write_settings_func'] = sttgs.write_settings
state.state['possible_sensors'] = sttgs.possible_sensors
state.state['fire_callback_func'] = callbacks.fire_callback

logging.debug(state.state['get_settings_func']())
logging.debug(state.state['get_settings_func']())

### START WIFI AND CONNECT TO NETWORK ###
callbacks.fire_callback('wlan_starting_to_connect')
print('IP address: ', connect_to_wifi(state.state['ssid'], state.state['wifi_pw']))
callbacks.fire_callback('wlan_connected')

### INSTANTIATE THE SERVER AND SET IT UP ###

server.run()