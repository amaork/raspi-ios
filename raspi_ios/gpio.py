# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
from .core import RaspiIOHandle
from raspi_io.gpio import GPIOMode, GPIOSetup, GPIOCtrl, GPIOChannel
__all__ = ['RaspiGPIOHandle']


class RaspiGPIOHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        print("Success register:{0:s}".format(self.PATH))
        GPIO.setwarnings(False)

    async def setmode(self, ws, data):
        data = GPIOMode().loads(data)
        if isinstance(data, GPIOMode):
            GPIO.setmode(data.mode)

    async def setup(self, ws, data):
        data = GPIOSetup().loads(data)
        if isinstance(data, GPIOSetup):
            if data.direction == GPIOSetup.IN:
                GPIO.setup(data.channel, data.direction, data.pull_up_down)
            else:
                GPIO.setup(data.channel, data.direction, data.pull_up_down, data.initial)

    async def output(self, ws, data):
        data = GPIOCtrl().loads(data)
        if isinstance(data, GPIOCtrl):
            GPIO.output(data.channel, data.value)

    async def input(self, ws, data):
        data = GPIOChannel().loads(data)
        if isinstance(data, GPIOChannel):
            result = GPIOCtrl(channel=data.channel, value=GPIO.input(data.channel))
            await ws.send(result.dumps())
