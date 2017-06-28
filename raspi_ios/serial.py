# -*- coding: utf-8 -*-
import serial
from .core import RaspiIOHandle
from raspi_io.serial import SerialInit, SerialClose, SerialRead, SerialWrite, SerialFlush
__all__ = ['RaspiSerialHandle']


class RaspiSerialHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (serial.SerialException, ValueError, RuntimeError)

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        print("Success register:{}".format(self.PATH))
        self.__list = dict()

    def __get_serial(self, name):
        port = self.__list.get(name)
        if not isinstance(port, serial.Serial):
            raise ValueError("Do not found serial port:{}".format(name))

        return port

    async def init(self, data):
        # Parse request
        setting = SerialInit().loads(data)

        # Check if port is already opened
        if setting.port in self.__list:
            raise RuntimeError("Serial:{} is occupied".format(setting.port))

        # Create a serial port instance
        port = serial.Serial(
            port=setting.port, baudrate=setting.baudrate, bytesize=setting.bytesize,
            parity=setting.parity, stopbits=setting.stopbits, timeout=setting.timeout)
        port.flushInput()
        port.flushOutput()

        self.__list[setting.port] = port

    async def close(self, data):
        req = SerialClose().loads(data)

        port = self.__get_serial(req.port)
        port.flushInput()
        port.flushOutput()
        port.close()

        del self.__list[req.port]

    async def read(self, data):
        # Parse request
        req = SerialRead().loads(data)

        # Get serial port object
        port = self.__get_serial(req.port)

        # Return read data
        data = port.read(req.size).decode("utf-8")
        if len(data) == 0:
            raise RuntimeError("timeout")

        return data

    async def write(self, data):
        req = SerialWrite().loads(data)

        # Get serial port object
        port = self.__get_serial(req.port)

        # Write data to serial
        return port.write(req.data.encode("ascii"))

    async def flush(self, data):
        req = SerialFlush().loads(data)

        # Get serial port object
        port = self.__get_serial(req.port)

        # Flush serial port
        if req.where == SerialFlush.IN:
            port.flushInput()
        elif req.where == SerialFlush.OUT:
            port.flushOutput()
        elif req.where == SerialFlush.BOTH:
            port.flushInput()
            port.flushOutput()
