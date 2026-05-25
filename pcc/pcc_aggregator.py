import uvicorn
import zmq
import zmq.asyncio
import argparse
import struct
import asyncio
import traceback
from collections import deque
from time import time, sleep
from datetime import datetime, UTC
from . import PUB_DEVICE, PUB_ENTRY, PUB_LOG, DEFAULT_ZMQ_AGGREGATOR_TRANSPORT, DEFAULT_SQL_LOCATION, DEFAULT_TIME_FORMAT
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Field, Session, SQLModel, create_engine, select, desc, asc, and_
from typing import List
import json

class Device(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    serial_num: str = Field(index=True)


class DeviceEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    device_id: int | None = Field(default=None, foreign_key='device.id')
    event_time: datetime = Field(index=True)
    entry_time: datetime = Field(index=True)
    entry_idx: int | None = Field(default=None, index=True)


class DeviceConnectLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    device_id: int | None = Field(default=None, foreign_key='device.id')
    serial_port: str = Field(index=True)
    event_time: datetime = Field(index=True)
    device_time: datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor_transport_url = app.state.monitor_transport_url
    db_engine_url = app.state.db_engine_url

    zctx = zmq.asyncio.Context()

    try:
        db_engine = create_engine(db_engine_url)
        SQLModel.metadata.create_all(db_engine)
    except SQLModel.exc.ArgumentError:
        print(f"Invalid Database URL '{db_engine_url}'")
        exit(-1)

    app.state.db_engine = db_engine

    gather_task = asyncio.create_task(zmq_gatherer(zctx, db_engine, monitor_transport_url))

    yield

    # Shutdown
    gather_task.cancel()

app = FastAPI(lifespan=lifespan)
app.mount("/html", StaticFiles(directory="html", html=True), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allows all origins
    allow_credentials=True,   # Allows cookies and auth headers
    allow_methods=["*"],      # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],      # Allows all headers
)
async def zmq_gatherer(zctx: zmq.asyncio.Context, db_engine, gather_transport: str):
    try:

        zsock = zctx.socket(zmq.ROUTER)
        zsock.setsockopt(zmq.LINGER, 1000)
        zsock.bind(gather_transport)

        while True:
            try:
                message = await asyncio.wait_for(zsock.recv_multipart(), 1.0)
                print(f"RX: {message}")
                msg_id = message[0].decode('utf-8')
                msg_ts = datetime.fromtimestamp(struct.unpack(">f", message[1])[0], UTC)
                msg_type = message[2].decode('utf-8')

                msg_payload = []
                for part in message[3:]:
                    msg_payload.append(part.decode('utf-8'))

                with Session(db_engine) as session:
                    if msg_type == PUB_DEVICE:
                        device_serial = msg_payload[0]
                        device_time = datetime.strptime(msg_payload[1], DEFAULT_TIME_FORMAT)

                        res = session.exec(select(Device).where(Device.serial_num == device_serial))
                        found_device = res.first()
                        if not found_device:
                            found_device = Device(serial_num=device_serial)
                            session.add(found_device)

                        connect_log = DeviceConnectLog(device_id=found_device.id, event_time=msg_ts, serial_port=msg_id, device_time=device_time)
                        session.add(connect_log)
                        session.commit()

                        # Get latest index
                        latest_device_entry_idx = 0
                        res = session.exec(select(DeviceEntry).order_by(desc(DeviceEntry.entry_idx)).where(DeviceEntry.device_id == found_device.id).limit(1))
                        for entry in res:
                            latest_device_entry_idx = entry.entry_idx

                        zsock.send_multipart([message[0], str(latest_device_entry_idx).encode('utf-8')])

                    elif msg_type == PUB_ENTRY:
                        device_serial = msg_payload[0]
                        entry_time = datetime.strptime(msg_payload[1], DEFAULT_TIME_FORMAT)
                        entry_idx = int(msg_payload[2])

                        device_id = get_device_id_by_serial(session, device_serial)
                        if device_id:
                            # Check for existing entry
                            res = session.exec(select(DeviceEntry).where(and_(DeviceEntry.device_id == device_id,DeviceEntry.entry_idx == entry_idx)))
                            found_entry = res.first()
                            if not found_entry:
                                entry = DeviceEntry(device_id=device_id, event_time=msg_ts, entry_time=entry_time, entry_idx=entry_idx)
                                session.add(entry)
                                session.commit()

                    elif msg_type == PUB_LOG:
                        pass
                    else:
                        pass
                    print(f"Received from {msg_id}, type: {msg_type} at {str(msg_ts)}")

            except Exception as e:
                if str(e) != '':
                    print(traceback.format_exc())

    except asyncio.CancelledError:
        pass

def get_device_id_by_serial(session , serial_num: str):
    res = session.exec(select(Device).where(Device.serial_num == serial_num).limit(1))
    found_device = res.first()
    if not found_device:
        return None
    else:
        return found_device.id

@app.get("/device/{device_serial}/entries", response_model=List[DeviceEntry])
async def get_device_history(request: Request, device_serial: str):
    db_engine = request.app.state.db_engine
    with Session(db_engine) as session:
        device_id = get_device_id_by_serial(session, device_serial)
        if not device_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device with serial number '{device_serial}' was not found")

        entries = []
        res = session.exec(select(DeviceEntry).order_by(desc(DeviceEntry.entry_idx)).where(DeviceEntry.device_id == device_id))
        for entry in res:
            entries.append(entry)

    return entries


@app.get("/device_list", response_model=List[Device])
async def get_device_list(request: Request):
    db_engine = request.app.state.db_engine
    entries = []
    with Session(db_engine) as session:
        res = session.exec(select(Device).order_by(asc(Device.id)))
        for entry in res:
            entries.append(entry.model_dump())

    return entries


@app.get("/")
def redirect_to_static():
    return RedirectResponse(url="/html")

def main():
    parser = argparse.ArgumentParser(prog="pcc-aggregator", description="Aggregator for USB device data")
    parser.add_argument('--monitor-transport', default=DEFAULT_ZMQ_AGGREGATOR_TRANSPORT, type=str, help="ZMQ Transport")
    parser.add_argument('--ip', type=str, default="127.0.0.1", help="REST API IP")
    parser.add_argument('--port', type=int, default=8080, help="REST API Port")
    parser.add_argument('--database', type=str, default=DEFAULT_SQL_LOCATION, help="SQL Database URL")
    args = parser.parse_args()

    # Pass the ZMQ URL to the FastAPI app state so lifespan can access it
    app.state.db_engine_url = args.database
    app.state.monitor_transport_url = args.monitor_transport

    # Run the Uvicorn server programmatically
    # Note: 'reload=True' cannot be used when passing an app object directly
    uvicorn.run(app, host=args.ip, port=args.port)

if __name__ == "__main__":
    main()
