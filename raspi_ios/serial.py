# -*- coding: utf-8 -*-
import glob
import fcntl
import serial
from .core import RaspiIOHandle
from .server import register_handle
from raspi_io.serial import SerialInit, SerialClose, SerialRead, SerialWrite, SerialFlush, SerialBaudrate
__all__ = ['RaspiSerialHandle']


@register_handle
class RaspiSerialHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (serial.SerialException, ValueError, RuntimeError, BlockingIOError)

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        self.__port = serial.Serial()

    def __del__(self):
        self.__port.close()

    @staticmethod
    def get_nodes():
        return glob.glob("/dev/ttyS*") + glob.glob("/dev/ttyUSB*")

    async def init(self, ws, data):
        # Parse request
        setting = SerialInit(**data)

        # Create a serial port instance
        self.__port = serial.Serial(
            port=setting.port, baudrate=setting.baudrate, bytesize=setting.bytesize,
            parity=setting.parity, stopbits=setting.stopbits, timeout=setting.timeout)
        self.__port.flushInput()
        self.__port.flushOutput()

        # Acquire an exclusive lock
        fcntl.flock(self.__port.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    async def close(self, ws, data):
        req = SerialClose(**data)
        if self.__port.is_open:
            self.__port.flushInput()
            self.__port.flushOutput()
            self.__port.close()

    async def read(self, ws, data):
        # Parse request
        req = SerialRead(**data)

        # Return read data
        data = self.__port.read(req.size)
        if len(data) == 0:
            raise RuntimeError("timeout")

        return self.encode_data(data)

    async def write(self, ws, data):
        req = SerialWrite(**data)
        data = self.decode_data(req.data)

        # Write data to serial
        return self.__port.write(data)

    async def flush(self, ws, data):
        req = SerialFlush(**data)

        # Flush serial port
        if req.where == SerialFlush.IN:
            self.__port.flushInput()
        elif req.where == SerialFlush.OUT:
            self.__port.flushOutput()
        elif req.where == SerialFlush.BOTH:
            self.__port.flushInput()
            self.__port.flushOutput()

    async def set_baudrate(self, ws, data):
        req = SerialBaudrate(**data)
        self.__port.baudrate = req.baudrate
