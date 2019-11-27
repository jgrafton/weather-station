#!/usr/bin/env python

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import os
import sys
import time
import serial
import pprint
import logging
import datetime

# Prometheus registry setup
registry = CollectorRegistry()
gpm2_5 = Gauge('backyard_particulate_matter_2_5', 'Particulate Matter 2.5um count', registry=registry)
gpm10 = Gauge('backyard_particulate_matter_10', 'Particulate Matter 10um count', registry=registry)

PMS5003_RESET_GPIO = '/sys/class/gpio/gpio17'

AVERAGE_READS = 10

SLEEP_BETWEEN_READS = 1

# Attempt a sensor reset after some errors.
RESET_ON_FRAME_ERRORS = 20

# Abort the averaged read after too many errors.
MAX_FRAME_ERRORS = 10

MAX_TOTAL_RESPONSE_TIME = 12

# Normal data frame length.
DATA_FRAME_LENGTH = 28

# Command response frame length.
CMD_FRAME_LENGTH = 4

# Sensor settling after wakeup requires at least 30 seconds (sensor sepcifications).
WAIT_AFTER_WAKEUP = 40

# Total Response Time is 10 seconds (sensor specifications).
MAX_TOTAL_RESPONSE_TIME = 12

# Calculate average on this output data.
AVERAGE_FIELDS = ['data1', 'data2', 'data3', 'data4', 'data5', 'data6', 'data7', 'data8', 'data9', 'data10', 'data11', 'data12']

#-------------------------------------------------------------- 
# PMS5003 Commands for Passive Mode.
#---------------------------------------------------------------
CMD_SLEEP  = b'\x42' + b'\x4d' + b'\xe4' + b'\x00' + b'\x00'
CMD_WAKEUP = b'\x42' + b'\x4d' + b'\xe4' + b'\x00' + b'\x01'

#---------------------------------------------------------------
# Convert a two bytes string into a 16 bit integer.
#---------------------------------------------------------------
def int16bit(b):
    return (ord(b[0]) << 8) + ord(b[1])

#---------------------------------------------------------------
# Make a list of averaged reads: (datetime, float, float, ...)
#---------------------------------------------------------------
def make_average(reads_list):
    average = []
    average.append(datetime.datetime.utcnow())
    for k in AVERAGE_FIELDS:
        average.append(float(sum(r[k] for r in reads_list)) / len(reads_list))
    return average

#---------------------------------------------------------------
# Convert the list created by make_average() to a string.
#---------------------------------------------------------------
def average2str(a):
    s = a[0].strftime('%Y-%m-%dT%H:%M:%SZ')
    for f in a[1:]:
        s += ' %0.2f' % (f)
    return s

#---------------------------------------------------------------
# Return the hex dump of a buffer of bytes.
#---------------------------------------------------------------
def buff2hex(b):
    return " ".join("0x{:02x}".format(ord(c)) for c in b)

#---------------------------------------------------------------
# Enter sensor sleep state.
#---------------------------------------------------------------
def sensor_sleep(_port):
    logging.info("Sending sleep command")
    send_buffer(CMD_SLEEP, _port)
    _port.flushInput()

#---------------------------------------------------------------
# Exit from sleep state and wait sensor to settle.
#---------------------------------------------------------------
def sensor_wakeup(_port):
    logging.info("Sending wakeup command")
    response = send_buffer(CMD_WAKEUP, _port)
    if not response:
        logging.error('No response to wakeup command')
        sensor_reset()
        logging.info('Sending wakeup command again')
        response = send_buffer(CMD_WAKEUP, _port)
        if not response:
            logging.error('No response to repeated wakeup command')
    logging.info("Waiting %d seconds for sensor to settle" % (WAIT_AFTER_WAKEUP,))
    time.sleep(WAIT_AFTER_WAKEUP)
    _port.flushInput()

#---------------------------------------------------------------
# Send a RESET signal to sensor.
#---------------------------------------------------------------
def sensor_reset():
    logging.info("Sending RESET signal to sensor")
    try:
        gpio_direction = None
        if not os.path.isdir(PMS5003_RESET_GPIO):
            logging.error(u'GPIO for sensor RESET is not exported: %s' % (PMS5003_RESET_GPIO,))
            return
        else:
            with open(os.path.join(PMS5003_RESET_GPIO, 'direction'), 'r') as f:
                gpio_direction = f.read().strip()
        if gpio_direction != 'out':
            logging.error(u'GPIO for sensor RESET is not set to output')
            return
        else:
            logging.info(u'Setting GPIO line to LOW for a short time')
            with open(os.path.join(PMS5003_RESET_GPIO, 'value'), 'w') as f:
                f.write("0\n")
            time.sleep(0.5)
            with open(os.path.join(PMS5003_RESET_GPIO, 'value'), 'w') as f:
                f.write("1\n")
            time.sleep(1.0)
    except Exception, e:
        logging.error(u'PMS5003 sensor RESET via GPIO line: Exception %s' % (str(e),))
    except KeyboardInterrupt:
        sys.exit(1)
    return

