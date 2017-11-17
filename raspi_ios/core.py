# -*- coding: utf-8 -*-
import json
import base64
import websockets
from raspi_io.core import RaspiAckMsg, RaspiMsgDecodeError
__all__ = ['RaspiIOHandle']


class RaspiIOHandle(object):
    PATH = ""
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
                handle = self.__class__.__dict__.get(request.get('handle'))

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
