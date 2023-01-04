possible_sensors = ('bme280', 'dht22', 'none')

def settings_wrapper():
    """
    Check whether settings exist in `settings.json`
    * if yes, get them from read_settings() and return them
    * if no, get wifi settings from read_initial_wifi_settings(), write
      them with write_settings(), then return them
    """

    settings = read_settings()

    if not settings:
        # cobble together settings then write them to settings file if we haven't got any
        print('reading setup wifi settings from wifi.txt')
        ssid, wifi_pw = read_initial_wifi_settings()
        settings = {
            'pico_id': 'setup',
            'sensor': 'none',
            'gpio': 0,
            'sda': 20,
            'scl': 17,
            'ssid': ssid,
            'wifi_pw': wifi_pw
        }
        write_settings(settings)
    
    return settings

def read_settings():
    """
    Read settings from settings.json and return them.
    """
    import json, os

    # Check whether settings exist at all
    if not 'settings.json' in os.listdir():
        return None

    with open('settings.json', mode='r') as f:
        settings = json.load(f)
    return settings

def read_initial_wifi_settings() -> tuple:
    """
    Load wifi settings from wifi.txt.
    Returns tuple of `ssid` and `wifi_pw`
    """
    with open('wifi.txt', 'r') as f:
        ssid = f.readline().strip()
        wifi_pw = f.readline().strip()
    
    return ssid, wifi_pw

def write_settings(settings: dict) -> None:
    """
    Serialise settings as JSON and save to file.

    Args:
        settings (dict): Dictionary containing settings to write to disk.
    """
    import json
    with open('settings.json', mode='w') as f:
        json.dump(settings, f)

