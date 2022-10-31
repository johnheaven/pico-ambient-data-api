### Rename this to settings.py and fill in your own settings

global_settings = {}
global_settings_spareroom = {}

global_settings_spareroom = {
    'sensor_type': 'dht22',
    'pico_id': 'spare bedroom',
    'secrets': [
        {
            'ssid': '[SSID]',
            'pw': '[PW]'
        },
        {
            'ssid': '[SSID-2]',
            'pw': '[PW-2]'
        }
    ]
}

global_settings_bedroom = {
    'sensor_type': 'bme280',
    'pico_id': 'bedroom',
    'secrets': [
        {
            'ssid': '[SSID]',
            'pw': '[PASSWORD]'
        },
        {
            'ssid': '[SSID-2]',
            'pw': '[PASSWORD-2]'
        }
    ]
}

global_settings['UUID-1'] = global_settings_spareroom
global_settings['[UUID-2]'] = global_settings_bedroom