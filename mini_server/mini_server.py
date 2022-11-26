class mini_server():
    # code for request/response adapted from https://www.raspberrypi.com/news/how-to-run-a-webserver-on-raspberry-pi-pico-w/
    def __init__(self, secrets: list, not_found_response: tuple, response_timeout=5, device_uuid: str=''):
        import rp2
        
        self.secrets = secrets
        self.routes = []
        self.not_found_response = not_found_response
        self.current_route = ''
        self.current_request_str = ''
        self.response_timeout = response_timeout

        # if we have a function for finding UUID, then let's be havin' it!
        self.device_uuid = device_uuid

        # wifi connection data/setup
        rp2.country('DE')
    
    def connect_to_wifi(self):
        import network
        import socket
        import utime
        import machine

        ### activate WLAN on device
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        # try each network 4 times

        ### try to connect - cycle through available secrets
        
        # get long list of (repeated) secrets
        secrets_repeated = self.secrets * 4
        
        # keep cycling through them until the list is empty
        while len(secrets_repeated) > 0:
            # get one of the ssid-password pairs
            secret = secrets_repeated.pop(0)
            # connect to the ssid
            self.wlan.connect(secret['ssid'], secret['pw'])
            # wait for connect or fail
            # max_wait is number of seconds to wait in total
            max_wait = 20
            while max_wait > 0:
                # keep waiting for specified amount of time
                if self.wlan.status() < 0 or self.wlan.status() > 3 or self.wlan.status() == network.STAT_GOT_IP: break
                max_wait -= 1
                print(f'waiting for connection to {secret["ssid"]}...')
                print(f'status = {self.wlan.status()}')
                utime.sleep(1)

            if self.wlan.status() != network.STAT_GOT_IP:
                # something went wrong
                print('Couldn\'t connect ...')
                print('Status code received:', self.wlan.status())
                # if we've got no more networks to try, then sleep 10 mins before resetting the machine
                # so we can start again
                if len(secrets_repeated) == 0:
                    print('Network connection failed')
                    print('Waiting 10 mins then restarting...')
                    utime.sleep(600)
                    machine.reset()
            else:
                print(f'Connected to: {secret["ssid"]}')
                status = self.wlan.ifconfig()
                print( 'ip = ' + status[0] )
                if self.device_uuid:
                    print(f'UUID: {self.device_uuid}')
                secrets_repeated = []

        # Open socket
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]  # type: ignore
        
        self.open_socket = socket.socket()  # type: ignore
        
        # these two lines make it easier to debug - you don't have to hard reset the Pico
        # every time you want to restart. (Without this, you get an OSError: [Errno 98] EADDRINUSE error) 
        self.open_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #type:ignore
        self.open_socket.bind(addr)

        print('listening on', addr)

    def listen(self):
        import machine
        from utime import sleep
        # Listen for connections
        s = self.open_socket
        s.listen(1)
        # set a timeout of 0.1 seconds
        while True:
            try:
                cl, addr = s.accept()
                
                cl.settimeout(0.5)

                # receive up to 2048 bytes at a time and store the result as a string
                responses = []
                while True:
                    try:
                        print('DEBUG: Trying to receive data...')
                        data = cl.recv(128)
                        print('DEBUG: Received data...')
                        print(data)
                    except:
                        print('DEBUG: No more data...')
                        break
                    else:
                        print('DEBUG: Appending data...')
                        responses.append(data)
                
                print('DEBUG: FINISHED receiving data')
                response = b''.join(responses)

                self.current_request_str = str(response.decode('utf-8'))
                    
                print('DEBUG: request_string = \n')
                for line in self.current_request_str.split('\n'): print(line)
                #input('DEBUG: Press enter to continue')
                with open('last_request.txt', 'w') as f:
                    print(f.write(self.current_request_str))

                self.__handle_routes(cl)
                cl.close()

            except (OSError, KeyboardInterrupt) as e:
                s.close() #type: ignore
                self.wlan.disconnect()
                print('Connection closed')
                if isinstance(e, OSError):
                    # go into deep sleep for 10 mins then try again (hopefully)
                    #print('OSError...')
                    #machine.deepsleep(600000)
                    raise e
                elif isinstance(e, KeyboardInterrupt):
                    raise e

    def add_route(self, route: str, handler, params: dict):
        # list of tuples of routes (i.e. strings) and handlers (i.e. functions)
        self.routes.append(
            (route, handler, params)
        )
    
    def __handle_routes(self, cl):
        # cl is the client

        # get route and query parameters
        _, route, query_parameters, _ = self.__parse_request_string(self.current_request_str)

        # debug
        print('request on route: ', route)

        # get the handler function and the default params we need to pass in
        route_handlers = self.__get_handlers(route)

        for route_handler in route_handlers:
            _, handler_func, handler_params = route_handler
            print('DEBUG: route_handler = ', route_handler)
            # execute the handler and get a header and response
            header, response = handler_func(**handler_params, query_parameters=query_parameters)
            # send the header
            cl.send(header)
            # send the response
            cl.send(response)
            cl.close()
    
    def __parse_request_string(self, request_string):
        # micropython regex is severely limited... as if regex wasn't complicated enough.
        # https://docs.micropython.org/en/latest/library/re.html
        # so it's easier to break down the string with built-in string functions.
        #
        # e.g. for 'GET /update/?pico_name=test+name&ssid=blah+blah&wifi_pass=testpass&sensor=on'

        # just get the first line
        request_string = request_string.split('\n')[0]

        # get the method (GET or POST), query (e.g. http://192.168.2.153/.../update)
        # and protocol (e.g. HTTP/1.1)
        method, query, protocol = request_string.split(' ')

        # get the path (e.g. http://192.168.2.153) and query string (e.g. pico_name=test+name&ssid=blah+blah&wifi_pass=testpass&sensor=on)
        route, _, query_string = query.partition('?')
        
        if query_string:
            # split out each parameter
            parameters = query_string.split('&')
            # get a dictionary of parameters by splitting each parameter on the = sign
            query_parameters = {parameter.split('=')[0]: parameter.split('=')[1] for parameter in parameters}
        else:
            query_parameters = None

        route = route.rstrip('/')
        
        return method, route, query_parameters, protocol

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
