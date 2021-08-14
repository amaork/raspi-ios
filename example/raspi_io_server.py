#!/usr/bin/env python3.5
import daemon
import lockfile
from raspi_ios import *


if __name__ == "__main__":
    with daemon.DaemonContext(pidfile=lockfile.FileLock("/var/run/raspi_io_server.pid")):
        server = RaspiIOServer()
        server.register(RaspiI2CHandle)
        server.register(RaspiSPIHandle)
        server.register(RaspiGPIOHandle)
        server.register(RaspiQueryHandle)
        server.register(RaspiSerialHandle)
        server.register(RaspiUpdateHandle)
        server.register(RaspiMmalGraphHandle)
        server.register(RaspiTVServiceHandle)
        server.register(RaspiSPIFlashHandle)
        server.register(RaspiGPIOSPIFlashHandle)
        server.run_forever()
