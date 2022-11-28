# Bibliotheken laden
from machine import Pin
from utime import sleep
from dht import DHT22

# Initialisierung GPIO und DHT22
sleep(1)
dht22_sensor = DHT22(Pin(15, Pin.IN, Pin.PULL_UP))

# Wiederholung (Endlos-Schleife)
while True:
    # Messung durchführen
    dht22_sensor.measure()
    # Werte lesen
    temp = dht22_sensor.temperature()
    humi = dht22_sensor.humidity()
    # Werte ausgeben
    print('      Temperatur:', temp, '°C')
    print('Luftfeuchtigkeit:', humi, '%')
    print()
    sleep(3)