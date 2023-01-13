# Ambient Data API for Raspberry Pico
Gets temperature, pressure and humidity data from a sensor attached to a Pico W and exposes it as JSON data via an API in the local network. It's all written in MicroPython.

This data can then be logged; see [ambient-data-logger](https://github.com/johnheaven/ambient-data-logger) as a basic example.

It currently supports the BME280 and the DHT22. It's intended to be written in a structured way that makes it relatively easy to add new sensors and endpoints, although it's still work in progress.

## Adding a new sensor type

* add a `__init_[SENSOR_NAME]` method within the `ambient_data_reader` class in `ambient_data.py`
* add a `__get_[SENSOR_NAME]_reading` method within the `ambient_data_reader` class in `ambient_data.py`
* change `__init__` within the `ambient_data_reader` class so it chooses your sensor depending on which `sensor_type` is passed in.

Currently, the return values of the `__get_[SENSOR_NAME]_reading` methods have to be uniform. Return `None` if your sensor doesn't support one of the values.

## Adding new routes

I've now integrated Pimoroni's Phew server, so see [their docs](https://github.com/pimoroni/phew) for adding new routes.

## Setting up

For initial setup, put a file `wifi.txt` in the root folder. This needs to contain SSID on the first line, and password on the second line.

The Pico will connect to this network on first boot so you can set it up.

## Setup

Once your Pico has connected and you know the IP (this is shown in the REPL when connecting, e.g. via Thonny), you can go to /settings and change the wifi network and the sensor type as well as the name of the device.

## Useful resources

* Most robust settings for DHT-22:
  * https://www.elektronik-kompendium.de/sites/raspberry-pi/2703031.htm
