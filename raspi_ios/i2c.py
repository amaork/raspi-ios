# -*- coding: utf-8 -*-
import glob
import pylibi2c
from .core import RaspiIOHandle
from raspi_io.i2c import I2COpen, I2CClose, I2CRead, I2CWrite, I2CDevice
__all__ = ['RaspiI2CHandle']


class RaspiI2CHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (TypeError, ValueError, RuntimeError, AttributeError)

    def __init__(self):
        super(RaspiI2CHandle, self).__init__()
        self.__device = dict()

    def __del__(self):
        bus = self.__device.get('bus')
        if isinstance(bus, int) and bus > 0:
            pylibi2c.close(self.__device['bus'])

    @staticmethod
    def get_nodes():
        return glob.glob("/dev/i2c-*")

    async def open(self, data):
        # Parse request
        req = I2COpen(**data)
        device = I2CDevice(**req.device)

        # First open i2c bus
        bus = pylibi2c.open(device.bus)
        if bus == -1:
            raise RuntimeError('Open i2c bus:{} error'.format(device.name))

        # Save i2c device
        self.__device = device.__dict__
        self.__device['bus'] = bus

    async def close(self, data):
        req = I2CClose(**data)
        bus = self.__device.get('bus')
        if isinstance(bus, int) and bus > 0:
            pylibi2c.close(self.__device['bus'])

    async def read(self, data):
        req = I2CRead(**data)
        buf = bytes(req.size)
        if req.is_ioctl_read():
            ret = pylibi2c.ioctl_read(self.__device, req.addr, buf, req.size)
        else:
            ret = pylibi2c.read(self.__device, req.addr, buf, req.size)

        return self.encode_data(buf) if ret == req.size else None

    async def write(self, data):
        req = I2CWrite(**data)
        data = self.decode_data(req.data)
        if req.is_ioctl_write():
            ret = pylibi2c.ioctl_write(self.__device, req.addr, data, len(data))
        else:
            ret = pylibi2c.write(self.__device, req.addr, data, len(data))

        return ret
