# -*- coding: utf-8 -*-
import uuid
import RPi.GPIO as GPIO
from .core import RaspiIOHandle
from .server import register_handle
from raspi_io.gpio import GPIOMode, GPIOSetup, GPIOCleanup, GPIOCtrl, GPIOChannel, \
    GPIOSoftPWM, GPIOSoftPWMCtrl, GPIOSoftSPI, GPIOSoftSPIXfer, GPIOSoftSPIRead, GPIOSoftSPIWrite
__all__ = ['RaspiGPIOHandle']


@register_handle
class RaspiGPIOHandle(RaspiIOHandle):
    IO_RES = set()
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (ValueError, TypeError, IOError, RuntimeError)

    def __init__(self):
        super(RaspiIOHandle, self).__init__()
        GPIO.setwarnings(False)
        self.__io_res = set()
        self.__pwm_list = dict()
        self.__spi_list = dict()

    def __del__(self):
        [pwm.stop() for pwm in self.__pwm_list.values()]
        GPIO.cleanup(list(self.__io_res))
        self.release_gpio(self.__io_res)

    @staticmethod
    def get_nodes():
        return [RaspiGPIOHandle.PATH]

    def check_gpio(self, gpio):
        """Check if gpio is occupied

        :param gpio: gpio number or gpio list
        :return: occupied raise IOError
        """
        if isinstance(gpio, (tuple, list)):
            for channel in gpio:
                self.check_gpio(channel)
        else:
            # TODO: gpio same directions is ok
            if gpio in self.IO_RES and gpio not in self.__io_res:
                raise IOError("Channel:{} is occupied".format(gpio))

    def register_gpio(self, gpio):
        if isinstance(gpio, (tuple, list)):
            for chanel in gpio:
                self.register_gpio(chanel)
        else:
            self.IO_RES.add(gpio)
            self.__io_res.add(gpio)

    def release_gpio(self, gpio):
        if isinstance(gpio, (tuple, list, set)):
            for channel in list(gpio):
                self.release_gpio(channel)
        else:
            if gpio in self.__io_res:
                self.IO_RES.remove(gpio)
                self.__io_res.remove(gpio)

    async def setmode(self, ws, data):
        data = GPIOMode(**data)
        GPIO.setmode(data.mode)

    async def setup(self, ws, data):
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

    async def cleanup(self, ws, data):
        data = GPIOCleanup(**data)
        GPIO.cleanup(data.channel)
        self.release_gpio(data.channel)

    async def output(self, ws, data):
        data = GPIOCtrl(**data)
        GPIO.output(data.channel, data.value)

    async def input(self, ws, data):
        data = GPIOChannel(**data)
        return GPIO.input(data.channel)

    async def pwm_init(self, ws, data):
        pwm = GPIOSoftPWM(**data)
        if not isinstance(pwm.channel, int):
            raise TypeError("Pwm channel type error")

        # Get pwm instance uuid
        pwm_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, "{0:d},{1:d},{2:d}".format(pwm.mode, pwm.channel, pwm.frequency)))

        # Create a pwm instance using uuid as key
        GPIO.setmode(pwm.mode)
        self.check_gpio(pwm.channel)
        GPIO.setup(pwm.channel, GPIO.OUT)
        self.__pwm_list[pwm_uuid] = GPIO.PWM(pwm.channel, pwm.frequency)
        self.register_gpio(pwm.channel)

    async def pwm_ctrl(self, ws, data):
        ctrl = GPIOSoftPWMCtrl(**data)

        # Get pwm instance
        pwm = self.__pwm_list.get(ctrl.uuid)
        if not isinstance(pwm, GPIO.PWM):
            raise ValueError("Do not found pwm:{}".format(ctrl.uuid))

        # Start or stop pwm, duty == 0 stop pwm
        pwm.start(ctrl.duty) if ctrl.duty else pwm.stop()

    async def spi_init(self, ws, data):
        spi = GPIOSoftSPI(**data)

        # Get pwm instance uuid
        spi_uuid = spi.generate_uuid()

        # Init spi gpio
        GPIO.setmode(spi.mode)
        # TODO: Check gpio
        # self.check_gpio([spi.cs, spi.clk, spi.mosi, spi.miso])
        GPIO.setup(spi.miso, GPIO.IN)
        GPIO.setup([spi.cs, spi.clk, spi.mosi], GPIO.OUT)

        # Register spi to spi device list
        self.__spi_list[spi_uuid] = spi

    async def spi_xfer(self, ws, data):
        xfer = GPIOSoftSPIXfer(**data)

        # Get spi instance
        spi = self.__spi_list.get(xfer.uuid)
        if not isinstance(spi, GPIOSoftSPI):
            raise ValueError("Do not found spi:{}".format(xfer.uuid))

        read_bytes = list()
        shift_mask = (1 << (spi.bits_per_word - 1))
        word_mask = 0xffffffffffffffff >> (64 - spi.bits_per_word)

        # SPI bus init
        GPIO.output(spi.cs, 1)
        GPIO.output([spi.cs, spi.clk, spi.mosi], 0)

        # Write data to spi
        for word in xfer.data:
            word &= word_mask
            for i in range(spi.bits_per_word):
                GPIO.output(spi.clk, 0)
                GPIO.output(spi.mosi, 1 if word & shift_mask else 0)
                GPIO.output(spi.clk, 1)
                word = (word << 1) & word_mask

        # Read data back
        for n in range(xfer.size):
            word = 0x0
            for i in range(spi.bits_per_word):
                GPIO.output(spi.clk, 0)
                bit = GPIO.input(spi.miso) & 1
                word |= (bit << (spi.bits_per_word - 1 - i))
                GPIO.output(spi.clk, 1)

            read_bytes.append(word)

        return read_bytes

    async def spi_read(self, ws, data):
        read = GPIOSoftSPIRead(**data)

        # Get spi instance
        spi = self.__spi_list.get(read.uuid)
        if not isinstance(spi, GPIOSoftSPI):
            raise ValueError("Do not found spi:{}".format(read.uuid))

        # SPI bus init
        read_bytes = list()
        GPIO.output(spi.cs, 1)
        GPIO.output([spi.cs, spi.clk, spi.mosi], 0)

        # Read data back
        for n in range(read.size):
            word = 0x0
            for i in range(spi.bits_per_word):
                GPIO.output(spi.clk, 0)
                bit = GPIO.input(spi.miso) & 1
                word |= (bit << (spi.bits_per_word - 1 - i))
                GPIO.output(spi.clk, 1)

            read_bytes.append(word)

        return read_bytes

    async def spi_write(self, ws, data):
        write = GPIOSoftSPIWrite(**data)

        # Get spi instance
        spi = self.__spi_list.get(write.uuid)
        if not isinstance(spi, GPIOSoftSPI):
            raise ValueError("Do not found spi:{}".format(write.uuid))

        # TODO: Move to GPIOSoftSPI class
        shift_mask = (1 << (spi.bits_per_word - 1))
        word_mask = 0xffffffffffffffff >> (64 - spi.bits_per_word)

        # SPI bus init
        GPIO.output(spi.cs, 1)
        GPIO.output([spi.cs, spi.clk, spi.mosi], 0)

        # Write data to spi
        for word in write.data:
            word &= word_mask
            for i in range(spi.bits_per_word):
                GPIO.output(spi.clk, 0)
                GPIO.output(spi.mosi, 1 if word & shift_mask else 0)

                # LSB Strobe
                if i == spi.bits_per_word - 1:
                    GPIO.output(spi.cs, 1)

                GPIO.output(spi.clk, 1)
                word = (word << 1) & word_mask
