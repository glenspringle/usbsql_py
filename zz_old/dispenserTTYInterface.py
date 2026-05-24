# Dispenser USB Serial Port Interface
# websites:
# https://pythonguides.com/python-compare-strings/
# https://realpython.com/python-split-string/#split-with-different-delimiters-using-sep
# https://www.pythoncentral.io/how-to-parse-a-string-in-python-a-step-by-step-guide/
# https://medium.com/@namanlazarus/mastering-the-state-design-pattern-in-python-a-practical-guide-fad8a2778765
# https://python-statemachine.readthedocs.io/en/latest/index.html
#   python3 -m pip install python-statemachine
#   git clone git://github.com/fgmacedo/python-statemachine
#
# https://pytutorial.com/install-python-package-on-raspberry-pi/
# https://raspberrytips.com/install-latest-python-raspberry-pi/
# 
from time import time
import serial
import re
#from statemachine import StateChart, State

ser = serial.Serial(port='/dev/ttyACM0',
                    baudrate=115200,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=1)
print (ser.name)
state = 0
while 1:
        # Request => $PCC_REQ_STATUS*<xx>
        #       <xx> = checksum
    if (state==0):
        ser.write('$PCC_REQ_STATUS*xx\n'.encode('utf-8'))
        reqStatusTime=time()
        state = 1
        # Response => $PCC_SN,<serial number string>,year,month,date,seconds,entryCount,lastEntry*<xx>
        #       <xx> = checksum
    elif (state==1):
        string=ser.readline()
        strText=string.decode('utf-8')
        strRESplit=re.split(r"[,|*|\s]", strText)
        if (strRESplit[0] == "$PCC_STATUS"):
                #print (strRESplit)
            serialNumber = strRESplit[1]
            year    = strRESplit[2]
            month   = strRESplit[3]
            date    = strRESplit[4]
            seconds = strRESplit[5]
            entryCount= strRESplit[6]
            lastEntry = strRESplit[7]
            print ("S/N,Y,M,D,S,E,L:{sn},{year},{month},{day},{sec},{ec},{le}".format(sn=serialNumber,year=year,month=month,day=date,sec=seconds,ec=entryCount,le=lastEntry))
            pollCount = int(entryCount) # prepare for Use Time Requests
            state = 2
        else:
            state = 0
    # Request => $PCC_REQ_USETIME,<count>
    #        <count> is an identifier where zero (0) is
    #               the most recent entry, one (1) is the
    #               next most recent, etc
    elif (state==2):
        reqStr="$PCC_REQ_USETIME,{}*xx\n".format(pollCount)
        #print(reqStr)
        ser.write(reqStr.encode('utf-8'))
        state = 3
    # Response => $PCC_USETIME,<count>,<index>,<YYYY>,<MM>,<DD>,<Seconds>
    #        <count> is an identifier where zero (0) is
    #               the most recent entry
    #        <index> is an identifier that starts from
    #               zero (0) when the device was first initialized
    elif (state==3):
        str=ser.readline()
        strText=str.decode('utf-8')
        strRESplit=re.split(r"[,|*|\s]", strText)
        if (strRESplit[0] == "$PCC_USETIME"):
            #print (strRESplit)
            devicePollCount= strRESplit[1]
            deviceUseYear  = strRESplit[2]
            deviceUseMonth = strRESplit[3]
            deviceUseDay   = strRESplit[4]
            deviceUseTime  = strRESplit[5]
            print ("Use Index,Time: {count},{year},{month},{day},{time}".format(count=devicePollCount,year=deviceUseYear,month=deviceUseMonth,day=deviceUseDay,time=deviceUseTime))
            #print ("Use Index: ",deviceUseIndex)
            if (pollCount != int(lastEntry)):
                pollCount=pollCount-1
                state = 2
            else:
                diffTime = time()-reqStatusTime
                print(f"{diffTime:.3f} sec")
                print("No more data")
                state = 0
        else:
            state = 0
    else:
        state=0
        
        