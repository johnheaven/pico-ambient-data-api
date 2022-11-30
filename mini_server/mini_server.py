class mini_server():
    # code for request/response adapted from https://www.raspberrypi.com/news/how-to-run-a-webserver-on-raspberry-pi-pico-w/
    def __init__(self, secrets: list):
        import rp2
        
        self.secrets = secrets
        
        # routes and callbacks (they're essentially the same entity)
        self.routes = []
        self.callbacks = []

        # the handler for 404 not found - start() will throw an error if this is still empty by the time it's called
        self.not_found_response = tuple()
        
        # placeholder params which can be passed to callbacks when they are available
        self.placeholder_params = {}

        # wifi connection data/setup
        # TODO: write a method to configure this
        rp2.country('DE')
    
    def start(self):
        """
        The method that fires up the mighty machine that is the webserver.
        """

        import machine

        ### CHECK FOR 404 NOT FOUND ROUTE/HANDLER ###
        if self.not_found_response == tuple(): raise RuntimeError("No 404 response defined... use mini_server.add_route() with route == '__not_found__")

        ### CONNECT TO WLAN NETWORK ###
        self.__fire_callback('wifi_starting_to_connect')

        wlan = self.__turn_on_wlan()

        # attempt to connect to a wifi network
        # 1. get a list of (repeated) secrets - i.e. try each SSID/password combination 4 times
        secrets_repeated = self.secrets * 4

        # 2. keep cycling through them until the list is empty or we have a connection
        wlan_connected = False
        while len(secrets_repeated) > 0 and wlan_connected == False:
            print(f'Connecting to WLAN... tries {len(secrets_repeated)} left')
            secrets = self.secrets.pop()
            print(f'Attempting to connect to {secrets["ssid"]}')
            wlan_connected = self.__connect_to_wlan(wlan, secrets)

        if wlan_connected:
            current_ssid = secrets['ssid'] #type: ignore
            print(f'Connected on {current_ssid}')
        else:
            # go to sleep for 10 minutes and try again later
            print(f'Couldn\'t connect so sleeping for 10 mins before restarting...')
            machine.deepsleep(600)

        # connect to socket
        s = self.__open_socket()

        # listen for connections
        s.listen(3)
        while True:
            try:
                cl, addr = s.accept()
                # get a generator for the request
                request = self.__request_gen(cl)
                self.__handle_routes_and_callbacks(cl, request)
                cl.close()

            except (OSError, KeyboardInterrupt) as e:
                s.close()
                self.__fire_callback('fatal_error')
                print('Connection closed')
                raise e

    def __turn_on_wlan(self):
        import network
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        self.__fire_callback('wifi_active')
        return wlan

    def __connect_to_wlan(self, wlan, secrets: dict, max_wait: int=30):
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
                    self.add_callback('fatal_error', lambda **params: wlan.disconnect())
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

    def __open_socket(self):
        import usocket as socket
        # Open socket
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        s = socket.socket()
        
        # Without SO.REUSEADDDR, you get an OSError: [Errno 98] EADDRINUSE error which is a pain when restarting during debugging. 
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)

        print('listening on', addr)

        return s
 
    def __handle_routes_and_callbacks(self, cl, request):
        
        # get route and query parameters
        parsed_request = self.__parse_request(request)
        # check that it hasn't returned False, meaning it failed to parse
        if parsed_request:
            _, route, _, _, _ = parsed_request
        else:
            return False

        # get a tuple with handler functions and the default params we need to pass in
        route_handlers = self.__get_handlers_or_callbacks(route, kind='route')

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
    
    def __parse_request(self, request):
        from helpers.bits_and_bobs import next
        # e.g. for 'GET /update/?pico_name=test+name&ssid=blah+blah&wifi_pass=testpass&sensor=on'

        request_lines = self.__request_lines_gen(request)
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
        print('DEBUG: route = ', route)
        
        if query_string:
            # split out each parameter
            parameters = query_string.split('&')
            # get a dictionary of parameters by splitting each parameter on the = sign
            query_parameters = {parameter.split('=')[0]: parameter.split('=')[1] for parameter in parameters}
        else:
            query_parameters = None
        
        form_data = self.__form_data_gen(current_line, request_lines) if current_line[:4] == 'POST' else None

        # make them available for everyone... might cause problems if concurrent requests are added!
        self.__add_placeholder_param('route', route)
        self.__add_placeholder_param('query_parameters', query_parameters)
        self.__add_placeholder_param('form_data', form_data)

        return method, route, query_parameters, form_data, protocol

    def __form_data_gen(self, current_line, request_lines):
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
        current_line, request_lines, content_type_found = self.__scroll_to(current_line, request_lines, 'Content-Type')

        content_type = ''
        if content_type_found:
            _, _, content_type = current_line.partition(': ')

        # if it's a multipart form (i.e. not urlencoded)
        if content_type_found and content_type[:19] == 'multipart/form-data':
            print('DEBUG: multipart data')
            # get the boundary (i.e. the string that separates form entries)
            boundary = content_type.partition('; ')[2][9:].strip()
            print('DEBUG: boundary = \n' + boundary)
            field_sep = '--' + boundary
            form_end = '--' + boundary + '--'

            # separate original request string now we know the boundary - we need to add '---' to the start
            # we can throw away the first two, and last items:
            # - the first item is everything before the first boundary
            # - the last item is just '--' because the form items end with the boundary + '--'
            
            # move to first field
            current_line, request_lines, content_type_found = self.__scroll_to(current_line, request_lines, field_sep)
            # move to first line after first boundary
            # do until end of form data reached
            
            # get a regex for finding the key (it's faster if we compile it once and reuse it)
            re_key = re.compile('^Content-Disposition: form-data; name="(.*)"\s*$')

            while form_end not in current_line:
                print('DEBUG: outer loop (reading fields)')
                current_line = next(request_lines)
                print('DEBUG: current_line \n', current_line)
                
                # get key and value. key is just in first line, value is any following data (up to next boundary)
                key = re_key.match(current_line).groups()[0]
                current_line = next(request_lines)
                value = ''
                while field_sep not in current_line:
                    print('DEBUG: inner loop (reading lines)')
                    value += current_line
                    current_line = next(request_lines)
                print('DEBUG: yielding (key, value) = \n', (key, value))
                yield key, value
        else:
            # can't deal with urlencoded data as there's no micropython library for decoding it
            # TODO: return an appropriate status code
            pass

    def __scroll_to(self, current_line, request_lines, begins_with):
            #print('DEBUG: Before __scroll_to current_line = ', current_line)
            found = True
            while current_line[:len(begins_with)] != begins_with:
                #if current_line == '': raise ValueError('current_line empty')
                try:
                    current_line = next(request_lines)
                    print('DEBUG: current_line[:len(begins_with)] = ', current_line[:len(begins_with)])
                    #print('DEBUG: current_line = ', current_line)
                except StopIteration:
                    found = False
                    break
            print('DEBUG: After __scroll_to current_line = ', current_line)
            return current_line, request_lines, found

    def __get_handlers_or_callbacks(self, route_or_callback: str, kind) -> tuple:
        
        """
        Checks all route/callback definitions for the one that contain this route
        and return handlers and parameters in a tuple

        Args:
            route_or_callback (str): The ID of the route or callback as a string
            kind (str, optional): Whether it's a route or callback. Defaults to 'route'.

        Returns:
            tuple: Contains tuples, each with
            * string: the ID of the route of callback,
            * function: the function itself,
            * dict: parameters that needs to be passed into it when calling it, i.e. handler_function(**params)
        """
        
        # get the object to lookup the callbacks or routes in
        lookup = self.callbacks if kind == 'callback' else self.routes

        # find only the relevant handlers
        handlers = tuple(
            filter(
                lambda handler: True if route_or_callback == handler[0] else False,
                lookup
                )
            )

        # if there aren't any registered handlers for this route, we want to substitute the "not found" handler
        # for routes, or nothing for callbacks
        if len(handlers) == 0:
            handlers = tuple() if kind == 'callback' else (self.not_found_response,)
        
        # add in any placeholder_params that are now available by merging them with the existing params (these are present in handler[-1])
        handlers = tuple(
            map(
                # both need to be tuples to add them, hence the brackets. This is essentially replacing the last two items (params and placeholder_params with a merged dict of the two)
                # ... but with placeholder_params now a dictionary with the placeholders filled in
                lambda handler: handler[:-2] + (self.__get_placeholder_params(keys=handler[-1], merge=handler[-2]),),
                handlers
                )
            )

        return handlers

    def add_route(self, route: str, handler, params: dict={}, placeholder_params: tuple=tuple()):
        return self.__add_route_or_callback(route, 'route', handler, params, placeholder_params)

    def add_callback(self, callback_id: str, handler, params: dict={}, placeholder_params: tuple=tuple()):
        return self.__add_route_or_callback(callback_id, 'callback', handler, params, placeholder_params)

    def __add_route_or_callback(self, id: str, kind: str, handler, params: dict, placeholder_params: tuple):
        """
        Add a route, handler and parameters i.e. a URL path and the function to be called when it is requested.

        Args:
            route (str): The string representation of the route (e.g. /data)
            handler (Callable): A callable (i.e. function) to be called to handle route
            params (dict, optional): Keywords arguments to be passed to routes in addition to any default params passed by the server. Defaults to {}.
        """

        # deal with routes and callbacks appropriately, and the special case of the "404 not found" route
        if kind == 'route' and id != '__not_found__':
            routes_or_callbacks = self.routes
        elif id == '__not_found__':
            self.not_found_response = (id, handler, params, placeholder_params)
            return
        else:
            routes_or_callbacks = self.callbacks

        routes_or_callbacks.append((id, handler, params, placeholder_params))

    def __fire_callback(self, event):
        # get the callback function and parameters, or return a dummy function
        callbacks = self.__get_handlers_or_callbacks(route_or_callback=event, kind='callback')
        print('DEBUG: callbacks = ', callbacks)
        if len(callbacks) == 0: return
        for callback in callbacks:
            _, handler, params = callback
            handler(**params)
        return callbacks

    # receive up to 1024 bytes at a time and store the result as a string
    def __request_gen(self, cl, bytes=1024):
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

    def __request_lines_gen(self, request, terminator='\r\n'):
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

    def __add_placeholder_param(self, key, value):
        self.placeholder_params[key] = value
        return self.placeholder_params
    
    def __get_placeholder_params(self, keys: tuple, merge: dict={}) -> dict:
        """
        Get placeholder parameters available at the time this method is called
        and return a dictionary, optionally merged with the dictionary specified 
        as merge.

        This is useful so callbacks and routes can receive arguments that aren't available when they're registered.

        Args:
            keys (tuple): Keys of variables to include
            merge (dict, optional): Optional dictionary to merge with. This takes precedence in case of conflict. Defaults to {}.

        Returns:
            dict: Dictionary with available values
        """

        placeholder_params = {key: self.placeholder_params.get(key, None) for key in keys}
        placeholder_params.update(merge)
        return placeholder_params if placeholder_params is not None else {}
