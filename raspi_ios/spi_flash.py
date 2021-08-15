# -*- coding: utf-8 -*-
import glob
import time
import spidev
import hashlib
from .core import RaspiIOHandle
from raspi_io.spi_flash import SPIFlashInstruction, SPIFlashDevice, SPIFlashWriteStatus
from raspi_io.core import get_binary_data_header, DATA_TRANSFER_BLOCK_SIZE, RaspiBinaryDataHeader
__all__ = ['RaspiSPIFlashHandle']


class RaspiSPIFlashHandle(RaspiIOHandle):
    BP_MASK = 0x3C
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

    def get_sr(self):
        sr1 = self.__spi.xfer([self.__flash_instruction.read_sr1, 0])[1]
        sr2 = self.__spi.xfer([self.__flash_instruction.read_sr2, 0])[1]
        return sr2 << 8 | sr1

    def set_sr(self, sr):
        self.enable_write()
        self.__spi.xfer([self.__flash_instruction.write_sr, sr & 0xff, (sr >> 8) & 0xff])
        time.sleep(0.1)
        self.busy_wait()

    def busy_wait(self):
        while self.get_sr() & 0x1:
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

    async def read_status(self, ws, data):
        return self.get_sr()

    async def write_status(self, ws, data):
        data = SPIFlashWriteStatus(**data)
        self.set_sr(data.status)
        return True

    async def erase(self, ws, data):
        # First clear block protection bit
        status = self.get_sr()
        if status & self.BP_MASK:
            status &= ~self.BP_MASK
            self.set_sr(status)

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
        header = RaspiBinaryDataHeader(**data)
        chip_data = await self.receive_binary_data(ws, header)

        # Convert data to list
        chip_data = list(chip_data)

        # Write data to page
        for page in range(int(self.__flash_chip_size / self.__flash_page_size)):
            start = page * self.__flash_page_size
            self.write_page(page, chip_data[start: start + self.__flash_page_size])

        return True
