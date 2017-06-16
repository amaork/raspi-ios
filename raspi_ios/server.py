# -*- coding: utf-8 -*-
import asyncio
import websockets
from .core import RaspiIOHandle
from raspi_io.core import WS_PORT
from urllib.parse import urlparse
__all__ = ['RaspiIOServer']


class RaspiIOServer(object):
    def __init__(self):
        self.__route = dict()

    def run(self, host):
        handle = websockets.serve(self.router, host, WS_PORT)
        asyncio.get_event_loop().run_until_complete(handle)
        asyncio.get_event_loop().run_forever()

    def register(self, handle):
        if not issubclass(handle, RaspiIOHandle):
            print("RaspiIOHandle TypeError:{0:s}".format(type(handle)))
            return False

        if handle.PATH in self.__route:
            return True

        self.__route[handle.PATH] = handle()
        return True

    async def router(self, ws, path):
        url = urlparse(path)
        handle = self.__route.get(url.path[1:])
        if isinstance(handle, RaspiIOHandle):
            await handle.handle(ws, path)
        else:
            await ws.close()
