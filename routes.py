def wrap_route(route_function):
    def wrapped_route_function(*args, **kwargs):
        route_function(*args, **kwargs)
    return wrapped_route_function

@wrap_route
def identify_myself(*args, **kwargs):
    from helpers.helpers import device_uuid_string
    unique_id = device_uuid_string()
    
    cl = args[0]
    cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    cl.send(f"<html><body<><h1>{kwargs['pico_id']}</h1><p>It's me!</p><p>Unique ID: {unique_id}</p></body></html>")

@wrap_route
def ambient_data_readings(cl, **kwargs):
    import json
    # kwargs['ambient_data'] = the ambient_data generator
    return_data = list(next(kwargs['ambient_data']))
    return_data.append(kwargs['pico_id'])
    return_data.append(kwargs['sensor_type'])
    return_data.append(kwargs['pico_uuid'])
    return_data = dict(zip(('temp', 'pressure', 'humidity', 'pico_id', 'sensor', 'pico_uuid'), return_data))
    cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n')
    cl.send(json.dumps(return_data))

@wrap_route
def not_found(cl, *args, **kwargs):
    # 404
    cl.send('HTTP/1.0 404 Not Found\r\nContent-type: text/html\r\n\r\n')
    cl.send(f'<html><body><h1>{kwargs['pico_id']}</h1><p>404: Resource not found.</p></body></html>')

@wrap_route
def update_settings(cl, *args, **kwargs):
    # update settings e.g. wifi
    template_list = []
    replacements = {'pico_name': 'test name', 'ssid_name': 'blah blah', 'wifi_pass': 'testpass', 'bme280_checked': 'checked', 'dht22_checked': ''}

    with open('templates/update.html', mode='r') as template:
        cl.send("\n".join(list(template)).format(**replacements))
