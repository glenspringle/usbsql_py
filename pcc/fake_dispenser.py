import argparse
import serial
from time import sleep, time
from datetime import datetime,timedelta, UTC
from .graceful_exiter import GracefulExiter
from .nmea0183 import nmea0183_create, nmea0183_parse
from . import PCC_REQ_STATUS, PCC_REQ_USAGE, PCC_RESP_STATUS, PCC_RESP_USAGE, PCC_REQ_UPDATE, PCC_RESP_UPDATE, DEFAULT_BAUDRATE
from . import convert_to_date_format, convert_to_datetime


TIMEOUT_PERIOD = 0.05
SN = "20303455-5930430F-00100009"
NEWEST_ENTRY_IDX = 10
EARLIEST_ENTRY_IDX = 1


flag = GracefulExiter()


def send_response(ser: serial.Serial, msg: list):
    payload = nmea0183_create(msg)
    ser.write(payload.encode('utf-8'))
    print(payload.strip())


def main():
    parser = argparse.ArgumentParser(prog='fake_dispenser', description='Dispenser USB Serial Program')
    parser.add_argument('port', type=str, help="Serial port to use")
    parser.add_argument('-b', '--baudrate', default=DEFAULT_BAUDRATE, type=int, help="Baud rate")

    args = parser.parse_args()

    # Open serial port for processing
    try:
        ser = serial.Serial(
            port=args.port,
            baudrate=args.baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=TIMEOUT_PERIOD)
    except:
        print(f"Invalid serial port '{args.port}'")
        exit(-1)

    entries = []
    for n in range(0, NEWEST_ENTRY_IDX):
        entries.append(datetime.now() - timedelta(hours=(NEWEST_ENTRY_IDX - n)))

    while not flag.ready_to_exit():
        resp = ser.readline()
        if resp != b'':
            msg_parts = nmea0183_parse(resp.decode('utf-8'))
            if msg_parts:
                if msg_parts[0] == PCC_REQ_STATUS:
                    year, month, day, seconds = convert_to_date_format(datetime.now(UTC))
                    send_response(ser, [PCC_RESP_STATUS,SN,year,month,day,seconds,NEWEST_ENTRY_IDX,EARLIEST_ENTRY_IDX])

                elif msg_parts[0] == PCC_REQ_USAGE:
                    lookup_idx = int(msg_parts[1])
                    if lookup_idx <= NEWEST_ENTRY_IDX and lookup_idx > 0:
                        year, month, day, seconds = convert_to_date_format(entries[lookup_idx-1])
                        send_response(ser, [PCC_RESP_USAGE,lookup_idx,year,month,day,seconds])
                elif msg_parts[0] == PCC_REQ_UPDATE:
                    send_response(ser, [PCC_RESP_UPDATE, "OK"])
                    pass
                else:
                    pass
        sleep(0.05)


if __name__ == '__main__':
    main()
