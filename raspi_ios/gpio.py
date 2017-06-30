# -*- coding: utf-8 -*-
import uuid
import RPi.GPIO as GPIO
from .core import RaspiIOHandle
from raspi_io.gpio import GPIOMode, GPIOSetup, GPIOCleanup, GPIOCtrl, GPIOChannel, GPIOSoftPWM, GPIOSoftPWMCtrl
__all__ = ['RaspiGPIOHandle']


class RaspiGPIOHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (ValueError, RuntimeError)

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        print("Success register:{0:s}".format(self.PATH))
        GPIO.setwarnings(False)
        self.__pwm_list = dict()

    async def setmode(self, data):
        data = GPIOMode().loads(data)
        GPIO.setmode(data.mode)

    async def setup(self, data):
        data = GPIOSetup().loads(data)
        if data.direction == GPIOSetup.IN:
            GPIO.setup(data.channel, data.direction, data.pull_up_down)
        else:
            GPIO.setup(data.channel, data.direction, data.pull_up_down, data.initial)

    async def cleanup(self, data):
        data = GPIOCleanup().loads(data)
        GPIO.cleanup(data.channel)

    async def output(self, data):
        data = GPIOCtrl().loads(data)
        GPIO.output(data.channel, data.value)

    async def input(self, data):
        data = GPIOChannel().loads(data)
        return GPIO.input(data.channel)

    async def pwm_init(self, data):
        pwm = GPIOSoftPWM().loads(data)

        # Get pwm instance uuid
        pwm_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "{0:d},{1:d},{2:d}".format(pwm.mode, pwm.channel, pwm.frequency)))

        # Create a pwm instance using uuid as key
        GPIO.setmode(pwm.mode)
        GPIO.setup(pwm.channel, GPIO.OUT)
        self.__pwm_list[pwm_uuid] = GPIO.PWM(pwm.channel, pwm.frequency)

    async def pwm_ctrl(self, data):
        ctrl = GPIOSoftPWMCtrl().loads(data)

        # Get pwm instance
        pwm = self.__pwm_list.get(ctrl.uuid)
        if not isinstance(pwm, GPIO.PWM):
            raise ValueError("Do not found pwm:{}".format(ctrl.uuid))

        # Start or stop pwm, duty == 0 stop pwm
        pwm.start(ctrl.duty) if ctrl.duty else pwm.stop()