#---------------------------------------------------------------
# Send a command buffer to the serial port, with checksum.
# Return the response frame, if any.
#---------------------------------------------------------------
def send_buffer(b, _port):
    checksum = 0
    for i in range(0, len(b)):
        checksum += ord(b[i])
    b += chr(checksum / 256) + chr(checksum % 256)
    logging.debug("Using passive mode to send buffer: %s" % (buff2hex(b),))
    _port.flushInput()
    written = _port.write(b)
    if written != len(b):
        logging.warning("Short write, sent %d bytes instead of %d" % (written, len(b)))
        response = None
    else:
        # Get a response frame (if any). Examples:
        # Wakeup CMD: 0x42 0x4d 0xe4 0x00 0x01
        #   Response: 0x42 0x4d 0x00 0x1c ...(full data frame)
        # Sleep CMD:  0x42 0x4d 0xe4 0x00 0x00
        #   Response: 0x42 0x4d 0x00 0x04 0xe4 0x00
        response = read_pm_frame(_port)
    return response

#---------------------------------------------------------------
# Read a data frame from serial port, the first 4 bytes are:
# 0x42, 0x4d, frame length (16 bit integer).
# Return None on errors.
#---------------------------------------------------------------
def read_pm_frame(_port):
    frame = b''
    start = datetime.datetime.utcnow()
    while True:
        b0 = _port.read()
        if b0 != '':
            logging.debug('Got char 0x%x from serial read()' % (ord(b0),))
        else:
            logging.debug('Timeout on serial read()')
        if b0 == b'\x42':
            logging.debug('b0 0x%x from serial read()' % (ord(b0),))
            b1 = _port.read()
            logging.debug('b1? 0x%x from serial read()' % (ord(b1),))
            if b1 == b'\x4d':
                logging.debug('b1 0x%x from serial read()' % (ord(b1),))
                b2 = _port.read()
                logging.debug('b2 0x%x from serial read()' % (ord(b2),))
                b3 = _port.read()
                logging.debug('b3 0x%x from serial read()' % (ord(b3),))
                frame_len = ord(b2) * 256 + ord(b3)
                if frame_len == DATA_FRAME_LENGTH:
                    # Normal data frame.
                    frame += b0 + b1 + b2 + b3
                    frame += _port.read(frame_len)
                    if (len(frame) - 4) != frame_len:
                        logging.error("Short read, expected %d bytes, got %d" % (frame_len, len(frame) - 4))
                        return None
                    # Verify checksum (last two bytes).
                    expected = int16bit(frame[-2:])
                    checksum = 0
                    for i in range(0, len(frame) - 2):
                        checksum += ord(frame[i])
                    if checksum != expected:
                        logging.error("Checksum mismatch: %d, expected %d" % (checksum, expected))
                        return None
                    logging.debug("Received data frame = %s" % (buff2hex(frame),))
                    return frame
                elif frame_len == CMD_FRAME_LENGTH:
                    # Command response frame.
                    frame += b0 + b1 + b2 + b3
                    frame += _port.read(frame_len)
                    logging.debug("Received command response frame = %s" % (buff2hex(frame),))
                    return frame
                else:
                    # Unexpected frame.
                    logging.error("Unexpected frame length = %d" % (frame_len))
                    time.sleep(MAX_TOTAL_RESPONSE_TIME)
                    _port.flushInput()
                    return None

        if (datetime.datetime.utcnow() - start).seconds >= MAX_TOTAL_RESPONSE_TIME:
            logging.error("Timeout waiting data-frame signature")
            return None

