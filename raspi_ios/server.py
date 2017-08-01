# -*- coding: utf-8 -*-
import asyncio
import websockets
from multiprocessing import Process
from raspi_io.core import DEFAULT_PORT

from .setting import RaspiSettingHandle
from .core import RaspiIOHandle, RaspiAckMsg
from urllib.parse import urlparse
__all__ = ['RaspiIOServer']


class RaspiIOServer(object):
    def __init__(self, host="0.0.0.0", port=DEFAULT_PORT):
        self.__host = host
        self.__port = port
        self.__route = dict()
        self.__process = list()
        self.__route[RaspiSettingHandle.PATH] = RaspiSettingHandle

    def __run_serve(self, host, port):
        handle = websockets.serve(self.router, host, port)
        asyncio.get_event_loop().run_until_complete(handle)
        asyncio.get_event_loop().run_forever()

    def run_forever(self):
        for process in self.__process:
            process.start()

        self.__run_serve(self.__host, self.__port)

    def register(self, component):
        """Register a component, to RaspiIOServer

        :param component: RaspiIOHandle type object
        :return:
        """
        if not issubclass(component, RaspiIOHandle):
            print("Component TypeError:{0:s}".format(type(component)))
            return False

        path = component.PATH
        if path in self.__route:
            return True

        # Register component route
        self.__route[path] = component

        # Create a process for each node with different port
        for node in component.get_nodes():
            port = RaspiSettingHandle.register(path, node)
            process = Process(target=self.__run_serve, args=(self.__host, port), name="{}:{}".format(path, node))
            self.__process.append(process)

        print("Success register:{}".format(path))
        return True

    async def router(self, ws, path):
        try:

            url = urlparse(path)
            handle = self.__route.get(url.path[1:])

            if handle is None:
                error = RaspiAckMsg(ack=False, data="Error: do not registered {!r}".format(path))
                await ws.send(error.dumps())
                return

            if issubclass(handle, RaspiIOHandle):
                await handle().process(ws, path)
            else:
                await ws.close()
        except websockets.ConnectionClosed:
            pass
