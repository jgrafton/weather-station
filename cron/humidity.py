#!/usr/bin/env python3

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import Adafruit_DHT
import time
import subprocess
import json
import pprint

DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4
SLEEP = 5

def celsius_to_fahrenheit(c):
    return (c * 1.8) + 32.0

if __name__ == '__main__':
    registry = CollectorRegistry()
    gtf = Gauge('garage_temperature_f', 'Temperature of garage in degrees F', registry=registry)
    gtc = Gauge('garage_temperature_c', 'Temperature of garage in degrees C', registry=registry)
    gh = Gauge('garage_humidity', 'Humidity of garage', registry=registry)

    print('Sleeping {} seconds before taking reading.'.format(SLEEP))
    time.sleep(SLEEP);

    humidity, temperature_c = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature_c is not None:
        temperature_f = celsius_to_fahrenheit(temperature_c)
        print("Temp={0:0.1f}F  Humidity={1:0.1f}%".format(temperature_f, humidity))
        gtf.set(temperature_f)
        gtc.set(temperature_c)
        gh.set(humidity)
        push_to_gateway('localhost:9091', job='humidity', registry=registry)
    else:
        print('Sensor failure.  Check wiring')

