possible_sensors = ('bme280', 'dht22', 'none')

def settings_wrapper():
    """
    Check whether settings exist in `settings.json`
    * if yes, get them from read_settings() and return them
    * if no, get wifi settings from read_initial_wifi_settings(), write
      them with write_settings(), then return them
    """

    settings = read_settings()

    if settings is False:
        # cobble together settings then write them to settings file if we haven't got any
        print('reading setup wifi settings from wifi.txt')
        ssid, wifi_pw = read_initial_wifi_settings()
        settings = {
            'pico_id': 'setup',
            'sensor': 'none',
            'gpio': 0,
            'ssid': ssid,
            'wifi_pw': wifi_pw
        }
        write_settings(settings)
    
    return settings

def read_settings():
    """
    Read settings from settings.json and return them. Tries 3 times.
    """
    import json, time, os

    # Check whether settings exist at all
    if not 'settings.json' in os.listdir():
        return False

    attempts = 3
    while True:
        try:
            with open('settings.json', mode='r') as f:
                settings = json.load(f)
        except OSError:
            attempts -=1
            if attempts:
                print('OSError, sleeping 2s before retrying')
                time.sleep(2)
            else:
                print('OSError, failed 3 times')
                return False
        else:
            return settings

def read_initial_wifi_settings():
    """
    Try to load wifi settings from wifi.txt.
    Returns `ssid` and `wifi_pw`
    """
    import os, machine
    
    # get wifi.txt regardless of capitalisation
    filenames = os.listdir()
    try:
        filename_index = [filename.lower() for filename in filenames].index('wifi.txt')
    except ValueError:
        print('Not much to do... we don\'t have any initial wifi settings.')
        raise ValueError
    
    initial_settings_filename = filenames[filename_index]
    
    with open(initial_settings_filename, 'r') as f:
        ssid = f.readline().strip('\n')
        wifi_pw = f.readline().strip('\n')
    
    return ssid, wifi_pw

def write_settings(settings):
    """
    Serialise settings as JSON and save to file. Tries 3 times.

    Args:
        settings (dict): Dictionary containing settings to write to disk.
    """
    import json, time

    attempts = 3
    while True:
        try:
            with open('settings.json', mode='w') as f:
                settings = json.dump(settings, f)
        except OSError:
            attempts -=1
            if attempts:
                print('OSError, sleeping 2s before retrying')
                time.sleep(2)
            else:
                print('OSError, failed 3 times')
                return False
        else:
            return True

def delete_settings():
    """
    Deletes settings. Tries 3 times.

    Returns:
        bool: True if successful, False if fails
    """
    import os, time
    attempts = 3
    while True:
        try:
            os.remove('settings.json')
        except OSError:
            attempts -=1
            if attempts:
                print('OSError, sleeping 2s before retrying')
                time.sleep(2)
            else:
                print('OSError, failed 3 times')
                return False
        else:
            return True
