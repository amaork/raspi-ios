# -*- coding: utf-8 -*-
from . import *


if __name__ == "__main__":
    server = RaspiIOServer()
    server.register(RaspiI2CHandle)
    server.register(RaspiSPIHandle)
    server.register(RaspiGPIOHandle)
    server.register(RaspiQueryHandle)
    server.register(RaspiSerialHandle)
    server.register(RaspiUpdateHandle)
    server.register(RaspiTVServiceHandle)
    server.register(RaspiMmalGraphHandle)
    server.register(RaspiSPIFlashHandle)
    server.register(RaspiGPIOSPIFlashHandle)
    server.run_forever()
