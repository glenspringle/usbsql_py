from time import time
import signal
import argparse
import serial
import re
from .graceful_exiter import GracefulExiter



def main():
    flag = GracefulExiter()

    parser = argparse.ArgumentParser(prog='proj_name', description='USB Serial Program')
    parser.add_argument('port', type=str, help="Serial port to use")
    parser.add_argument('-b', '--baudrate', default=115200, type=int, help="Baud rate")

    args = parser.parse_args()

    ser = serial.Serial(port=args.port,
                    baudrate=args.baudrate,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=1)
    print (ser.name)
    state = 0
    while not flag.exit():
        # Request => $PCC_REQ_SN*<xx>
        #       <xx> = checksum
        if (state==0):
            ser.write('$PCC_REQ_SN*xx\n'.encode('utf-8'))
            reqSNTime=time()
            state = 1
        # Response => $PCC_SN,<serial number string>*<xx>
        #       <xx> = checksum
        elif (state==1):
            string=ser.readline()
            strText=string.decode('utf-8')
# Debugging
#            if (ser.in_waiting > 0):
#                string=ser.read()
#                strText=string.decode('utf-8')
#                print(strText)
#                if strText=='*':
#                    state=0
            strRESplit=re.split(r"[,|*|\s]", strText)
            if (strRESplit[0] == "$PCC_SN"):
                #print (strRESplit)
                serialNumber = strRESplit[1]
                print ("S/N:",serialNumber)
                state = 2
            else:
                state = 0
        # Request => $PCC_REQ_TIME*<xx>
        elif (state==2):
            ser.write('$PCC_REQ_TIME*xx\n'.encode('utf-8'))
            state = 3
        # Response => $PCC_TIME,<year>,<month>,<day>,<seconds>*<xx>
        #       <year>,<month>,<day> = date
        #       <seconds> = time since midnight in seconds
        elif (state==3):
            string=ser.readline()
            strText=string.decode('utf-8')
            strRESplit=re.split(r"[,|*|\s]", strText)
            if (strRESplit[0] == "$PCC_TIME"):
                #print (strRESplit)
                deviceYear  = strRESplit[1]
                deviceMonth = strRESplit[2]
                deviceDay   = strRESplit[3]
                deviceTime  = strRESplit[4]
                print ("Device Time(Y,M,D,T): {year},{month},{day},{time}".format(year=deviceYear,month=deviceMonth,day=deviceDay,time=deviceTime))
                state = 4
                pollCount=0 # prepare for Use Time Requests
            else:
                state = 0
        # Request => $PCC_REQ_USETIME,<count>*<xx>
        #        <count> = 0 is most recent time the device was used
        #        <count> = 1 is next most recent time the device was used
        elif (state==4):
            reqStr="$PCC_REQ_USETIME,{}*xx\n".format(pollCount)
            #print(reqStr)
            ser.write(reqStr.encode('utf-8'))
            state = 5
        # Response => $PCC_USETIME,<count>,<index>,<year>,<month>,<day>,<seconds>*<xx>
        #        <count> = 0 is most recent time the device was used
        #        <count> = 1 is next most recent time the device was used
        #        <index> is an identifier count that starts from
        #               zero (0) when the device was new
        #       <year>,<month>,<day> = date
        #       <seconds> = time since midnight in seconds
        elif (state==5):
            string=ser.readline()
            strText=string.decode('utf-8')
            strRESplit=re.split(r"[,|*|\s]", strText)
            if (strRESplit[0] == "$PCC_USETIME"):
                #print (strRESplit)
                devicePollCount= strRESplit[1]
                deviceUseIndex = strRESplit[2]
                deviceUseYear  = strRESplit[3]
                deviceUseMonth = strRESplit[4]
                deviceUseDay   = strRESplit[5]
                deviceUseTime  = strRESplit[6]
                print ("Count,Index,Y,M,D,T: {count},{index},{year},{month},{day},{time}".format(count=devicePollCount,index=deviceUseIndex,year=deviceUseYear,month=deviceUseMonth,day=deviceUseDay,time=deviceUseTime))
                #print ("Use Index: ",deviceUseIndex)
                if (deviceUseIndex != '0'):
                    pollCount=1+pollCount
                    state = 4
                else:
                    diffTime=time()-reqSNTime
                    print(f"{diffTime:.3f} sec")
                    print("No more data")
                    state = 0
            else:
                state = 0
#        else:
#            state=0


if __name__ == '__main__':
    main()
