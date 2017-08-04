# -*- coding: utf-8 -*-
import socket
from .core import RaspiIOHandle
from raspi_io.core import DEFAULT_PORT
from raspi_io.setting import RaspiWsPort
__all__ = ['RaspiSettingHandle']


class RaspiSettingHandle(RaspiIOHandle):
    __setting__ = dict()
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (TypeError, ValueError, RuntimeError, AttributeError)

    def __init__(self):
        super(RaspiSettingHandle, self).__init__()

    async def get_port(self, data):
        req = RaspiWsPort(**data)
        if req.path in self.__setting__:
            return self.__setting__[req.path].get(req.node) or DEFAULT_PORT

        return DEFAULT_PORT

    @staticmethod
    def register(path, node):
        """Register path and node

        :param path: RaspiIOHandle path
        :param node: RaspiIOHandle node
        :return:node using port
        """
        port = RaspiSettingHandle.get_free_port()
        if path in RaspiSettingHandle.__setting__:
            RaspiSettingHandle.__setting__[path].update({node: port})
        else:
            RaspiSettingHandle.__setting__[path] = {node: port}

        return port

    @staticmethod
    def get_free_port():
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(('', 0))
        _, port = tcp.getsockname()
        tcp.close()
        return port
