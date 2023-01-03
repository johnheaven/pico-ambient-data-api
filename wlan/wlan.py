def turn_on_wlan(callbacks, runtime_params, wlan_country='DE'):
    import network, rp2
    from utime import sleep_ms

    rp2.country(wlan_country)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # add IP as placeholder parameter - it sometimes reports 0.0.0.0 so keep trying n times until it comes back with a useful value
    attempts = 20
    wlan_ip = str()
    while True and attempts:
        attempts -= 1
        wlan_ip = wlan.ifconfig()[0]
        if wlan_ip != '0.0.0.0': break
        sleep_ms(10)
    
    runtime_params.add_runtime_param('wlan_ip', wlan_ip)
    callbacks.fire_callback('wlan_active')
    return wlan

def connect_to_network(secrets, callbacks, runtime_params):
    import machine
    ### CONNECT TO WLAN NETWORK ###
    callbacks.fire_callback('wlan_starting_to_connect')

    wlan = turn_on_wlan(callbacks, runtime_params)

    # attempt to connect to a wifi network
    # 1. get a list of (repeated) secrets - i.e. try each SSID/password combination 4 times
    secrets_repeated = [secrets] * 4

    # 2. keep cycling through them until the list is empty or we have a connection
    wlan_connected = False
    while len(secrets_repeated) > 0 and wlan_connected == False:
        print(f'Connecting to WLAN... {len(secrets_repeated)} tries left')
        secrets = secrets.pop()
        print(f'Attempting to connect to {secrets["ssid"]}')
        wlan_connected = connect_to_wlan(wlan, secrets, callbacks, runtime_params)

    if wlan_connected:
        print(f'Connected to {runtime_params.get_runtime_param("current_ssid")}')
        print(f'Host IP: {runtime_params.get_runtime_param("wlan_ip")}')
    else:
        # go to sleep for 10 minutes and try again later
        print(f'Couldn\'t connect so sleeping for 10 mins before restarting...')
        machine.deepsleep(600)

def connect_to_wlan(wlan, secrets: dict, callbacks, runtime_params, max_wait: int=30):
    """
    Attempts to connect to using the secrets provided. Returns True for success, False for failure.

    Args:
        wlan (WLAN object): The WLAN object returned when connecting to socket
        secrets (dict): WLAN credentials in format {'ssid': [SSID], 'wifi_pw': [WIFI PASSWORD]}
        max_wait (int, optional): Maximum time to wait in seconds before timing out. Defaults to 30.

    Returns:
        bool: True for success, False for failure
    """
    import network
    import utime

    # connect to the ssid
    wlan.connect(secrets['ssid'], secrets['wifi_pw'])
    # max_wait is number of seconds to wait in total
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() > 3 or wlan.status() == network.STAT_GOT_IP:
                # add callback to disconnect on fatal error
                callbacks.add_callback('fatal_error', 'callback', lambda **params: wlan.disconnect(), params={}, runtime_params={})
                # register useful runtime parameters
                runtime_params.add_runtime_param('host_ip', wlan.ifconfig)
                runtime_params.add_runtime_param('current_ssid', wlan.config('ssid'))

                callbacks.fire_callback('wlan_connected')

                return True
        max_wait -= 5
        print(f'waiting for connection to {secrets["ssid"]}...')
        print(f'status = {wlan.status()}')
        utime.sleep(5)

    if wlan.status() != network.STAT_GOT_IP:
        # something went wrong
        print('Couldn\'t connect ...')
        print('Status code received:', wlan.status())
        return False

def open_socket():
    import usocket as socket
    # Open socket
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    
    # Without SO.REUSEADDDR, you get an OSError: [Errno 98] EADDRINUSE error which is a pain when restarting during debugging. 
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)

    print('listening on', addr)

    return s