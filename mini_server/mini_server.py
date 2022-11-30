class mini_server():
    # code for request/response adapted from https://www.raspberrypi.com/news/how-to-run-a-webserver-on-raspberry-pi-pico-w/
    def __init__(self, secrets: list, not_found_response: tuple, response_timeout=5, device_uuid: str=''):
        import rp2
        
        self.secrets = secrets
        self.routes = []
        self.callbacks = {}
        self.not_found_response = not_found_response
        self.current_route = ''
        self.response_timeout = response_timeout

        # if we have a UUID, then let's be havin' it!
        self.device_uuid = device_uuid

        # wifi connection data/setup
        rp2.country('DE')
    
    def connect(self):
        import network
        import socket
        import utime
        import machine

        ### activate WLAN on device
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        # try each network 4 times

        ### try to connect - cycle through available secrets
        self.fire_callback('wifi_starting_to_connect')
        
        # get long list of (repeated) secrets - i.e. try each SSID/password combination 4 times
        secrets_repeated = self.secrets * 4
        current_ssid = ''

        # keep cycling through them until the list is empty
        while len(secrets_repeated) > 0:
            # get one of the ssid-password pairs
            secret = secrets_repeated.pop(0)
            # connect to the ssid
            self.wlan.connect(secret['ssid'], secret['wifi_pw'])
            # wait for connect or fail
            # max_wait is number of seconds to wait in total
            max_wait = 20
            while max_wait > 0:
                # keep waiting for specified amount of time
                if self.wlan.status() < 0 or self.wlan.status() > 3 or self.wlan.status() == network.STAT_GOT_IP: break
                max_wait -= 1
                print(f'waiting for connection to {secret["ssid"]}...')
                print(f'status = {self.wlan.status()}')
                utime.sleep(5)

            if self.wlan.status() != network.STAT_GOT_IP:
                # something went wrong
                print('Couldn\'t connect ...')
                print('Status code received:', self.wlan.status())
                # if we've got no more networks to try, then sleep 10 mins before resetting the machine
                # so we can start again
                if len(secrets_repeated) == 0:
                    self.fire_callback('cant_connect')
                    print('Network connection failed')
                    print('Deep sleeping for 10 mins then trying again...')
                    machine.deepsleep(600)
                else:
                    utime.sleep(5)
            else:
                # save ssid name for later use
                current_ssid = secret['ssid']
                self.fire_callback('wifi_connected')
                print(f'Connected to: {secret["ssid"]}')
                status = self.wlan.ifconfig()
                print( 'ip = ' + status[0] )
                secrets_repeated = []

        # Open socket
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]  # type: ignore
        
        self.open_socket = socket.socket()  # type: ignore
        
        # these two lines make it easier to debug - you don't have to hard reset the Pico
        # every time you want to restart. (Without this, you get an OSError: [Errno 98] EADDRINUSE error) 
        self.open_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #type:ignore
        self.open_socket.bind(addr)

        print('listening on', addr)

        # needs work - this is more functional than object oriented...
        self.listen(current_ssid)

    def listen(self, current_ssid):
        import machine
        from utime import sleep
        # Listen for connections
        s = self.open_socket
        s.listen(1)
        while True:
            try:
                cl, addr = s.accept()
                
                cl.settimeout(1)

                # receive up to 1024 bytes at a time and store the result as a string
                requests = []
                while True:
                    try:
                        #print('DEBUG: Trying to receive data...')
                        data = cl.recv(1024)
                        #print('DEBUG: Received data...\n' + data)
                    except:
                        #print('DEBUG: No more data...')
                        break
                    else:
                        #print('DEBUG: Appending data...')
                        requests.append(data)
                
                #print('DEBUG: FINISHED receiving data')
                request = b''.join(requests)
                
                # don't bother if there isn't a reasonable request
                if len(request) == 0: continue

                # decode the request to string from bytes
                current_request_str = str(request.decode('utf-8'))
                    
                #print('DEBUG: request_string = \n' + current_request_str)

                self.__handle_routes(cl, current_request_str, current_ssid)
                
                cl.close()

            except (OSError, KeyboardInterrupt) as e:
                if isinstance(e, OSError):
                    raise e
                elif isinstance(e, KeyboardInterrupt):
                    s.close()
                    self.wlan.disconnect()
                    print('Connection closed')
                    raise e

    def add_route(self, route: str, handler, params: dict={}):
        # list of tuples of routes (i.e. strings) and handlers (i.e. functions)
        self.routes.append(
            (route, handler, params)
        )

    def add_callback(self, event: str, callback: tuple) -> None:
        # add callback function to the list for the appropriate key within the dictionary
        self.callbacks.setdefault(event, []).append(callback)

    def fire_callback(self, event, more_params={}):
        # get the callback function and parameters, or return a dummy function
        if event in self.callbacks.keys():
            current_callbacks = self.callbacks[event]
            for callback in current_callbacks:
                # merge the params from the callback with more_params (more_params take precedence)
                more_params.update(callback[1])
                # fire the callback with all the parameters
                callback[0](**more_params)
    
    def __handle_routes(self, cl, current_request_str, current_ssid):
        # cl is the client

        # get route and query parameters
        _, route, query_parameters, form_data, _ = self.__parse_request_string(current_request_str)

        #print('DEBUG: request on route: ', route)

        # get the handler function and the default params we need to pass in
        route_handlers = self.__get_handlers(route)

        for route_handler in route_handlers:
            _, handler_func, handler_params = route_handler
            #print('DEBUG: route_handler = ', route_handler)
            # execute the handler and get a header and response
            header, response_generator = handler_func(**handler_params, query_parameters=query_parameters, form_data=form_data, current_ssid=current_ssid)
            # send the header
            cl.send(header)
            # send the response
            for chunk in response_generator:
                # print('DEBUG: chunk = \n', chunk)
                total_bytes = len(chunk)
                sent_bytes = 0
                while sent_bytes < total_bytes:
                    sent_bytes = cl.write(chunk[sent_bytes:])

            cl.close()
    
    def __parse_request_string(self, request_string):
        # micropython regex is severely limited... as if regex wasn't complicated enough.
        # https://docs.micropython.org/en/latest/library/re.html
        # so it's easier to break down the string with built-in string functions.
        #
        # e.g. for 'GET /update/?pico_name=test+name&ssid=blah+blah&wifi_pass=testpass&sensor=on'

        # get a list of lines
        request_string_lines = request_string.split('\n')

        # get the method (GET or POST), query (e.g. http://192.168.2.153/.../update)
        # and protocol (e.g. HTTP/1.1) from first line only
        method, query, protocol = request_string_lines[0].split(' ')

        # get the route (e.g. /data) and query string (e.g. pico_name=test+name&ssid=blah+blah&wifi_pass=testpass&sensor=on)
        route, _, query_string = query.partition('?')
        
        # remove trailing slash from route, unless it's just /
        route = '/' + route.strip('/')
        print('DEBUG: route = ' + route)
        
        if query_string:
            # split out each parameter
            parameters = query_string.split('&')
            # get a dictionary of parameters by splitting each parameter on the = sign
            query_parameters = {parameter.split('=')[0]: parameter.split('=')[1] for parameter in parameters}
        else:
            query_parameters = None
        
        # the thorny issue of POST requests...
        # an example POST request:
        #
        # POST /save-settings HTTP/1.1
        # Host: 192.168.2.153
        # User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:107.0) Gecko/20100101 Firefox/107.0
        # Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
        # Accept-Language: en-GB,en;q=0.5
        # Accept-Encoding: gzip, deflate
        # Content-Type: multipart/form-data; boundary=---------------------------339547375120055923303780590246
        # Content-Length: 543
        # Origin: http://192.168.2.153
        # Connection: keep-alive
        # Referer: http://192.168.2.153/update
        # Upgrade-Insecure-Requests: 1
        #
        # -----------------------------339547375120055923303780590246
        # Content-Disposition: form-data; name="pico_name"

        # test name
        # -----------------------------339547375120055923303780590246
        # Content-Disposition: form-data; name="sensor"

        # on
        # -----------------------------339547375120055923303780590246
        # Content-Disposition: form-data; name="ssid"

        # blah blah
        # -----------------------------339547375120055923303780590246
        # Content-Disposition: form-data; name="wifi_pass"

        # testpass
        # -----------------------------339547375120055923303780590246--
        form_data = None
        if request_string_lines[0][:4] == 'POST':
            _, _, content_type = [line for line in request_string_lines if 'Content-Type' in line[:12]][0].partition(': ')

            # if it's a multipart form (i.e. not urlencoded)
            if content_type[:19] == 'multipart/form-data':
                # get the boundary (i.e. the string that separates form entries)
                boundary = content_type.partition('; ')[2][9:].strip()
                #print('DEBUG: boundary = \n' + boundary)
                # separate original request string now we know the boundary - we need to add '---' to the start
                # we can throw away the first two, and last items:
                # - the first item is everything before the first boundary
                # - the last item is just '--' because the form items end with the boundary + '--'
                form_items = [form_item.rstrip('--') for form_item in request_string.split(boundary)][2:-1]
                # now we need to get a dictionary of field names and contents
                form_data = {}
                for form_item in form_items:
                    key, _, value = form_item.partition('\r\n\r\n')
                    form_data[key[40:-1]] = value.strip()

                print('DEBUG: form_data = \n' + str(form_data))

        return method, route, query_parameters, form_data, protocol

    def __get_handlers(self, route: str):
        # check all route/handler definitions for the one that contain this route
        # and return handler and parameters
        route_handlers = tuple(
            filter(
                lambda route_handler:
                    True if route == route_handler[0] else False,
                self.routes
                )
            )
        
        if len(route_handlers) == 0:
            # append empty dict to not_found_response so return format is consistent
            route_handlers = (self.not_found_response,)

        return route_handlers
