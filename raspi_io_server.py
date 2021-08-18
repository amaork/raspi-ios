#!/usr/bin/env python3.5
import daemon
import lockfile
from raspi_ios.server import RaspiIOServer, get_registered_handles


if __name__ == "__main__":
    with daemon.DaemonContext(pidfile=lockfile.FileLock("/var/run/raspi_io_server.pid")):
        server = RaspiIOServer()

        for handle in get_registered_handles():
            server.register(handle)

        server.run_forever()
