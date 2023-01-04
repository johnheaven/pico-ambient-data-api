
from phew.phew import server
from phew.phew.template import render_template
from phew.phew import logging
import helpers.state as state

def handler(f):
    def wrapped_handler(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapped_handler

@handler
def identify_myself(*args, **kwargs):
    from helpers.bits_and_bobs import device_uuid_string
    unique_id = device_uuid_string()
    
    header = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
    response = (f"<html><body<><h1>{kwargs['pico_id']}</h1><p>It's me!</p><p>Unique ID: {unique_id}</p></body></html>",)
    return header, response

@server.route(path='/data', methods=['GET'])
def ambient_data_readings(request):
    import json

    settings = state.state['get_settings_func']()

    return_data = list(next(state.state['ambient_data_gen']))
    return_data.append(settings['pico_id'])
    return_data.append(settings['sensor'])
    return_data.append(state.state['pico_uuid'])
    return_data = dict(zip(('temp', 'pressure', 'humidity', 'pico_id', 'sensor', 'pico_uuid'), return_data))
    
    return server.Response(body=json.dumps(return_data), headers={'Content-Type': 'application/json'})

@server.catchall()
def not_found(request):
    # 404
    pico_id = state.state['pico_id']
    return server.Response(body=f'<html><body><h1>{pico_id}</h1><p>404: Resource not found.</p></body></html>', status=404)

@server.route('/', methods=['GET'])
def overview(request):

    ### INITIALISE REPLACEMENTS I.E. VALUES WE INSERT INTO TEMPLATE
    replacements = {}

    ### HEADER ###
    logging.debug(state)
    replacements['pico_id'] = state.state['pico_id']

    # add ssid
    replacements['ssid'] = state.state['ssid']

    ### AMBIENT DATA VALUES ###
    replacements['temp'], replacements['pressure'], replacements['humidity'] = next(state.state['ambient_data_gen'])

    ### RETURN RESPONSE ###
    return render_template(template='/templates/index.html', **replacements)

@server.route('/settings', methods=['GET', 'POST'])
def settings(request):
    # show current settings
    # write new settings if they are submitted

    replacements = {}

    ### SAVE SETTINGS IF SUBMITTED ###
    
    form = request.form

    if len(form):
        logging.info('Saving form settings')
        new_settings = form
        if new_settings['sensor'] in ('dht22', 'bme280'):
            try:
                new_settings['gpio'] = int(form['gpio'])
                new_settings['sda'] = int(form['sda'])
                new_settings['scl'] = int(form['scl'])
            except ValueError as e:
                logging.error('No GPIO/SDA/SCL pin specified')
                print(e)

        # write the settings using the function provided
        logging.debug(f'new settings: {form}')
        state.state['write_settings_func'](new_settings)

        replacements['alert_text'] = 'Settings saved successfully'
        replacements['alert_color'] = 'success'

        # trigger callback
        state.state['fire_callback_func']('settings_saved')

    ### HEADER ###

    # add ssid
    replacements['ssid'] = state.state['ssid']

    ### SETTINGS FORM

    # get settings from the get_settings_func passed in as a kwargs parameter
    settings = state.state['get_settings_func']()
    print(settings)

    # a list of fields we need for the template. we add sensor as a special case later on
    exclude_from_fields = ['sensor']
    fields = filter(lambda item: False if item in exclude_from_fields else True, list(settings.keys()))
    
    # data for sensor radio buttons
    possible_sensors = state.state['possible_sensors']
    for sensor in possible_sensors:
        replacements[sensor + '_checked'] = 'checked' if settings['sensor'] == sensor else ''

    # the replacements we'll insert into the template
    replacements.update({key: (settings[key] if key in settings.keys() else '') for key in fields})

    return render_template(template='templates/settings.html', **replacements)
    #return header, response_generator(templates=('header.html', optional_saved, 'settings.html', 'footer.html'), replacements=replacements)
    
@server.route('/hard-reset', methods=['GET'])
def hard_reset(*args, **kwargs):
    import machine
    machine.reset()
