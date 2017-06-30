Raspi-ios 
========
Raspberry Pi websocket server, manage raspberry pi, and accept [raspi-io](https://github.com/amaork/raspi-io) control

## Features

- Support Python3.5+

- Support GPIO, PWM control

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
