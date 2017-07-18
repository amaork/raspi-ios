Raspi-ios
========
Raspberry Pi websocket server, manage raspberry pi, and accept [raspi-io](https://github.com/amaork/raspi-io) control

## Features

- Require Python3.5+

- Support I2C ([pylibi2c](https://github.com/amaork/libi2c))

- Support Serial ([pyserial](https://github.com/pyserial/pyserial))

- Support GPIO, Software PWM ([RPi.GPIO](https://sourceforge.net/projects/raspberry-gpio-python/))

## Installation

1. First install Python3.5, refer: [Installing Python 3.5 on Raspbian](https://gist.github.com/BMeu/af107b1f3d7cf1a2507c9c6429367a3b)

2. Second install requires: `asyncio`, `websockets`, `RPi.GPIO`, `pyserial`, `raspi_io`, `pylibi2c`

3. Finally install `raspi_ios`: `sudo python3.5 setup.py install `

## Usage

    from raspi_ios import RaspiIOServer, RaspiGPIOHandle, RaspiQueryHandle, RaspiSerialHandle

    # Create a raspi io server
    server = RaspiIOServer()

    # Register gpio handle (GPIO, SoftPWM support)
    server.register(RaspiGPIOHandle)

    # Register information query handle (raspi_io.Query)
    server.register(RaspiQueryHandle)

    # Register serial port handle (raspi_io.Serial)
    server.register(RaspiSerialHandle)

    # Running server
    server.run("0.0.0.0", 12345)
