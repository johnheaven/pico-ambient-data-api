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

Theoretically you can add new routes with the `add_route` method of 'mini_server'. You'd do this if you wanted to have a new HTML page or API endpoint.

To do this call `add_route` on an initiated instance of `mini_server`, passing in:
* the route in the form of a list of path components. (The 'directory names' or bits between the slashes — `/[list_item_1]/[list_item_2]/[list_item_n]`).
* the handler, which has to be wrapped using the `wrap_route` method. In normal Python (I think) you'd use a partial for this but `functools` isn't available in MicroPython.
* add your handler to the (confusingly named) `routes.py` file.

## Setting up

You need to copy `example-settings.py` to settings.py then fill in your details. Currently, you'll need your board's unique ID. You can get this by connecting to the REPL interface on your Pico W, then typing the following:

```python
import binascii, machine
binascii.b2a_base64(machine.unique_id()).decode('utf-8').strip('\n')
```

Hopefully the settings are otherwise self-explanatory.

## Different settings for different boards

If you want to differentiate several boards, e.g. for different rooms, you can have several versions of settings  (such as sensor type, name, wifi secrets). Modify the `example-settings.py` file with the UUID for each board, which you can obtain as described above. Of course you don't have to have the settings for all board on every board, but if you want to be able to copy exactly the same code to all your devices and have them work without and fiddling, this is the easiest way at the moment.

## Useful resources

I've done a lot of research to find the best settings at various points. Here are some of the articles I found useful.

* Most robust settings for DHT-22:
  * https://www.elektronik-kompendium.de/sites/raspberry-pi/2703031.htm