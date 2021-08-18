# -*- coding: utf-8 -*-
import glob
import pylibi2c
from .core import RaspiIOHandle
from .server import register_handle
from raspi_io.i2c import I2CRead, I2CWrite, I2CDevice
__all__ = ['RaspiI2CHandle']


@register_handle
class RaspiI2CHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (TypeError, ValueError, RuntimeError, AttributeError, IOError)

    def __init__(self):
        super(RaspiI2CHandle, self).__init__()
        self.__device = None

    def __del__(self):
        if isinstance(self.__device, pylibi2c.I2CDevice):
            self.__device.close()

    @staticmethod
    def get_nodes():
        return glob.glob("/dev/i2c-*")

    async def open(self, ws, data):
        # Parse request
        device = I2CDevice(**data).__dict__
        device.pop("handle")

        # First open i2c bus
        self.__device = pylibi2c.I2CDevice(**device)

    async def read(self, ws, data):
        req = I2CRead(**data)
        if req.is_ioctl_read():
            buf = self.__device.ioctl_read(req.addr, req.size)
        else:
            buf = self.__device.read(req.addr, req.size)

        return self.encode_data(buf)

    async def write(self, ws, data):
        req = I2CWrite(**data)
        data = self.decode_data(req.data)
        if req.is_ioctl_write():
            ret = self.__device.ioctl_write(req.addr, data)
        else:
            ret = self.__device.write(req.addr, data)

        return ret
