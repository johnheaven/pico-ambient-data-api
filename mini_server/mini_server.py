import rp2, uasyncio

class mini_server():
    # code for request/response adapted from https://www.raspberrypi.com/news/how-to-run-a-webserver-on-raspberry-pi-pico-w/
    def __init__(self, secrets: list, callbacks_obj, runtime_params_obj, wlan_country, wdt_timeout=8000, wdt_ping_freq=1500):
        self.secrets = secrets
        
        # steal methods from callback_obj
        self._get_callbacks = callbacks_obj.get_callbacks
        self._fire_callback = callbacks_obj.fire_callback
        self._add_route_or_callback = callbacks_obj.add_callback
        self._merge_runtime_params = callbacks_obj.merge_runtime_params

        # steal methods from runtime_params_obj
        self._add_runtime_param = runtime_params_obj.add_runtime_param
        self._get_runtime_param = runtime_params_obj.get_runtime_param
        self._merge_runtime_params = callbacks_obj.merge_runtime_params

        # the handler for 404 not found - start() will throw an error if this is still empty by the time it's called
        self.not_found_response = tuple()
        
        # wifi connection data/setup
        rp2.country(wlan_country)

        self._wdt_timeout = wdt_timeout
        self._wdt_ping_freq = wdt_ping_freq

        # make fire_callback method available as runtime param
        if callbacks_obj is not None: self._add_runtime_param('fire_callback', self._fire_callback)

        # make add_runtime_param available as runtime param
        # TODO: Wouldn't it make sense just to pass these into every handler by default?
        if runtime_params_obj is not None:
            self._add_runtime_param('add_runtime_param', self._add_runtime_param)
    
    def start(self):
        """
        The method that fires up the mighty machine that is the webserver.
        """
        import machine
        from utime import sleep, time

        ### CHECK FOR 404 NOT FOUND ROUTE/HANDLER ###
        if self.not_found_response == tuple(): raise RuntimeError("No 404 response defined... use mini_server.add_route() with route == '_not_found_'")

        ### CONNECT TO WLAN NETWORK ###
        self._fire_callback('wlan_starting_to_connect')

        wlan = self._turn_on_wlan()

        # attempt to connect to a wifi network
        # 1. get a list of (repeated) secrets - i.e. try each SSID/password combination 4 times
        secrets_repeated = [self.secrets] * 4

        # 2. keep cycling through them until the list is empty or we have a connection
        wlan_connected = False
        while len(secrets_repeated) > 0 and wlan_connected == False:
            print(f'Connecting to WLAN... tries {len(secrets_repeated)} left')
            secrets = self.secrets.pop()
            print(f'Attempting to connect to {secrets["ssid"]}')
            wlan_connected = self._connect_to_wlan(wlan, secrets)

        if wlan_connected:
            print(f'Connected to {self._get_runtime_param("current_ssid")}')
            print(f'Host IP: {self._get_runtime_param("wlan_ip")}')
        else:
            # go to sleep for 10 minutes and try again later
            print(f'Couldn\'t connect so sleeping for 10 mins before restarting...')
            machine.deepsleep(600)

        # 3. connect to socket
        s = self._open_socket()

        # 4. listen for connections and do things when we have them
        s.listen(1)

        loop = uasyncio.get_event_loop()

        loop.create_task(self.run(s))

    def _turn_on_wlan(self):
        import network
        from utime import sleep_ms

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

        # add IP as placeholder parameter - it sometimes reports 0.0.0.0 so keep trying n times until it comes back with a useful value
        attempts = 20
        while True and attempts:
            attempts -= 1
            wlan_ip = wlan.ifconfig()[0]
            if wlan_ip != '0.0.0.0': break
            sleep_ms(10)
        
        self._add_runtime_param('wlan_ip', wlan_ip) #type: ignore "possibly unbound" variable error
        self._fire_callback('wlan_active')
        return wlan

    def _connect_to_wlan(self, wlan, secrets: dict, max_wait: int=30):
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
        import machine

        # connect to the ssid
        wlan.connect(secrets['ssid'], secrets['wifi_pw'])
        # max_wait is number of seconds to wait in total
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() > 3 or wlan.status() == network.STAT_GOT_IP:
                    # add callback to disconnect on fatal error
                    self.add_callback('fatal_error', lambda **params: wlan.disconnect())
                    # register useful runtime parameters
                    self._add_runtime_param('host_ip', wlan.ifconfig)
                    self._add_runtime_param('current_ssid', wlan.config('ssid'))

                    self._fire_callback('wlan_connected')

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

    def _open_socket(self):
        import usocket as socket
        # Open socket
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        s = socket.socket()
        
        # Without SO.REUSEADDDR, you get an OSError: [Errno 98] EADDRINUSE error which is a pain when restarting during debugging. 
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)

        print('listening on', addr)

        return s
 
    async def run(self, s):
        while True:
            try:
                cl, addr = s.accept()
                # get a generator for the request
                request = self._request_gen(cl)
                # get the handlers (functions) for this request
                handlers = self._get_route_handlers(request)
                self._respond_with_route_handlers(cl, handlers)
                cl.close()

            except (OSError, KeyboardInterrupt) as e:
                s.close()
                if isinstance(e, OSError):
                    self._fire_callback('fatal_error')
                    print(e)
                    
                print('Connection closed')
                print(e)

    def _get_route_handlers(self, request) -> tuple:
        """Gets the handlers for the route that has been requested, and substitutes the runtime params

        Args:
            cl (Socket): connection object
            request (Iterator): the request generator

        Returns:
            tuple: The routes to be called for response
        """

        # get route and query parameters
        parsed_request = self._parse_request(request)
        # check that it hasn't returned False, meaning it failed to parse
        if parsed_request:
            _, route, _, _, _ = parsed_request
        else:
            # TODO A route for server error
            route = '_not_found_'

        # get a tuple of tuples with route name, handler function, default params, runtime params
        route_handlers = self._get_callbacks(route, kind='route')

        # substitute 404 response if empty
        route_handlers = route_handlers if len(route_handlers) else (self.not_found_response,)

        # merge the default params with any available runtime params
        route_handlers = self._merge_runtime_params(route_handlers)

        return route_handlers

    def _respond_with_route_handlers(self, cl, route_handlers: tuple) -> bool:
        """Takes a tuple with the tuples of routes/handlers. Each one gets called in succession, with the kwargs passed in.

        Args:
            cl (socket): The client connection
            route_handlers (tuple): A tuple of tuples, each containing the route name, function, and params.

        Returns:
            bool: _description_
        """
        # Call each handler in succession
        for route_handler in route_handlers:
            print('DEBUG: route_handler = ', route_handler)
            _, handler_func, handler_params = route_handler
            # execute the handler and get a header and response
            header, response_generator = handler_func(**handler_params)
            # send the header
            cl.send(header)
            # send the response
            for chunk in response_generator:
                # print('DEBUG: chunk = \n', chunk)
                total_bytes = len(chunk)
                sent_bytes = 0
                while sent_bytes < total_bytes:
                    sent_bytes = cl.write(chunk[sent_bytes:])
        return True
    
    def _parse_request(self, request):
        from helpers.bits_and_bobs import next

        # get a generator that yields lines of utf-8 decoded text
        request_lines = self._request_lines_gen(request)
        #print('DEBUG: first 2 items in request_lines = ', next(request_lines) + '\n' + next(request_lines))

        # get first line from the request (generator) unless it's empty, in which case we return
        current_line = next(request_lines, False)
        if not current_line: return False

        print('DEBUG: current_line = ', current_line)
        # get the method (GET or POST), query (e.g. http://192.168.2.153/.../update)
        # and protocol (e.g. HTTP/1.1) from first line only
        method, query, protocol = [item.strip() for item in current_line.split(' ')]
        #print('DEBUG: method, query, protocol = ', (method, query, protocol))

        # get the route (e.g. /data) and query string (e.g. pico_name=test+name&ssid=blah+blah&wifi_pass=testpass&sensor=on)
        route, _, query_string = query.partition('?')
        
        # remove trailing slash from route, unless it's just /
        route = '/' + route.strip('/')
        #print('DEBUG: route = ', route)
        
        ### QUERY PARAMETERS -> NOT PROPERLY SUPPORTED BECAUSE MICROPYTHON DOESN'T HAVE URLLIB, SO WE CAN'T DECODE THEM ###
        if query_string:
            # split out each parameter
            parameters = query_string.split('&')
            # get a dictionary of parameters by splitting each parameter on the = sign
            query_parameters = {parameter.split('=')[0]: parameter.split('=')[1] for parameter in parameters}
        else:
            query_parameters = None
        
        ### POST DATA -> WE CURRENTLY ASSUME THAT ALL POST REQUESTS ARE FORMS ###
        form_data = self._form_data_gen(current_line, request_lines) if method == 'POST' else None

        # make them available for everyone... might cause problems if concurrent requests are ever added!
        self._add_runtime_param('route', route)
        self._add_runtime_param('query_parameters', query_parameters)
        self._add_runtime_param('form_data', form_data)

        return method, route, query_parameters, form_data, protocol

    def _form_data_gen(self, current_line: str, request_lines):
        """A generator for lazy-parsing form data

        Args:
            current_line (str): The current line the request_generator is on (should have been previously captured)
            request_lines (generator): The generator for yielding the request line by line as strings

        Yields:
            (key, value) (tuple): A tuple containing key, value of form data
        """
        import ure as re

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
        
        # get Content Type (if it exists)
        current_line, request_lines, content_type_found = self._scroll_to(current_line, request_lines, 'Content-Type')

        content_type = ''
        if content_type_found:
            _, _, content_type = current_line.partition(': ')

        # if it's a multipart form (i.e. not urlencoded) then we're in business...
        if content_type_found and content_type[:19] == 'multipart/form-data':
            #print('DEBUG: multipart data')
            # get the boundary (i.e. the string that separates form entries)
            boundary = content_type.partition('; ')[2][9:].strip()
            #print('DEBUG: boundary = \n' + boundary)
            # the separator is different from the end... subtle but crucial
            field_sep = '--' + boundary
            form_end = '--' + boundary + '--'
            
            # move to first field
            current_line, request_lines, content_type_found = self._scroll_to(current_line, request_lines, field_sep)
            
            # get a regex for finding the key
            re_key = re.compile('^Content-Disposition: form-data; name="(.*)"\s*$')

            while form_end not in current_line:
                #print('DEBUG: outer loop (reading fields)')
                current_line = next(request_lines)
                #print('DEBUG: current_line \n', current_line)
                
                # get key and value. key is just in first line, value is any following data (up to next boundary)
                key = re_key.match(current_line).groups()[0]
                current_line = next(request_lines)
                value = ''
                while field_sep not in current_line:
                    #print('DEBUG: inner loop (reading lines)')
                    value += current_line
                    current_line = next(request_lines)
                #print('DEBUG: yielding (key, value) = \n', (key, value))
                yield key, value
        else:
            # can't deal with urlencoded data as there's no micropython library for decoding it
            # TODO: return an appropriate status code or just ignore -> this would require rewriting
            # TODO: the header parsing, so we don't even enter this function unless it's multipart
            print('Urlencoded data not supported')

    def _scroll_to(self, current_line, request_lines, begins_with):
            #print('DEBUG: Before _scroll_to current_line = ', current_line)
            found = True
            while current_line[:len(begins_with)] != begins_with:
                #if current_line == '': raise ValueError('current_line empty')
                try:
                    current_line = next(request_lines)
                    #print('DEBUG: current_line[:len(begins_with)] = ', current_line[:len(begins_with)])
                    #print('DEBUG: current_line = ', current_line)
                except StopIteration:
                    found = False
                    break
            #print('DEBUG: After _scroll_to current_line = ', current_line)
            return current_line, request_lines, found

    def add_route(self, route: str, handler, params: dict={}, runtime_params: tuple=tuple()):
        if route == '_not_found_': self.not_found_response = (route, handler, params, runtime_params)
        return self._add_route_or_callback(route, 'route', handler, params, runtime_params)

    def add_callback(self, callback_id: str, handler, params: dict={}, runtime_params: tuple=tuple()):
        return self._add_route_or_callback(callback_id, 'callback', handler, params, runtime_params)

    # receive up to 1024 bytes at a time and store the result as a string
    def _request_gen(self, cl, bytes=1024):
        """
        A generator that returns chunks of the http request
        """
        while True:
            data = cl.recv(bytes)
            #print('DEBUG: Received data...\n')
            if len(data):
                yield data
            else:
                break

    def _request_lines_gen(self, request, terminator='\r\n'):
        """
        A generator that returns the request line for line
        """

        next_line = ''
        chunk = ''
        
        while True:
            # consume chunk line by line until there are no line-breaks left
            if terminator in chunk:
                next_line, _, chunk = chunk.partition(terminator)
                #print('DEBUG: yielding utf-8 next_line = ', next_line)
                yield next_line
            else:
                try:
                    chunk += next(request).decode('utf-8')
                except StopIteration as e:
                    break
        if len(chunk) > 0:
            #print('DEBUG: yielding utf-8 chunk = ', chunk)
            yield chunk
