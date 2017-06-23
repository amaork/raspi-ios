# -*- coding: utf-8 -*-
import uuid
import RPi.GPIO as GPIO
from .core import RaspiIOHandle
from raspi_io.gpio import GPIOMode, GPIOSetup, GPIOCtrl, GPIOChannel, GPIOSoftPWM, GPIOSoftPWMCtrl
__all__ = ['RaspiGPIOHandle']


class RaspiGPIOHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        print("Success register:{0:s}".format(self.PATH))
        GPIO.setwarnings(False)
        self.__pwm_list = dict()

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

    async def pwm(self, ws, data):
        pwm = GPIOSoftPWM().loads(data)
        if not isinstance(pwm, GPIOSoftPWM):
            return

        # Get pwm instance uuid
        pwm_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "{0:d},{1:d},{2:d}".format(pwm.mode, pwm.channel, pwm.frequency)))

        # Create a pwm instance using uuid as key
        GPIO.setmode(pwm.mode)
        GPIO.setup(pwm.channel, GPIO.OUT)
        self.__pwm_list[pwm_uuid] = GPIO.PWM(pwm.channel, pwm.frequency)

    async def pwm_ctrl(self, ws, data):
        ctrl = GPIOSoftPWMCtrl().loads(data)
        if not isinstance(ctrl, GPIOSoftPWMCtrl):
            return

        # Get pwm instance
        pwm = self.__pwm_list.get(ctrl.uuid)
        if not isinstance(pwm, GPIO.PWM):
            return

        # Start or stop pwm, duty == 0 stop pwm
        pwm.start(ctrl.duty) if ctrl.duty else pwm.stop()
