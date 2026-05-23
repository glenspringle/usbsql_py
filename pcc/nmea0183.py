def __nmea0183_split(msg: str):
    start = msg.find('$')
    end = msg.find('*')

    if start == -1 or end == -1:
        return False

    return msg[start+1:end].split(',')


def nmea0183_checksum(msg: str):
    msg = msg.strip()

    checksum = 0
    for idx, ch in enumerate(msg):
        if idx == 0 and ch == '$':
            continue
        if ch == '*':
            break
        else:
            checksum = checksum ^ ord(ch)

    return checksum


def nmea0183_validate(msg: str):
    try:
        msg = msg.strip()
        checksum = nmea0183_checksum(msg)
        if checksum == int(msg[-2:], 16):
            return True

    except:
        return False

    return False


def nmea0183_parse(msg, validate_checksum: bool=True):
    if validate_checksum and not nmea0183_validate(msg):
        return False

    return __nmea0183_split(msg.strip())


def nmea0183_create(msg: list):
    payload = ",".join(str(part) for part in msg)
    checksum = nmea0183_checksum(payload)
    return f"${payload}*{checksum:02X}\n"
