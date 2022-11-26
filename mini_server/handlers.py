def handler(f):
    def wrapped_handler(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapped_handler

@handler
def identify_myself(*args, **kwargs):
    from helpers.bits_and_bobs import device_uuid_string
    unique_id = device_uuid_string()
    
    header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
    response = f"<html><body<><h1>{kwargs['pico_id']}</h1><p>It's me!</p><p>Unique ID: {unique_id}</p></body></html>"
    return header, response

@handler
def ambient_data_readings(*args, **kwargs):
    import json
    # kwargs['ambient_data'] is the ambient_data generator
    # kwargs['get_settings_func'] is the function for getting current settings

    settings = kwargs['get_settings_func']()

    return_data = list(next(kwargs['ambient_data']))
    return_data.append(settings['pico_id'])
    return_data.append(settings['sensor'])
    return_data.append(kwargs['pico_uuid'])
    return_data = dict(zip(('temp', 'pressure', 'humidity', 'pico_id', 'sensor', 'pico_uuid'), return_data))
    
    header = 'HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n'
    response = json.dumps(return_data)
    return header, response

@handler
def not_found(*args, **kwargs):
    # 404
    pico_id = kwargs['pico_id']

    header = 'HTTP/1.0 404 Not Found\r\nContent-type: text/html\r\n\r\n'
    response = f'<html><body><h1>{pico_id}</h1><p>404: Resource not found.</p></body></html>'
    return header, response

@handler
def update_settings_form(*args, **kwargs):
    # update settings e.g. wifi

    # a list of fields we need for the template. we add sensor as a special case later on
    fields =[
        'pico_id',
        'ssid',
        'wifi_pw',
        ]
    
    # get settings from the get_settings_func passed in as a kwargs parameter
    settings = kwargs['get_settings_func']()

    possible_sensors = kwargs['possible_sensors']

    # the replacements we'll insert into the template
    replacements = {key: (settings[key] if key in settings.keys() else '') for key in fields}

    # add current_ssid
    replacements['current_ssid'] = kwargs['current_ssid']

    for sensor in possible_sensors:
        replacements[sensor + '_checked'] = 'checked' if settings['sensor'] == sensor else ''

    print('DEBUG: replacements = \n' + str(replacements))

    # we need a header
    header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'

    # open the template and substitute the replacements
    with open('mini_server/templates/update.html', mode='r') as template:
        response = '\n'.join(list(template)).format(**replacements)
    return header, response

@handler
def save_settings(*args, **kwargs):
    # get current settings
    # merge with new settings
    # write settings to disk

    current_settings = kwargs['get_settings_func']()
    new_settings = kwargs['form_data']

    kwargs['write_settings_func'](new_settings)

    header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'

    response = f"""
    Current settings:
    {current_settings}
    <br><br>
    New settings:
    {new_settings}
    """

    return header, response
    