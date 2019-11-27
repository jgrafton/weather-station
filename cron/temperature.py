#!/usr/bin/env python3

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import glob
import time

registry = CollectorRegistry()

def celsius_to_fahrenheit(c):
    return (c * 1.8) + 32.0

def find_devices():
    return glob.glob('/sys/bus/w1/devices/28-*')

def read_temp(path):
    lines = []

    with open(path + '/w1_slave') as f:
        lines = f.readlines()

    if len(lines) != 2:
        return False, 0

    if lines[0].find('YES') == -1:
        return False, 0

    d = lines[1].strip().split('=')

    if len(d) != 2:
        return False, 0

    return True, int(d[1])


if __name__ == '__main__':
    gf = Gauge('backyard_temperature_f', 'Temperature of Garage in degrees F', registry=registry)
    gc = Gauge('backyard_temperature_c', 'Temperature of Garage in degrees C', registry=registry)
    devices = find_devices()

    for device in devices:
        valid, raw = read_temp(device)

        if valid:
            c = raw / 1000.0
            f = celsius_to_fahrenheit(c)
            print('{:0.2f} F'.format(f))
            print('{:0.2f} C'.format(c))
            gf.set(f)
            gc.set(c)
            push_to_gateway('localhost:9091', job='temperature', registry=registry)
