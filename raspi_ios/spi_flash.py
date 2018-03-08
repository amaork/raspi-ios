# -*- coding: utf-8 -*-
import glob
import spidev
import hashlib
from .core import RaspiIOHandle
from raspi_io.spi_flash import SPIFlashInstruction, SPIFlashDevice, SPIFlashProtection
from raspi_io.core import get_binary_data_header, DATA_TRANSFER_BLOCK_SIZE, RaspiBinaryDataHeader
__all__ = ['RaspiSPIFlashHandle']


class RaspiSPIFlashHandle(RaspiIOHandle):
    SRP0_BIT = 7
    SRP1_BIT = 0
    BLOCK_PROTECTION_BITS_MASK = 0x1c
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (IOError, ValueError, RuntimeError, IOError, IndexError, AttributeError)

    def __init__(self):
        super(RaspiSPIFlashHandle, self).__init__()
        self.__spi = spidev.SpiDev()
        self.__flash_chip_size = 0
        self.__flash_page_size = 0
        self.__flash_instruction = SPIFlashInstruction()

    def __del__(self):
        self.__spi.close()

    @staticmethod
    def get_nodes():
        return glob.glob("/dev/spidev*")

    def get_sr(self, index=1):
        instruction = self.__flash_instruction.read_sr1 if index == 1 else self.__flash_instruction.read_sr2
        return self.__spi.xfer([instruction, 0])[1]

    def set_sr(self, sr1, sr2):
        self.enable_write()
        self.__spi.xfer([self.__flash_instruction.write_sr, sr1, sr2])

    def busy_wait(self):
        while self.get_sr(1) & 0x1:
            pass

    def enable_write(self):
        self.__spi.xfer([self.__flash_instruction.write_enable])

    def read_page(self, page):
        address = page * self.__flash_page_size
        # Msb first
        cmd = [self.__flash_instruction.page_read, (address >> 16) & 0xff, (address >> 8) & 0xff, address & 0xff]
        return bytearray(self.__spi.xfer(cmd + [0] * self.__flash_page_size)[4:])

    def write_page(self, page, data):
        address = page * self.__flash_page_size
        cmd = [self.__flash_instruction.page_write, (address >> 16) & 0xff, (address >> 8) & 0xff, address & 0xff]
        # First enable write
        self.enable_write()

        # Second write page data
        self.__spi.xfer(cmd + data)

        # Wait done
        self.busy_wait()

    async def open(self, ws, data):
        flash = SPIFlashDevice(**data)
        # Get spi bus and dev from device name
        node = flash.device.split("spidev")[-1]
        bus = int(node.split(".")[0])
        dev = int(node.split(".")[1])

        # Open spi device
        self.__spi.open(bus, dev)
        self.__spi.max_speed_hz = flash.speed * 1000
        self.__spi.mode = ((flash.cpol & 1) << 1) | (flash.cpha & 1)

        # Update flash instruction and general info
        self.__flash_chip_size = flash.chip_size
        self.__flash_page_size = flash.page_size
        self.__flash_instruction = SPIFlashInstruction(**flash.instruction)
        return True

    async def close(self, ws, data):
        self.__spi.close()
        return True

    async def probe(self, ws, data):
        data = self.__spi.xfer([self.__flash_instruction.read_id, 0, 0, 0])
        return data[1], data[2] << 8 | data[3]

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
        self.__spi.xfer([self.__flash_instruction.chip_erase])

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
