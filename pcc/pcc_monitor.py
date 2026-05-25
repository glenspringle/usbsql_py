import zmq
import argparse
import serial
import struct
import traceback
from .graceful_exiter import GracefulExiter
from time import time
from datetime import datetime, UTC
from .nmea0183 import nmea0183_create, nmea0183_parse
from . import convert_to_date_format, convert_to_datetime
from . import PUB_DEVICE, PUB_ENTRY, PUB_LOG, PCC_REQ_STATUS, PCC_REQ_USAGE, PCC_RESP_STATUS, PCC_RESP_USAGE, PCC_REQ_UPDATE, PCC_RESP_UPDATE, DEFAULT_BAUDRATE, DEFAULT_ZMQ_AGGREGATOR_TRANSPORT, DEFAULT_TIME_FORMAT
from time import sleep

SERIAL_TIMEOUT_IN_SEC = 0.25
ZMQ_TIMEOUT_IN_MS = 1500

flag = GracefulExiter()


def send_request(ser: serial.Serial, msg: list):
    try:
        payload = nmea0183_create(msg)
        print(payload.encode('utf-8'))
        ser.write(payload.encode('utf-8'))
        resp = ser.readline()
        print(resp.decode('utf-8'))
        if resp == b'':
            return None
        else:
            return resp.decode('utf-8')
    except Exception as e:
        return None

def publish_msg(zsock: zmq.Socket, msg_type, msg: list, expect_response=False):
    payload = []
    for part in msg:
        if type(part) == datetime:
            payload.append(str(datetime.strftime(part, DEFAULT_TIME_FORMAT)).encode('utf-8'))
        else:
            payload.append(str(part).encode('utf-8'))
    try:
        zsock.send_multipart(msg_parts=[struct.pack('>f', datetime.now(UTC).timestamp()), msg_type.encode('utf-8')] + payload, flags=zmq.NOBLOCK)
    except Exception as e:
        return None

    if expect_response:
        try:
            return zsock.recv_multipart()
        except zmq.Again:
            return None

    return True


def publish_log(zsock: zmq.Socket, msg: str):
    publish_msg(zsock, PUB_LOG, [msg])


def publish_entry(zsock: zmq.Socket, dev_serial: str, entry_idx: int, entry_time: datetime):
    publish_msg(zsock, PUB_ENTRY, [dev_serial, entry_time, entry_idx])


def publish_device(zsock: zmq.Socket, dev_serial: str, dev_time: datetime):
    resp = publish_msg(zsock, PUB_DEVICE, [dev_serial, dev_time], expect_response=True)
    if resp is not None:
        return int(resp[0].decode('utf-8'))

    return None


