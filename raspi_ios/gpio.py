# -*- coding: utf-8 -*-
import uuid
import RPi.GPIO as GPIO
from .core import RaspiIOHandle
from raspi_io.gpio import GPIOMode, GPIOSetup, GPIOCleanup, GPIOCtrl, GPIOChannel, GPIOSoftPWM, GPIOSoftPWMCtrl
__all__ = ['RaspiGPIOHandle']


class RaspiGPIOHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        print("Success register:{0:s}".format(self.PATH))
        GPIO.setwarnings(False)
        self.__pwm_list = dict()

    async def setmode(self, data):
        try:

            data = GPIOMode().loads(data)
            GPIO.setmode(data.mode)

        except ValueError as err:
            raise RuntimeError(err)

    async def setup(self, data):
        try:

            data = GPIOSetup().loads(data)
            if data.direction == GPIOSetup.IN:
                GPIO.setup(data.channel, data.direction, data.pull_up_down)
            else:
                GPIO.setup(data.channel, data.direction, data.pull_up_down, data.initial)

        except ValueError as err:
            raise RuntimeError(err)

    async def cleanup(self, data):
        try:

            data = GPIOCleanup().loads(data)
            GPIO.cleanup(data.channel)

        except ValueError as err:
            raise RuntimeError(err)

    async def output(self, data):
        try:

            data = GPIOCtrl().loads(data)
            GPIO.output(data.channel, data.value)

        except ValueError as err:
            raise RuntimeError(err)

    async def input(self, data):
        try:

            data = GPIOChannel().loads(data)
            return GPIOCtrl(channel=data.channel, value=GPIO.input(data.channel)).dumps()

        except ValueError as err:
            raise RuntimeError(err)

    async def pwm_init(self, data):
        try:

            pwm = GPIOSoftPWM().loads(data)

            # Get pwm instance uuid
            pwm_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "{0:d},{1:d},{2:d}".format(
                pwm.mode, pwm.channel, pwm.frequency)))

            # Create a pwm instance using uuid as key
            GPIO.setmode(pwm.mode)
            GPIO.setup(pwm.channel, GPIO.OUT)
            self.__pwm_list[pwm_uuid] = GPIO.PWM(pwm.channel, pwm.frequency)

        except ValueError as err:
            raise RuntimeError(err)

    async def pwm_ctrl(self, data):
        try:

            ctrl = GPIOSoftPWMCtrl().loads(data)

            # Get pwm instance
            pwm = self.__pwm_list.get(ctrl.uuid)
            if not isinstance(pwm, GPIO.PWM):
                raise RuntimeError("Do not found pwm:{}".format(ctrl.uuid))

            # Start or stop pwm, duty == 0 stop pwm
            pwm.start(ctrl.duty) if ctrl.duty else pwm.stop()

        except ValueError as err:
            raise RuntimeError(err)
