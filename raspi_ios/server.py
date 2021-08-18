# -*- coding: utf-8 -*-
import uuid
import socket
import asyncio
import websocket
import websockets
import multiprocessing
import concurrent.futures
from urllib.parse import urlparse
from raspi_io.core import DEFAULT_PORT, RaspiAckMsg

from .core import RaspiIOHandle
__all__ = ['RaspiIOServer', 'register_handle', 'get_registered_handles']

__REGISTERED_HANDLES = set()


def register_handle(cls):
    if issubclass(cls, RaspiIOHandle):
        __REGISTERED_HANDLES.add(cls)
    return cls


def get_registered_handles():
    return set(__REGISTERED_HANDLES)


class RaspiIOServer(object):
    def __init__(self, address="0.0.0.0", port=DEFAULT_PORT):
        self.__port = port
        self.__address = address
        self.__max_workers = 0
        self.__route = multiprocessing.Manager().dict()
        self.__free_port = multiprocessing.Manager().list()
        self.__worker_port = multiprocessing.Manager().dict()

    @staticmethod
    def get_free_port():
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(('', 0))
        _, port = tcp.getsockname()
        tcp.close()
        return port

    @staticmethod
    def get_url_uuid(url):
        try:
            return str(uuid.uuid5(uuid.NAMESPACE_OID, "{}:{}".format(url.path, url.query)))
        except AttributeError:
            return ""

    def require_port(self, url):
        worker_uuid = self.get_url_uuid(url)

        try:
            # Already exist, increase port reference
            worker_port, num = self.__worker_port.get(worker_uuid)
            self.__worker_port[worker_uuid] = (worker_port, num + 1)
        except (TypeError, ValueError):
            # First time require, get a free port
            worker_port = self.__free_port.pop()
            self.__worker_port[worker_uuid] = (worker_port, 1)

        return worker_port

    def release_port(self, url):
        worker_uuid = self.get_url_uuid(url)

        try:
            worker_port, num = self.__worker_port.get(worker_uuid)
            num -= 1
            if num <= 0:
                # Client all disconnected, release this port
                self.__worker_port.pop(worker_uuid)
                self.__free_port.append(worker_port)
            else:
                # Decrease port reference counter
                self.__worker_port[worker_uuid] = (worker_port, num)
        except (TypeError, ValueError):
            pass

    def request_release_port(self, url):
        try:
            # Connect to route server, with params release, to release port
            websocket.create_connection("ws://{}:{}{};release?{}".format(
                self.__address, self.__port, url.path, url.query))
        except AttributeError:
            pass

    def run_forever(self):
        self.__free_port = [self.get_free_port() for _ in range(self.__max_workers)]
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.__max_workers + 1) as executor:
            # First submit route server to process pool
            executor.submit(self.route, self.__address, self.__port)
            for port in self.__free_port:
                executor.submit(self.handle, self.__address, port)

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

        # Calculate how many workers to be need
        self.__max_workers += len(component.get_nodes()) * 2
        print("Success register:{}".format(path))
        return True

    def handle(self, address, port):
        """Process client request

        :param address: listen address
        :param port: listen port
        :return:
        """
        async def serve(ws, path):
            url = urlparse(path)

            try:

                # According path get handle
                io_handle = self.__route.get(url.path[1:])
                if not issubclass(io_handle, RaspiIOHandle):
                    raise AttributeError

                # Create a RaspiIOHandle instance process require
                await io_handle.create_instance().process(ws, path)

            except (AttributeError, TypeError) as e:
                error = RaspiAckMsg(ack=False, data="Error: {}({!r})".format(e, path))
                await ws.send(error.dumps())
            except websockets.ConnectionClosed:
                pass
            finally:
                # Inform route process release port and process
                self.request_release_port(url)

        handle = websockets.serve(serve, address, port)
        asyncio.get_event_loop().run_until_complete(handle)
        asyncio.get_event_loop().run_forever()

    def route(self, address, port):
        """Assign unused port to client and recycling client release port

        :param address: listen address
        :param port: listen address
        :return:
        """
        async def serve(ws, path):
            try:

                url = urlparse(path)

                # Handle process require release port
                if url.params == "release":
                    self.release_port(url)
                # Client require get a dynamic port
                else:
                    worker_port = self.require_port(url)
                    await ws.send(RaspiAckMsg(ack=True, data=worker_port).dumps())

                # print(self.__worker_port)

            except (AttributeError, TypeError) as err:
                error = RaspiAckMsg(ack=False, data="Error: {!r}".format(err))
                await ws.send(error.dumps())
            except websockets.ConnectionClosed:
                pass

        handle = websockets.serve(serve, address, port)
        asyncio.get_event_loop().run_until_complete(handle)
        asyncio.get_event_loop().run_forever()
