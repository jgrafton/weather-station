# Outdoor Weather Station Build

![Proof of Concept](images/weather_station_poc.png?raw=true "Proof of Concept")

## About
Build a weather station that runs outdoors all day and night.  The station
should report metrics to a central server on the home's network which can be
aggrigated and graphed.

As a bonus build a website with gauge's letting the home's occupents know what
the outside weather is like.

### What to monitor
- temperature
- 2.5u particle matter
- 10u particle matter
- rain events
- barometric pressure
- humidity


## Research
### Power reducing options
- Turn off bluetooth
    - should be a raspberry pi overlay
- Turn off HDMI
    - /usr/bin/tvservice -o in /etc/rc.local

### Energy consumption
- How to measure the amount of power the raspberry pi consumes with the options I'm adding to it?
    - https://solartown.com/learning/solar-panels/choosing-and-sizing-batteries-charge-controllers-and-inverters-for-your-off-grid-solar-energy-system/

- Daily energy use for rpi0w, how many amp hours?
    - started measuring @ 9:45AM 11/15/19 with kill-a-watt
    - measured 0.01Kwh after 12 hours

- Relationship to solar panel size and how fast I can charge a
battery?

- Relationship to battery size and how long it will keep a device
running?


## Technology
### Computer: Raspberry Pi ZeroW
- The raspberry pi zero does not consume a lot of electricity which makes it an
    ideal canidate for the 'brain' of the weather station.
    - The raspberry pi zero draws less than 100mA while idle and 120mA to 140mA
        while the CPU is consumed.
- Has a builtin WIFI chipset that is also quite power efficient.

### OS: Rasbian
- Works out of the box and has drivers for most Raspberry Pi hardware.
    - https://www.raspberrypi.org/downloads/raspbian/

### Metric Collection: Prometheus
- http://prometheus.home.lan

### Metric Graphing: Grafana
- http://grafana.home.lan

### OS: FreeBSD?
- Have to run CURRENT since SDIO is not supported in any releases.
- ARM is not a teir 1 supported architecture which means difficulty in finding pre-built packages.

#### serial console not working
need to apply an overlay that disables bluetooth and resets UART0 to GPIO pins
14 and 15
https://www.raspberrypi.org/documentation/configuration/device-tree.md

config.txt
```
dtoverlay=pi3-disable-bt
```

#### wifi not working
- There is no driver, would have to use a USB wifi adapter.
```
wifi chip is a broadcom 43430
kldload sdio
sys/dev/sdio/sdiodevs:
product BROADCOM 43430          0xa9a6  BCM43430 fullmac SDIO WiFi
```

## Proof of concept
Build a Raspberry Pi ZeroW w/ comercial phone recharging solar panel that stays
running throughout the day and night and sends data to the metric collecting
server.


### POC Bill of Materials
- Raspberry Pi Zero WH
    - https://www.adafruit.com/product/3708
- Solar Panel
    - https://www.amazon.com/gp/product/B07V2CQVV3
    - 26800mAh capacity battery builtin
- USB mini to micro cable
- Sensors
    - [Temperature](https://www.adafruit.com/product/381)
        - DS18B20
        - (order adafruit's version)
    - [Particulate](https://www.amazon.com/gp/product/B07S5YX84W)
        - PMS5003
        - (on order)
    - [Humidity](https://www.adafruit.com/product/386)
        - DHT11
        - (upgrade to DHT22)

### POC Location
- [Outdoor Air Temperature Sensor Location](https://www.kele.com/content/blog/outside-air-temperature-sensor-location)
- Currently sits on the north side of our house.  It's shaded all day.

### Lesson's learned from POC
- Solar panel with battery built in is nice but does not allow for remote
    reporting of the solar panel / battery state.
- Putting a box that's in direct sunlight over the temperature sensor is not
    enough shade.  The temperature sensor should be shaded by the north side of
    a building.


## Budget
- $500
    - $100 solar panel 
        - $43.99 phone solar charger (amazon)
    - $100 sensors
        - $29.99 PMS5003 (amazon)
    - $100 computers
        - $32.99 Raspberry Pi Zero W kit (amazon)
        - $19.95 Raspberry Pi Zero WH (adafruit)
    - $100 battery & regulator
        - $78.95 PiJuice HAT (amazon)
    - $100 misc


## Task List
- ~~create github location~~
- ~~order second raspberry pi 0w w/ headers~~
- ~~order PMS5003 particulate sensor~~
- ~~attach temperature sensor to POC~~
- allow POC to run over night, does it survive?
- attach humidity sensor to POC
- attach headers to second raspberry pi
- attach header to PMS5003 sensor
- attach particulate sensor to POC
- spec out 12w solar panel for actual build
- spec out battery (4400mAh)
- attach PiJuice to second pi zero
- mess around with PiJuice on second pi zero
- create systemd service definition for reporter.py
- enable reporter.py service on rpiw0
