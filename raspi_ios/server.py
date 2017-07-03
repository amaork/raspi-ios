# -*- coding: utf-8 -*-
import asyncio
import websockets
from .core import RaspiIOHandle
from urllib.parse import urlparse
__all__ = ['RaspiIOServer']


class RaspiIOServer(object):
    def __init__(self):
        self.__route = dict()

    def run(self, host, port):
        handle = websockets.serve(self.router, host, port)
        asyncio.get_event_loop().run_until_complete(handle)
        asyncio.get_event_loop().run_forever()

    def register(self, component):
        """Register a component, to RaspiIOServer

        :param component: RaspiIOHandle type object
        :return:
        """
        if not issubclass(component, RaspiIOHandle):
            print("Component TypeError:{0:s}".format(type(component)))
            return False

        if component.PATH in self.__route:
            return True

        self.__route[component.PATH] = component
        print("Success register:{}".format(component.PATH))
        return True

    async def router(self, ws, path):
        url = urlparse(path)
        handle = self.__route.get(url.path[1:])
        if issubclass(handle, RaspiIOHandle):
            await handle().process(ws, path)
        else:
            await ws.close()
