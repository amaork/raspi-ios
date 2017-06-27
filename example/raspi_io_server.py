#!/usr/bin/env python3.5

from raspi_ios import *


if __name__ == "__main__":
    server = RaspiIOServer()
    server.register(RaspiGPIOHandle)
    server.run("0.0.0.0", 9876)
