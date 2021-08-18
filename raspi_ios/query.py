# -*- coding: utf-8 -*-
import os
import glob
from .version import version
from .core import RaspiIOHandle
from .server import register_handle
from raspi_io.query import QueryDevice, QueryHardware, QueryVersion, RebootSystem
__all__ = ['RaspiQueryHandle']


@register_handle
class RaspiQueryHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (ValueError, RuntimeError)

    def __init__(self):
        super(RaspiIOHandle, self).__init__()

    @staticmethod
    def get_nodes():
        return [RaspiQueryHandle.PATH]

    @staticmethod
    def ls_query(path, keyword):
        ret = os.popen("ls {0:s} | grep {1:s}".format(path, keyword))
        return ret.read().strip()

    @staticmethod
    def awk_query(cmd, keyword, location):
        ret = os.popen("{0:s} | grep {1:s} | awk '{{print ${2:d}}}'".format(cmd, keyword, location))
        return ret.read().strip()

    @staticmethod
    def glob_query(keyword):
        return glob.glob(keyword)

    async def reboot(self, ws, data):
        reboot = RebootSystem(**data)
        return self.reboot_system(reboot.delay)

    async def query_version(self, ws, data):
        ver = QueryVersion(**data)
        ver.server = version
        ver = ver.dict
        ver.pop('handle')
        return ver

    async def query_hardware(self, ws, data):
        query = QueryHardware(**data)
        if query.query == QueryHardware.HARDWARE:
            cmd = "cat /proc/cpuinfo"
            sn = self.awk_query(cmd, "Serial", 3)
            hardware = self.awk_query(cmd, "Hardware", 3)
            revision = self.awk_query(cmd, "Revision", 3)
            return hardware, revision, sn
        elif query.query == QueryHardware.ETHERNET:
            if query.params not in self.awk_query("ifconfig -s -a", "\ ", 1).split("\n")[1:]:
                raise ValueError("Unknown ethernet interface:{}".format(query.params))
            return self.awk_query("ifconfig {}".format(query.params), "netmask", 2)
        else:
            raise ValueError("Unknown hardware query")

    async def query_device(self, ws, data):
        query = QueryDevice(**data)
        if query.query == QueryDevice.ETH:
            interfaces = self.awk_query("ifconfig -s -a", "\ ", 1).split("\n")[1:]
            if "lo" in interfaces:
                interfaces.remove("lo")
            return interfaces
        elif query.query == QueryDevice.I2C:
            return self.glob_query("/dev/i2c-*")
        elif query.query == QueryDevice.SPI:
            return self.glob_query("/dev/spidev*")
        elif query.query == QueryDevice.SERIAL:
            port_list = self.glob_query("/dev/ttyS*") + self.glob_query("/dev/ttyUSB*")
            return port_list if query.option else list(filter(lambda port: not os.path.islink(port), port_list))
        elif query.query == QueryDevice.FILTER:
            return self.glob_query(os.path.join("/dev", query.filter))
        else:
            raise ValueError("Unknown device query")
