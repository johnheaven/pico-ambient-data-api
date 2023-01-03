
from phew.phew import server

def handler(f):
    def wrapped_handler(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapped_handler

def response_generator(templates: tuple, replacements: dict, read_bytes=1024, lookahead_bytes=2, template_dir='mini_server/templates/'):
    from ure import compile as re_compile

    # a simple regex to get all instances of {{token}}
    token_re = re_compile('(\{\{(\w*)\}\})')

    for template in templates:
        print('DEBUG: template = ', template)
        if not len(template): continue
        template = open(template_dir + template, mode='rb')
        # initialise chunk with arbitrary text just to make sure the loop starts
        chunk = b'whatever'
        while chunk:
            chunk = template.read(read_bytes - lookahead_bytes).decode('utf-8')
            incomplete_tokens = True
            while incomplete_tokens:
                # look ahead by set number of bytes if necessary to get a full token
                if chunk.count('{{') != chunk.count('}}'):
                    chunk += template.read(lookahead_bytes).decode('utf-8')
                    #print('DEBUG: incomplete tokens')
                else:
                    incomplete_tokens = False
            
            # use regex to do replacement, and yield result
            yield token_re.sub(
                lambda token_match: str(replacements[token_match.groups()[1]]) if token_match.groups()[1] in replacements.keys() else token_match.groups()[0],
                chunk)
        template.close()

@handler
def identify_myself(*args, **kwargs):
    from helpers.bits_and_bobs import device_uuid_string
    unique_id = device_uuid_string()
    
    header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
    response = (f"<html><body<><h1>{kwargs['pico_id']}</h1><p>It's me!</p><p>Unique ID: {unique_id}</p></body></html>",)
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
    return header, (response,)

@server.catchall()
def not_found(request, callbacks, runtime_params):
    # 404
    pico_id = runtime_params.get_runtime_param('pico_id')
    return server.Response(body=f'<html><body><h1>{pico_id}</h1><p>404: Resource not found.</p></body></html>', status=404)

@handler
def overview(*args, **kwargs):

    #print('DEBUG: kwargs = ', kwargs)

    ### INITIALISE REPLACEMENTS I.E. VALUES WE INSERT INTO TEMPLATE
    replacements = {}

    ### HEADER ###
    replacements['pico_id'] = kwargs['pico_id']
    # add current_ssid
    replacements['current_ssid'] = kwargs['current_ssid']

    ### AMBIENT DATA VALUES ###

    replacements['temp'], replacements['pressure'], replacements['humidity'] = next(kwargs['ambient_data'])

    ### RETURN HEADER AND GENERATOR FOR RESPONSE TEMPLATE ###

    # we need a header
    header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
    
    return header, response_generator(templates=('header.html', 'current_data.html', 'footer.html'), replacements=replacements)

@handler
def settings(*args, **kwargs):
    # show current settings
    # write new settings if they are submitted (request type == post, form_data is not empty)

    #print('DEBUG: list(form_data) = \n', list(kwargs['form_data']))

    replacements = {}

    ### SAVE SETTINGS IF SUBMITTED ###

    optional_saved = ''

    if kwargs['form_data'] is not None:
        new_settings = {pair[0]: pair[1].strip() for pair in kwargs['form_data']}

        new_settings['gpio'] = int(new_settings['gpio'])
        new_settings['sda'] = int(new_settings['sda'])
        new_settings['scl'] = int(new_settings['scl'])

        kwargs['write_settings_func'](new_settings)

        optional_saved = 'alert.html'

        replacements['alert_text'] = 'Settings saved successfully'
        replacements['alert_color'] = 'success'

        # trigger callback
        kwargs['fire_callback']('settings_saved')

    ### HEADER ###

    # add current_ssid
    replacements['current_ssid'] = kwargs['current_ssid']

    ### SETTINGS FORM

    # get settings from the get_settings_func passed in as a kwargs parameter
    settings = kwargs['get_settings_func']()

    # a list of fields we need for the template. we add sensor as a special case later on
    exclude_from_fields = ['sensor']
    fields = filter(lambda item: False if item in exclude_from_fields else True, list(settings.keys()))
    
    # data for sensor radio buttons
    possible_sensors = kwargs['possible_sensors']
    for sensor in possible_sensors:
        replacements[sensor + '_checked'] = 'checked' if settings['sensor'] == sensor else ''

    # the replacements we'll insert into the template
    replacements.update({key: (settings[key] if key in settings.keys() else '') for key in fields})

    # print('DEBUG: replacements = \n' + str(replacements))

    ### RETURN HEADER AND GENERATOR FOR RESPONSE TEMPLATE ###

    header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'

    return header, response_generator(templates=('header.html', optional_saved, 'settings.html', 'footer.html'), replacements=replacements)
    
@handler
def hard_reset(*args, **kwargs):
    import machine
    machine.reset()
