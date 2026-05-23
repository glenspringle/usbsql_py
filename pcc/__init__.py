from datetime import datetime

__version__ = "1.0.0"

PCC_REQ_STATUS = "PCC_REQ_STATUS"
PCC_RESP_STATUS = "PCC_STATUS"
PCC_REQ_USAGE = "PCC_REQ_USETIME"
PCC_RESP_USAGE = "PCC_USETIME"
PCC_REQ_UPDATE = "PCC_SET_COUNT_TIME"
PCC_RESP_UPDATE = "PCC_COUNT_TIME"

PUB_LOG = "LOG"
PUB_ENTRY = "ENTRY"
PUB_DEVICE = "DEVICE"

DEFAULT_BAUDRATE = 115200
DEFAULT_ZMQ_AGGREGATOR_TRANSPORT = 'tcp://127.0.1:9000' # 'ipc:///tmp/entry-aggregator' #
DEFAULT_SQL_LOCATION = "sqlite:///data/pcc.db"


DEFAULT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"

def convert_to_date_format(current_datetime: datetime):
    year = current_datetime.year
    month = current_datetime.month
    day = current_datetime.day
    seconds = (current_datetime.hour * 3600) + (current_datetime.minute * 60) + current_datetime.second

    return str(year), str(month), str(day), str(seconds)


def convert_to_datetime(year: int, month: int, day: int, time: int):
    hours = time // 3600
    minutes = (time - (hours * 3600)) // 60
    seconds = time - (hours * 3600) - (minutes * 60)
    return datetime.strptime(f"{str(year)}-{str(month)}-{str(day)} {str(hours)}:{str(minutes)}:{str(seconds)}+0000", DEFAULT_TIME_FORMAT)
