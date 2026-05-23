from pcc.nmea0183 import nmea0183_checksum, nmea0183_validate, nmea0183_parse

known_good = "$PCC,02*7E"
known_bad = "$PCC,02*15"

def test_checksum_calc():
    assert nmea0183_checksum("") == 0
    assert nmea0183_checksum(known_good) == 0x7E

def test_validate():
    assert nmea0183_validate(known_good) == True
    assert nmea0183_validate(known_bad) == False
    assert nmea0183_validate("") == False
    assert nmea0183_validate("$*23") == False

def test_parse_msg():
    parts = nmea0183_parse(known_good)
    assert parts == ["PCC", "02"]

def test_parse_msg_validate_bad_checksum():
    parts = nmea0183_parse(known_bad, validate_checksum=True)
    assert parts == False

def test_parse_msg_validate_good_checksum():
    parts = nmea0183_parse(known_good, validate_checksum=False)
    assert parts == ["PCC", "02"]

def test_parse_msg_skip_validate():
    parts = nmea0183_parse(known_bad, validate_checksum=False)
    assert parts == ["PCC", "02"]
