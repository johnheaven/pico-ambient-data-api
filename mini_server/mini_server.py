class mini_server():
    # code for request/response adapted from https://www.raspberrypi.com/news/how-to-run-a-webserver-on-raspberry-pi-pico-w/
    def __init__(self, secrets, rp2, not_found_response=None, device_uuid=None):
        import rp2
        
        self.secrets = secrets
        self.routes = []
        self.not_found_response = not_found_response

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
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        # try each network 4 times

        ### try to connect - cycle through available secrets
        
        # get long list of (repeated) secrets
        secrets_repeated = self.secrets * 4
        
        # keep cycling through them until the list is empty
        while len(secrets_repeated) > 0:
            # get one of the ssid-password pairs
            secret = secrets_repeated.pop(0)
            # connect to the ssid
            wlan.connect(secret['ssid'], secret['pw'])
            # wait for connect or fail
            # max_wait is number of seconds to wait in total
            max_wait = 20
            while max_wait > 0:
                # keep waiting for specified amount of time
                if wlan.status() < 0 or wlan.status() > 3 or wlan.status() == network.STAT_GOT_IP: break
                max_wait -= 1
                print(f'waiting for connection to {secret["ssid"]}...')
                print(f'status = {wlan.status()}')
                utime.sleep(1)

            if wlan.status() != network.STAT_GOT_IP:
                # something went wrong
                print('Couldn\'t connect ...')
                print('Status code received:', wlan.status())
                # if we've got no more networks to try, then sleep 10 mins before resetting the machine
                # so we can start again
                if len(secrets_repeated) == 0:
                    print('Network connection failed')
                    print('Waiting 10 mins then restarting...')
                    utime.sleep(600)
                    machine.reset()
            else:
                print(f'Connected to: {secret["ssid"]}')
                status = wlan.ifconfig()
                print( 'ip = ' + status[0] )
                if self.device_uuid is not None:
                    print(f'UUID: {self.device_uuid}')
                secrets_repeated = []

        # Open socket
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        self.open_socket = socket.socket()
        self.open_socket.bind(addr)
        self.open_socket.listen(1)

        print('listening on', addr)

    def listen(self):
        import machine, utime
        # Listen for connections
        s = self.open_socket
        while True:
            try:
                cl, addr = s.accept()
                print('client connected from', addr)
                request = cl.recv(1024)
                # print(request)
                self.current_url = str(request.decode('utf-8'))
                # only handle if request URI isn't empty
                if self.current_url != '':
                    self.__handle_routes(cl)
                cl.close()

            except OSError as e:
                cl.close()
                #flash_led(led=led)
                print('connection closed')
                # wait 10 mins then reset (and start again)
                utime.sleep(600)
                machine.reset()
    
    def add_route(self, route, handler):
        # dictionary of routes (i.e. strings) and handlers (i.e. functions)
        self.routes.append((route, handler))
    
    def __handle_routes(self, cl):
        # cl is the client
        # check whether the current URL is in the route -> cut off the 'GET ' at the start

        current_handler = tuple(filter(self.__check_route, self.routes))
        # assume there's only one value and execute it, otherwise 404
        if len(current_handler):
            current_handler[0][1](cl)
        else:
            if self.not_found_response:
                self.not_found_response(cl)

    def __get_url_parts(self, url):
        # advanced regex not supported in micropython :(
        return url.split('/')[2:]

    def __check_route(self, route_handler):
        # input needs to be a tuple of route and handler. The route is expected to be a tuple or list
        try:
            url_tokenised = tuple(filter(lambda s: False if s == '' else True, self.current_url.split(' ')[1].split('/')))
        except AttributeError:
            return False

        return True if route_handler[0] == url_tokenised else False
