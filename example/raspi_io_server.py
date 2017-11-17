#!/usr/bin/env python3.5
from raspi_ios import *


if __name__ == "__main__":
    server = RaspiIOServer()
    server.register(RaspiI2CHandle)
    server.register(RaspiSPIHandle)
    server.register(RaspiGPIOHandle)
    server.register(RaspiQueryHandle)
    server.register(RaspiSerialHandle)
    server.register(RaspiMmalGraphHandle)
    server.register(RaspiTVServiceHandle)
    server.run_forever()
