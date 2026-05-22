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
        # Request => $PCC_REQ_USETIME,<count>*<xx>
        #        <count> = entryCount is most recent time the device was used
        #        <count> = entryCount-1 is next most recent time the device was used
        #        <count> = lastEntry is last entry in the device log
        elif (state==2):
            reqStr="$PCC_REQ_USETIME,{}*xx\n".format(pollCount)
            #print(reqStr)
            ser.write(reqStr.encode('utf-8'))
            state = 3
        # Response => $PCC_USETIME,<count>,<index>,<year>,<month>,<date>,<seconds>*<xx>
        #        <count> = entryCount is most recent time the device was used
        #        <count> = entryCount-1 is next most recent time the device was used
        #        <count> = lastEntry is last entry in the device log
        #        <year>,<month>,<date> = date
        #        <seconds> = time since midnight in seconds
        elif (state==3):
            string=ser.readline()
            strText=string.decode('utf-8')
            strRESplit=re.split(r"[,|*|\s]", strText)
            if (strRESplit[0] == "$PCC_USETIME"):
                #print (strRESplit)
                devicePollCount= strRESplit[1]
                deviceUseYear  = strRESplit[2]
                deviceUseMonth = strRESplit[3]
                deviceUseDay   = strRESplit[4]
                deviceUseTime  = strRESplit[5]
                print ("Count,Y,M,D,T: {count},{year},{month},{day},{sec}".format(count=devicePollCount,year=deviceUseYear,month=deviceUseMonth,day=deviceUseDay,sec=deviceUseTime))
                #print ("Use Index: ",deviceUseIndex)
                if (pollCount != int(lastEntry)):
                    pollCount=pollCount - 1
                    state = 2
                else:
                    diffTime=time()-reqStatusTime
                    print(f"{diffTime:.3f} sec")
                    print("No more data")
                    state = 0
            else:
                state = 0
#        else:
#            state=0


if __name__ == '__main__':
    main()
