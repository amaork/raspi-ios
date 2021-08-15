# -*- coding: utf-8 -*-
import os
import json
import base64
import hashlib
import websockets
from collections import ChainMap
from raspi_io.core import RaspiAckMsg, RaspiMsgDecodeError, RaspiBinaryDataHeader
__all__ = ['RaspiIOHandle']


class RaspiIOHandle(object):
    PATH = ""
    TEMP_DIR = '/tmp'
    CATCH_EXCEPTIONS = ()

    @staticmethod
    def get_nodes():
        """Get support nodes

        :return: should return a node list
        """
        pass

    @staticmethod
    def encode_data(data):
        """Encode data to base64

        :param data: data will encode
        :return: data after encode
        """
        return str(base64.b64encode(bytes(data)))

    @staticmethod
    def decode_data(data):
        """Decode data from base64

        :param data: data receive from network
        :return: data after decode
        """
        # Convert b64 string to bytes
        # Python2 base64 after encode is str, python3 after encode is bytes()
        return base64.b64decode(data[2:-1]) if data.startswith("b'") and data.endswith("'") else base64.b64decode(data)

    @classmethod
    def create_instance(cls):
        return cls()

    async def process(self, ws, path):
        nak = None
        ack = None
        while True:
            try:

                ack = nak = None

                # Receive request
                data = await ws.recv()
                request = json.loads(data)

                # Get handle from request
                handle = ChainMap(self.__class__.__dict__, self.__class__.__base__.__dict__).get(request.get('handle'))

                # Request process
                if callable(handle):

                    # Catch Runtime error
                    try:
                        ack = await handle(self, ws=ws, data=request)
                    except self.CATCH_EXCEPTIONS as err:
                        nak = 'Process request error:{}'.format(err)
                else:
                    nak = "{0:s} unknown request:{1:s}".format(path, request)

            except (RaspiMsgDecodeError, json.JSONDecodeError) as err:
                nak = 'Parse request error:{}!'.format(err)
            except websockets.ConnectionClosed:
                print("Websocket{} is closed".format(ws.remote_address))
                break
            finally:
                if ws.open:
                    # Generate ack msg
                    if nak is not None:
                        replay = RaspiAckMsg(ack=False, data=nak)
                    else:
                        replay = RaspiAckMsg(ack=True, data=ack if ack is not None else "")

                    await ws.send(replay.dumps())

    async def receive_binary_file(self, ws, data):
        """Common receive binary file handle, receive binary data stream form ws

        :param ws: websocket
        :param data: RaspiBinaryDataHeader include data size, slices, md5 format etc
        :return: success return True, failed raise exception
        """
        header = RaspiBinaryDataHeader(**data)

        try:
            await self.receive_binary_data(ws, header, save_as_file=True)
        except (ValueError, IOError) as e:
            raise RuntimeError('Receive file failed: {}'.format(e))

        return os.path.join("/tmp", "{}.{}".format(header.md5, header.format))

    @staticmethod
    async def receive_binary_data(ws, header, save_as_file=False):
        """Command receive binary data handle

        :param ws: websocket
        :param header: RaspiBinaryDataHeader
        :param save_as_file: if set will save binary data as a file (file name is md5.format save at /tmp)
        :return: binary data(type bytes)
        """
        binary_data = bytes()

        # Receive graph binary data
        for i in range(header.slices):
            temp = await ws.recv()
            binary_data += temp

        # Check graph size
        if len(binary_data) != header.size:
            raise ValueError("data size do not matched")

        # Check graph md5
        if hashlib.md5(binary_data).hexdigest() != header.md5:
            raise ValueError("data md5 checksum do not matched")

        # Save graph to a temporary file
        if save_as_file:
            file_path = os.path.join("/tmp", "{}.{}".format(header.md5, header.format))
            with open(file_path, "wb") as fp:
                fp.write(binary_data)

        return binary_data
