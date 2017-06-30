# -*- coding: utf-8 -*-
import os
import serial.tools.list_ports
from .core import RaspiIOHandle
from raspi_io.query import QueryDevice, QueryHardware
__all__ = ['RaspiQueryHandle']


class RaspiQueryHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (ValueError, RuntimeError)

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        print("Success register:{}".format(self.PATH))

    @staticmethod
    def ls_query(path, keyword):
        ret = os.popen("ls {0:s} | grep {1:s}".format(path, keyword))
        return ret.read().strip()

    @staticmethod
    def awk_query(cmd, keyword, location):
        ret = os.popen("{0:s} | grep {1:s} | awk '{{print ${2:d}}}'".format(cmd, keyword, location))
        return ret.read().strip()

    async def query_hardware(self, data):
        query = QueryHardware().loads(data)
        if query.query == QueryHardware.HARDWARE:
            cmd = "cat /proc/cpuinfo"
            sn = self.awk_query(cmd, "Serial", 3)
            hardware = self.awk_query(cmd, "Hardware", 3)
            revision = self.awk_query(cmd, "Revision", 3)
            return hardware, revision, sn
        elif query.query == QueryHardware.ETHERNET:
            if query.params not in self.awk_query("ifconfig -s -a", "\ ", 1).split("\n")[1:]:
                raise ValueError("Unknown ethernet interface:{}".format(query.params))
            return self.awk_query("ifconfig", query.params, 5)
        else:
            raise ValueError("Unknown hardware query")

    async def query_device(self, data):
        path = "/dev"
        query = QueryDevice().loads(data)
        if query.query == QueryDevice.ETH:
            interfaces = self.awk_query("ifconfig -s -a", "\ ", 1).split("\n")[1:]
            interfaces.remove("lo")
            return interfaces
        elif query.query == QueryDevice.I2C:
            return [os.path.join(path, dev) for dev in self.ls_query(path, "i2c-*").split("\n")]
        elif query.query == QueryDevice.SPI:
            return [os.path.join(path, dev) for dev in self.ls_query(path, "spidev*").split("\n")]
        elif query.query == QueryDevice.SERIAL:
            return [port[0] for port in list(serial.tools.list_ports.comports())]
        elif query.query == QueryDevice.FILTER:
            return [os.path.join(path, dev) for dev in self.ls_query(path, query.filter).split("\n")]
        else:
            raise ValueError("Unknown device query")
