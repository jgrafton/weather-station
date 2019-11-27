#!/usr/bin/env python3

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from pijuice import PiJuice
import pprint
import time

registry = CollectorRegistry()
gbch = Gauge('pijuice_battery_charge', 'Percentage of PiJuice battery left', registry=registry)
gbcu = Gauge('pijuice_battery_current', 'Percentage of PiJuice battery left', registry=registry)
giocu = Gauge('pijuice_io_current', 'Percentage of PiJuice battery left', registry=registry)

pijuice = PiJuice(1, 0x14)

print('Sleeping 10 seconds before taking reading.')
time.sleep(10)

charge = pijuice.status.GetChargeLevel()
batt_current = pijuice.status.GetBatteryCurrent()
current = pijuice.status.GetIoCurrent()

print('Charge Level: {}'.format(charge['data']))
gbch.set(charge['data'])

print('IO Current: {}'.format(current['data']))
giocu.set(current['data'])

print('Battery Current: {}'.format(batt_current['data']))
gbcu.set(batt_current['data'])

push_to_gateway('localhost:9091', job='pijuice', registry=registry)