def main():
    parser = argparse.ArgumentParser(prog='pcc_processor', description='USB Serial Program')
    parser.add_argument('port', type=str, help="Serial port to monitor")
    parser.add_argument('-b', '--baudrate', default=DEFAULT_BAUDRATE, type=int, help="Baud rate")
    parser.add_argument('-o', '--oneshot', default=False, type=bool, help="Try once on startup to access serial port")
    parser.add_argument('-a', '--aggregator', default=DEFAULT_ZMQ_AGGREGATOR_TRANSPORT, type=str, help="Aggregator Transport")

    args = parser.parse_args()

    # Connect to server running locally (or external?)
    zcontext = zmq.Context()

    # Any entries or devices connected, we send the event upstream to the aggregator
    try:
        zdata = zcontext.socket(zmq.DEALER)
        zdata.setsockopt(zmq.IDENTITY, args.port.encode("utf-8"))
        zdata.setsockopt(zmq.LINGER, ZMQ_TIMEOUT_IN_MS)
        zdata.setsockopt(zmq.RCVTIMEO, ZMQ_TIMEOUT_IN_MS)
        zdata.setsockopt(zmq.IMMEDIATE, 1)
        zdata.connect(args.aggregator)
    except Exception as e:
        print(f"Invalid gatherer transport '{args.aggregator}'")
        print(e)
        print(traceback.format_exc())
        exit(-1)


    ser = None
    last_device_and_idx = None
    while not flag.ready_to_exit():
        sleep(1.0)
        try:
            try:
                ser = serial.Serial(
                    port=args.port,
                    baudrate=args.baudrate,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=SERIAL_TIMEOUT_IN_SEC)

                while ser.in_waiting:
                    ser.read()

            except Exception as e:
                last_device_and_idx = None
                if ser is not None:
                    ser.close()
                    ser = None
                continue

            # Get Request Status
            resp = send_request(ser, [PCC_REQ_STATUS])
            if not resp:
                publish_log(zdata, f"Timeout reading status")
                continue

            status_msg_parts = nmea0183_parse(resp)
            if not status_msg_parts:
                publish_log(zdata, f"Unable to parse status response: {status_msg_parts}")
                continue

            if len(status_msg_parts) != 8:
                publish_log(zdata, f"Invalid status response length: {len(status_msg_parts)}")
                continue

            if not status_msg_parts[0] == PCC_RESP_STATUS:
                publish_log(zdata, f"Unknown status response header: {status_msg_parts}")
                continue

            dev_serial  = status_msg_parts[1]
            dev_year    = int(status_msg_parts[2])
            dev_month   = int(status_msg_parts[3])
            dev_day     = int(status_msg_parts[4])
            dev_seconds = int(status_msg_parts[5])
            latest_idx  = int(status_msg_parts[6])
            earliest_idx = int(status_msg_parts[7])
            dev_time = convert_to_datetime(dev_year, dev_month, dev_day, dev_seconds)


            # Only publish this device connected if its not been sent up yet
            # We don't want to bother 'reading' this device, if it won't be logged!
            resp = publish_device(zdata, dev_serial, dev_time)
            if resp is not None:
                year, month, day, seconds = convert_to_date_format(datetime.now(UTC))
                res = send_request(ser,[PCC_REQ_UPDATE, resp, year, month, day, seconds])
                if not res:
                    continue

                if latest_idx == 0:
                   continue

                if last_device_and_idx != None:
                    if last_device_and_idx == (dev_serial, latest_idx):
                        continue

                earliest_idx = max(earliest_idx, resp)
                if resp != latest_idx:
                    for n in range(earliest_idx+1, latest_idx+1):
                        resp = send_request(ser, [PCC_REQ_USAGE, n])
                        if not resp:
                            publish_log(zdata, f"Timeout receiving usage entry")
                            continue

                        entry_msg_parts = nmea0183_parse(resp)
                        if not entry_msg_parts:
                            publish_log(zdata, f"Unknown usage response: {status_msg_parts[0]}")
                            continue

                        if not len(entry_msg_parts) == 6:
                            publish_log(zdata, f"Unknown usage response: {status_msg_parts[0]}")
                            continue

                        if not entry_msg_parts[0] == PCC_RESP_USAGE:
                            publish_log(zdata, f"Unknown usage response: {status_msg_parts[0]}")
                            continue

                        entry_idx     = int(entry_msg_parts[1])
                        entry_year    = int(entry_msg_parts[2])
                        entry_month   = int(entry_msg_parts[3])
                        entry_day     = int(entry_msg_parts[4])
                        entry_seconds = int(entry_msg_parts[5])
                        entry_time = convert_to_datetime(entry_year, entry_month, entry_day, entry_seconds)
                        publish_entry(zdata, dev_serial, entry_idx, entry_time)

                        last_device_and_idx = (dev_serial, entry_idx)
            else:
                print("Aggregator unavailable, retrying...")

            ser.close()
            ser = None

        except Exception as e:
            print(f"Unknown error encountered: {traceback.format_exc()}")
            pass

if __name__ == '__main__':
    main()
