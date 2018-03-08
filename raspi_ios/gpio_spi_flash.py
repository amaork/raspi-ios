# -*- coding: utf-8 -*-
import hashlib
import RPi.GPIO as GPIO
from .core import RaspiIOHandle
from raspi_io.gpio_spi_flash import GPIOSPIFlashDevice
from raspi_io.spi_flash import SPIFlashInstruction, SPIFlashProtection
from raspi_io.core import get_binary_data_header, DATA_TRANSFER_BLOCK_SIZE, RaspiBinaryDataHeader
__all__ = ['RaspiGPIOSPIFlashHandle']


class RaspiGPIOSPIFlashHandle(RaspiIOHandle):
    SRP0_BIT = 7
    SRP1_BIT = 0
    BLOCK_PROTECTION_BITS_MASK = 0x1c

    FRAME_MASK = 0xff
    SHIFT_MASK = 0x80
    BITS_PER_FRAME = 8
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (IOError, ValueError, RuntimeError, IOError, IndexError, AttributeError)

    def __init__(self):
        super(RaspiGPIOSPIFlashHandle, self).__init__()
        self.__di = 0
        self.__do = 0
        self.__cs = 0
        self.__clk = 0
        self.__flash_chip_size = 0
        self.__flash_page_size = 0
        self.__flash_instruction = SPIFlashInstruction()

    def __del__(self):
        GPIO.cleanup()

    @staticmethod
    def get_nodes():
        return range(2)

    def xfer(self, data, size=0):
        read_bytes = list()
        GPIO.output(self.__cs, 1)
        GPIO.output([self.__clk, self.__do, self.__cs], 0)

        # Write data to spi
        for byte in data:
            byte &= self.FRAME_MASK
            for i in range(self.BITS_PER_FRAME):
                GPIO.output(self.__clk, 0)
                GPIO.output(self.__do, 1 if byte & self.SHIFT_MASK else 0)
                GPIO.output(self.__clk, 1)
                byte = (byte << 1) & self.FRAME_MASK

        # Read data back
        for n in range(size):
            byte = 0x0
            for i in range(self.BITS_PER_FRAME):
                GPIO.output(self.__clk, 0)
                bit = GPIO.input(self.__di) & 1
                byte |= (bit << (self.BITS_PER_FRAME - 1 - i))
                GPIO.output(self.__clk, 1)

            read_bytes.append(byte)

        return read_bytes

    def page2addr(self, page):
        address = page * self.__flash_page_size
        return [(address >> 16) & 0xff, (address >> 8) & 0xff, address & 0xff]

    def get_sr(self, index=1):
        instruction = self.__flash_instruction.read_sr1 if index == 1 else self.__flash_instruction.read_sr2
        return self.xfer([instruction], 1)[0]

    def set_sr(self, sr1, sr2):
        self.enable_write()
        self.xfer([self.__flash_instruction.write_sr, sr1, sr2])

    def busy_wait(self):
        while self.get_sr(1) & 0x1:
            pass

    def enable_write(self):
        self.xfer([self.__flash_instruction.write_enable])

    def read_page(self, page):
        address = self.page2addr(page)
        return bytearray(self.xfer([self.__flash_instruction.page_read] + address, self.__flash_page_size))

    def write_page(self, page, data):
        address = self.page2addr(page)
        # First enable write
        self.enable_write()

        # Send write page data
        self.xfer([self.__flash_instruction.page_write] + address + data)

        # Wait write done
        self.busy_wait()

    async def open(self, ws, data):
        flash = GPIOSPIFlashDevice(**data)

        # Get gpio pin settings
        self.__cs = flash.cs
        self.__do = flash.mosi
        self.__di = flash.miso
        self.__clk = flash.clk
        self.__flash_chip_size = flash.chip_size
        self.__flash_page_size = flash.page_size
        self.__flash_instruction = SPIFlashInstruction(**flash.instruction)

        # First init gpio for spi bus
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.__di, GPIO.IN)
        GPIO.setup([self.__cs, self.__do, self.__clk], GPIO.OUT, initial=False)
        return True

    async def close(self, ws, data):
        GPIO.cleanup([self.__cs, self.__do, self.__di, self.__clk])

    async def probe(self, ws, data):
        data = self.xfer([self.__flash_instruction.read_id], 3)
        return data[0], data[1] << 8 | data[2]

    async def status(self, ws, data):
        return self.get_sr(2) << 8 | self.get_sr(1)

    async def erase(self, ws, data):
        # First clear block protection bit
        sr1 = self.get_sr(1)
        sr2 = self.get_sr(2)
        sr1 &= ~self.BLOCK_PROTECTION_BITS_MASK
        self.set_sr(sr1, sr2)

        # Second enable write and erase chip
        self.enable_write()
        self.xfer([self.__flash_instruction.chip_erase])

        # Final wait chip erase done
        self.busy_wait()
        return True

    async def read_chip(self, ws, data):
        # First read chip data to memory
        chip_data = bytes()
        for page in range(int(self.__flash_chip_size / self.__flash_page_size)):
            chip_data += self.read_page(page)

        # Second generate binary data header
        header = get_binary_data_header(chip_data)
        await ws.send(header.dumps())

        # Finally send chip data
        for i in range(header.slices):
            await ws.send(chip_data[i * DATA_TRANSFER_BLOCK_SIZE: (i + 1) * DATA_TRANSFER_BLOCK_SIZE])

        return True

    async def write_chip(self, ws, data):
        chip_data = bytes()
        header = RaspiBinaryDataHeader(**data)

        # First receive chip binary data
        for i in range(header.slices):
            temp = await ws.recv()
            chip_data += temp

        # Second check data size and md5 checksum
        if len(chip_data) != header.size or len(chip_data) != self.__flash_chip_size:
            raise ValueError("data size do not matched")

        if hashlib.md5(chip_data).hexdigest() != header.md5:
            raise ValueError("data md5 checksum do not matched")

        # Convert data to list
        chip_data = list(chip_data)

        # Write data to page
        for page in range(int(self.__flash_chip_size / self.__flash_page_size)):
            start = page * self.__flash_page_size
            self.write_page(page, chip_data[start: start + self.__flash_page_size])

        return True

    async def hardware_write_protection(self, ws, data):
        protection = SPIFlashProtection(**data)
        sr1 = self.get_sr(1)
        sr2 = self.get_sr(2)

        # Enable SRP1, SRP0 = (0, 1)
        if protection.enable:
            sr1 |= (1 << self.SRP0_BIT)
            sr2 &= ~(1 << self.SRP1_BIT)
        # Disable SRP1, SRP0 = (0, 0)
        else:
            sr1 &= ~(1 << self.SRP0_BIT)
            sr2 &= ~(1 << self.SRP1_BIT)

        # Write to status register
        self.set_sr(sr1, sr2)
        return True
