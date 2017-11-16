Raspi-ios
========
Raspberry Pi [raspi-io](https://github.com/amaork/raspi-io) server

## Features

- Require Python3.5+

- Support I2C ([pylibi2c](https://github.com/amaork/libi2c))

- Support SPI ([Spidev](https://github.com/doceme/py-spidev))

- Support Serial ([pyserial](https://github.com/pyserial/pyserial))

- Support GPIO, Software PWM ([RPi.GPIO](https://sourceforge.net/projects/raspberry-gpio-python/))

- Support TVService, HDMI video settings interface ([pylibmmal.TVService](https://github.com/amaork/pylibmmal))

## Installation

1. First install Python3.5, refer: [Installing Python 3.5 on Raspbian](https://gist.github.com/BMeu/af107b1f3d7cf1a2507c9c6429367a3b)

2. Second install requires: raspi_io: 

    ```bash
    $ sudo pip3.5 install git+https://github.com/amaork/raspi-io.git
    ```

3. Finally install raspi_ios:

    ```bash
    $ sudo python3.5 setup.py install
    ```

    ​	or 

    ```bash
    $ sudo pip3.5 install git+https://github.com/amaork/raspi-ios.git
    ```

## Default port

`raspi_ios` default listen on port **`9876`**, you can change it like this:

```python
from raspi_ios import RaspiIOServer
server = RaspiIOServer(port=xxxx)
```

## Usage

```python
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
server.run_forever()
```

## Example

```bash
$ python3.5 -m raspi_ios.io_server
```
