# -*- coding: utf-8 -*-
import uuid
import RPi.GPIO as GPIO
from .core import RaspiIOHandle
from raspi_io.gpio import GPIOMode, GPIOSetup, GPIOCleanup, GPIOCtrl, GPIOChannel, GPIOSoftPWM, GPIOSoftPWMCtrl
__all__ = ['RaspiGPIOHandle']


class RaspiGPIOHandle(RaspiIOHandle):
    IO_RES = list()
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (ValueError, RuntimeError)

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        GPIO.setwarnings(False)
        self.__io_res = list()
        self.__pwm_list = dict()

    def __del__(self):
        GPIO.cleanup(self.__io_res)
        self.release_gpio(self.__io_res)

    def check_gpio(self, gpio):
        """Check if gpio is occupied

        :param gpio: gpio number or gpio list
        :return: occupied raise RuntimeError
        """
        if isinstance(gpio, (tuple, list)):
            for channel in gpio:
                self.check_gpio(channel)
        else:
            if gpio in self.IO_RES and gpio not in self.__io_res:
                raise RuntimeError("Channel:{} is occupied".format(gpio))

    def register_gpio(self, gpio):
        if isinstance(gpio, (tuple, list)):
            for chanel in gpio:
                self.register_gpio(chanel)
        else:
            self.IO_RES.append(gpio)
            self.__io_res.append(gpio)

    def release_gpio(self, gpio):
        if isinstance(gpio, (tuple, list)):
            for channel in list(gpio):
                self.release_gpio(channel)
        else:
            if gpio in self.__io_res:
                self.IO_RES.remove(gpio)
                self.__io_res.remove(gpio)

    async def setmode(self, data):
        data = GPIOMode(**data)
        GPIO.setmode(data.mode)

    async def setup(self, data):
        data = GPIOSetup(**data)

        # Make sure, channel is not be occupied
        self.check_gpio(data.channel)

        # Setup channel as input/output
        if data.direction == GPIOSetup.IN:
            GPIO.setup(data.channel, data.direction, data.pull_up_down)
        else:
            GPIO.setup(data.channel, data.direction, data.pull_up_down, data.initial)

        # Success setup, register gpio
        self.register_gpio(data.channel)

    async def cleanup(self, data):
        data = GPIOCleanup(**data)
        GPIO.cleanup(data.channel)
        self.release_gpio(data.channel)

    async def output(self, data):
        data = GPIOCtrl(**data)
        GPIO.output(data.channel, data.value)

    async def input(self, data):
        data = GPIOChannel(**data)
        return GPIO.input(data.channel)

    async def pwm_init(self, data):
        pwm = GPIOSoftPWM(**data)
        if not isinstance(pwm.channel, int):
            raise RuntimeError("Pwm channel type error")

        # Get pwm instance uuid
        pwm_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "{0:d},{1:d},{2:d}".format(pwm.mode, pwm.channel, pwm.frequency)))

        # Create a pwm instance using uuid as key
        GPIO.setmode(pwm.mode)
        self.check_gpio(pwm.channel)
        GPIO.setup(pwm.channel, GPIO.OUT)
        self.__pwm_list[pwm_uuid] = GPIO.PWM(pwm.channel, pwm.frequency)
        self.register_gpio(pwm.channel)

    async def pwm_ctrl(self, data):
        ctrl = GPIOSoftPWMCtrl(**data)

        # Get pwm instance
        pwm = self.__pwm_list.get(ctrl.uuid)
        if not isinstance(pwm, GPIO.PWM):
            raise ValueError("Do not found pwm:{}".format(ctrl.uuid))

        # Start or stop pwm, duty == 0 stop pwm
        pwm.start(ctrl.duty) if ctrl.duty else pwm.stop()