def data_frame_verbose(f):
    return (' PM1.0 (CF=1) ug/m3: {};\n'
            ' PM2.5 (CF=1) ug/m3: {};\n'
            ' PM10  (CF=1) ug/m3: {};\n'
            ' PM1.0 (STD)  ug/m3: {};\n'
            ' PM2.5 (STD)  ug/m3: {};\n'
            ' PM10  (STD)  ug/m3: {};\n'
            ' Particles >  0.3 um count: {};\n'
            ' Particles >  0.5 um count: {};\n'
            ' Particles >  1.0 um count: {};\n'
            ' Particles >  2.5 um count: {};\n'
            ' Particles >  5.0 um count: {};\n'
            ' Particles > 10.0 um count: {};\n'
            ' Reserved: {};\n'
            ' Checksum: {};'.format(
                f['data1'],  f['data2'],  f['data3'],
                f['data4'],  f['data5'],  f['data6'],
                f['data7'],  f['data8'],  f['data9'],
                f['data10'], f['data11'], f['data12'],
                f['reserved'], f['checksum']))

#---------------------------------------------------------------
# Save averaged data somewhere.
#---------------------------------------------------------------
def save_data(text):
    print('Particles > 2.5: {}'.format(text[10]))
    print('Particles > 10: {}'.format(text[12]))
    gpm2_5.set(text[10])
    gpm10.set(text[12])
    push_to_gateway('localhost:9091', job='pms5003', registry=registry)
    return


if __name__ == '__main__':
    handler = logging.StreamHandler(stream=sys.stdout)
    log = logging.getLogger()
    log.setLevel('DEBUG')

    port = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=2)

    logging.info('Waking sensor up.')
    sensor_wakeup(port)

    reads_list = []
    error_count = 0
    error_total = 0
    while True:
        try:

            rcv = read_pm_frame(port)

            # Manage data-frame errors.
            if rcv == None:
                error_count += 1
                error_total += 1
            if error_count >= RESET_ON_FRAME_ERRORS:
            	logging.warning("Repeated read errors, attempting sensor reset")
            	sensor_reset()
            	error_count = 0
            	continue
            if error_total >= MAX_FRAME_ERRORS:
                if (SLEEP_BETWEEN_READS >= 0):
                    logging.error("Too many read errors, sleeping a while")
                    time.sleep(SLEEP_BETWEEN_READS)
                    error_total = 0
                    continue
                else:
                    logging.error("Too many read errors, exiting")
                break

            # Skip non-output data-frames.
            if (rcv == None) or ((len(rcv) - 4) != DATA_FRAME_LENGTH):
                continue

            # Got a valid data-frame.
            res = {'timestamp': datetime.datetime.utcnow(),
               'data1':     int16bit(rcv[4:]),
               'data2':     int16bit(rcv[6:]),
               'data3':     int16bit(rcv[8:]),
               'data4':     int16bit(rcv[10:]),
               'data5':     int16bit(rcv[12:]),
               'data6':     int16bit(rcv[14:]),
               'data7':     int16bit(rcv[16:]),
               'data8':     int16bit(rcv[18:]),
               'data9':     int16bit(rcv[20:]),
               'data10':    int16bit(rcv[22:]),
               'data11':    int16bit(rcv[24:]),
               'data12':    int16bit(rcv[26:]),
               'reserved':  buff2hex(rcv[28:30]),
               'checksum':  int16bit(rcv[30:])
               }
            logging.debug("Got valid data frame:\n" + data_frame_verbose(res))

            reads_list.append(res)
            if len(reads_list) >= AVERAGE_READS:
                # Calculate the average of each measured data.
                logging.info("Got %d valid readings, calculating average" % (len(reads_list)))
                average = make_average(reads_list)
                average_str = average2str(average)
                logging.info("Average data: %s" % (average_str,))
                save_data(average)
                del reads_list[:]
                break
            if SLEEP_BETWEEN_READS < 0:
                break
            if SLEEP_BETWEEN_READS > (WAIT_AFTER_WAKEUP * 3):
                # If sleep time is long enough, enter sensor sleep state.
                sensor_sleep(port)
                logging.info("Waiting %d seconds before new read" % (SLEEP_BETWEEN_READS,))
                time.sleep(SLEEP_BETWEEN_READS)
                sensor_wakeup(port)
            else:
                # Keep sensor awake and wait for next reads.
                logging.info("Waiting %d seconds before new read" % (SLEEP_BETWEEN_READS,))
                time.sleep(SLEEP_BETWEEN_READS)
                port.flushOutput()
                port.flushInput()

        except KeyboardInterrupt:
            break

    try:
        logging.info("Exiting main loop")
        sensor_sleep(port)
        port.close()
        sys.exit(0)
    except KeyboardInterrupt:
        pass

