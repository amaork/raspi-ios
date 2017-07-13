# -*- coding: utf-8 -*-
import serial
from .core import RaspiIOHandle
from raspi_io.serial import SerialInit, SerialClose, SerialRead, SerialWrite, SerialFlush
__all__ = ['RaspiSerialHandle']


class RaspiSerialHandle(RaspiIOHandle):
    SERIAL_LIST = list()
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (serial.SerialException, ValueError, RuntimeError)

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        self.__port = serial.Serial()

    def __del__(self):
        if self.__port.is_open:
            self.__port.flushInput()
            self.__port.flushOutput()
            self.__port.close()

        if self.__port.name in self.SERIAL_LIST:
            self.SERIAL_LIST.remove(self.__port.name)

    async def init(self, data):
        # Parse request
        setting = SerialInit(**data)

        # Check if is occupied
        if setting.port in self.SERIAL_LIST:
            raise RuntimeError("Serial:{} is occupied".format(setting.port))

        # Create a serial port instance
        self.__port = serial.Serial(
            port=setting.port, baudrate=setting.baudrate, bytesize=setting.bytesize,
            parity=setting.parity, stopbits=setting.stopbits, timeout=setting.timeout)
        self.__port.flushInput()
        self.__port.flushOutput()

        # Add serial to serial list
        self.SERIAL_LIST.append(self.__port.name)

    async def close(self, data):
        req = SerialClose(**data)
        if self.__port.is_open:
            self.__port.flushInput()
            self.__port.flushOutput()
            self.__port.close()
            self.SERIAL_LIST.remove(self.__port.name)

    async def read(self, data):
        # Parse request
        req = SerialRead(**data)

        # Return read data
        data = self.__port.read(req.size).decode("utf-8")
        if len(data) == 0:
            raise RuntimeError("timeout")

        return data

    async def write(self, data):
        req = SerialWrite(**data)

        # Write data to serial
        return self.__port.write(req.data.encode("ascii"))

    async def flush(self, data):
        req = SerialFlush(**data)

        # Flush serial port
        if req.where == SerialFlush.IN:
            self.__port.flushInput()
        elif req.where == SerialFlush.OUT:
            self.__port.flushOutput()
        elif req.where == SerialFlush.BOTH:
            self.__port.flushInput()
            self.__port.flushOutput()
