# -*- coding: utf-8 -*-
import glob
import spidev
from .core import RaspiIOHandle
from raspi_io.spi import SPIOpen, SPIClose, SPIRead, SPIWrite, SPIXfer, SPIXfer2
__all__ = ['RaspiSPIHandle']


class RaspiSPIHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (IOError, ValueError, RuntimeError, IOError, AttributeError)

    def __init__(self):
        super(RaspiSPIHandle, self).__init__()
        self.__spi = spidev.SpiDev()

    def __del__(self):
        self.__spi.close()

    @staticmethod
    def get_nodes():
        return glob.glob("/dev/spidev*")

    async def open(self, ws, data):
        device = SPIOpen(**data)
        if device.device not in self.get_nodes():
            raise IOError("Open spi device error, no such device:{}".format(device.device))

        # Get spi bus and dev from device name
        node = device.device.split("spidev")[-1]
        bus = int(node.split(".")[0])
        dev = int(node.split(".")[1])

        # Open device
        self.__spi.open(bus, dev)

        # Set attribute
        self.__spi.max_speed_hz = device.max_speed * 1000
        self.__spi.threewire = device.threewire
        self.__spi.lsbfirst = device.lsbfirst
        self.__spi.cshigh = device.cshigh
        self.__spi.no_cs = device.no_cs
        self.__spi.loop = device.loop
        self.__spi.mode = device.mode

    async def close(self, ws, data):
        req = SPIClose(**data)
        self.__spi.close()

    async def read(self, ws, data):
        req = SPIRead(**data)
        result = self.__spi.readbytes(req.size)
        return self.encode_data(result) if len(result) == req.size else None

    async def write(self, ws, data):
        req = SPIWrite(**data)
        data = self.decode_data(req.data)
        self.__spi.writebytes(list(data))
        return len(data)

    async def xfer(self, ws, data):
        req = SPIXfer(**data)
        write_data = self.decode_data(req.write_data)
        speed = req.speed * 1000 or self.__spi.max_speed_hz
        read_data = self.__spi.xfer(list(write_data) + [0] * req.read_size, speed, req.delay)
        return self.encode_data(bytes(read_data)[len(write_data):])

    async def xfer2(self, ws, data):
        req = SPIXfer2(**data)
        write_data = self.decode_data(req.write_data)
        speed = req.speed * 1000 or self.__spi.max_speed_hz
        read_data = self.__spi.xfer2(list(write_data) + [0] * req.read_size, speed, req.delay)
        return self.encode_data(bytes(read_data)[len(write_data):])
