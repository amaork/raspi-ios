# -*- coding: utf-8 -*-
import json
import websockets
from raspi_io.core import RaspiAckMsg
__all__ = ['RaspiIOHandle']


class RaspiIOHandle(object):
    PATH = ""

    async def handle(self, ws, path):
        nak = ""
        ack = ""

        while True:
            try:

                data = await ws.recv()
                request = json.loads(data)
                handle = self.__class__.__dict__.get(request.get('handle'))
                if callable(handle):
                    ack = await handle(self, data=data)
                else:
                    nak = "{0:s} unknown request:{1:s}".format(path, request)

            except (TypeError, AttributeError, json.JSONDecodeError) as err:
                nak = 'Parse request error:{}!'.format(err)
            except RuntimeError as err:
                nak = 'Process request error:{}'.format(err)
            except websockets.ConnectionClosed:
                print("Websocket{} is closed".format(ws.remote_address))
                break
            finally:
                if ws.open:
                    replay = RaspiAckMsg(ack=True, data=ack or "") if not nak else RaspiAckMsg(ack=False, data=nak)
                    await ws.send(replay.dumps())
