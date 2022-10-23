import time
import network
import socket
from machine import Pin
import json
import re

from ambient_data import get_ambient_data
from secrets import secrets
from flash_led import flash_led

# get a generator to yield readings one at a time
ambient_data = get_ambient_data(iterations=True)

# wifi connection data/setup
rp2.country('DE')

ssid = secrets['ssid']
password = secrets['pw']

# give this Pico an id so it can be found over the network
pico_id = '1'

# code for request/response adapted from https://www.raspberrypi.com/news/how-to-run-a-webserver-on-raspberry-pi-pico-w/
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

# Wait for connect or fail
max_wait = 20
while max_wait > 0:
  if wlan.status() < 0 or wlan.status() >= 3:
    break
  max_wait -= 1
  print('waiting for connection...')
  time.sleep(1)

# Handle connection error
if wlan.status() != 3:
  raise RuntimeError('network connection failed')
else:
  print('connected')
  status = wlan.ifconfig()
  print( 'ip = ' + status[0] )

# Open socket
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print('listening on', addr)

# Regex for getting params (not currently used)
re_readings = re.compile(r'/data\/*(\d*)')


# Listen for connections
while True:
  try:
    cl, addr = s.accept()
#    print('client connected from', addr)
    request = cl.recv(1024)
#    print(request)
    request = str(request)
#    print(request)
    # get parameter (i.e. n readings) in format /temp/<n_readings>
    readings_match = re_readings.search(request)
    if readings_match is not None:
        print(readings_match.groups()[0])

    # prints the ID of the Pico in a browser
    its_me = request.find(f'/find/{pico_id}')
  
    if its_me == 6:
        print("It's me!")
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(f'<html>Pico W with ID {pico_id}</html>')
    elif readings_match is not None:
        return_data = list(next(ambient_data))
        return_data.append(pico_id)
        return_data.append('bme280')
        return_data = dict(zip(('temp', 'pressure', 'humidity', 'pico_id', 'sensor'), return_data))
        cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n')
        cl.send(json.dumps(return_data))
    else:
    # 404
      cl.send('HTTP/1.0 404 Not Found\r\nContent-type: text/html\r\n\r\n')
      cl.send(f'<html>404: Resource not found.</html>')
    
    cl.close()

  except OSError as e:
    cl.close()
    flash_led(led=led)
    print('connection closed')
