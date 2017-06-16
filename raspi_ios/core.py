# -*- coding: utf-8 -*-
import json
import websockets
__all__ = ['RaspiIOHandle']


class RaspiIOHandle(object):
    PATH = ""

    async def handle(self, ws, path):
        while True:
            try:

                data = await ws.recv()
                request = json.loads(data)
                handle = self.__class__.__dict__.get(request.get('handle'))
                if callable(handle):
                    await handle(self, ws, data=data)
                else:
                    print("{0:s} unknown request:{1:s}".format(path, request))

            except (TypeError, AttributeError, json.JSONDecodeError) as err:
                print('{0:s} parse request error:{1:s}!'.format(path, err))
                break
            except websockets.ConnectionClosed as err:
                print("Websocket error:{}".format(err))
                break
