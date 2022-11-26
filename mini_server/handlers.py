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
    # kwargs['ambient_data'] = the ambient_data generator
    return_data = list(next(kwargs['ambient_data']))
    return_data.append(kwargs['pico_id'])
    return_data.append(kwargs['sensor_type'])
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

    # a list of fields we need for the template
    fields =[
        'pico_name',
        'ssid_name',
        'wifi_pass',
        'bme280_checked',
        'dht22_checked'
        ]

    # the replacements we'll insert into the template
    replacements = {key: (kwargs[key] if key in kwargs.keys() else '') for key in fields}

    header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'

    with open('mini_server/templates/update.html', mode='r') as template:
        response = '\n'.join(list(template)).format(**replacements)
    
    return header, response

@handler
def save_settings(*args, **kwargs):
    # get current settings
    # merge with new settings
    # write settings to disk
    query_params = kwargs['query_parameters']
    header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
    response = f"""
    You submitted the following things:
    {query_params}
    """

    return header, response
    