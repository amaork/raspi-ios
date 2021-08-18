# -*- coding: utf-8 -*-
import os
from .core import RaspiIOHandle
from .server import register_handle
from pylibmmal import MmalGraph, LCD, HDMI
from raspi_io.graph import GraphInit, GraphClose, GraphProperty
__all__ = ['RaspiMmalGraphHandle']


@register_handle
class RaspiMmalGraphHandle(RaspiIOHandle):
    __graph = None
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (TypeError, ValueError, RuntimeError, OSError)

    def __init__(self):
        super(RaspiMmalGraphHandle, self).__init__()

    def __del__(self):
        try:
            if self.__graph.is_open:
                self.__graph.close()
        except AttributeError:
            pass

    @staticmethod
    def get_nodes():
        return list(map(str, [LCD, HDMI]))

    async def init(self, ws, data):
        req = GraphInit(**data)
        self.__graph = MmalGraph(req.display_num)
        return True

    async def open(self, ws, data):
        # Save graph to a temporary file
        file_path = await self.receive_binary_file(ws, data)

        # Display graph via mmal
        self.__graph.open(file_path)

        # Remove graph
        os.remove(file_path)
        return True

    async def close(self, ws, data):
        GraphClose(**data)
        if self.__graph.is_open:
            self.__graph.close()

    async def get_property(self, ws, data):
        req = GraphProperty(**data)
        if req.property == GraphProperty.IS_OPEN:
            return self.__graph.is_open
        elif req.property == GraphProperty.DISPLAY_NUM:
            return self.__graph.display_num
        else:
            raise ValueError("unknown property")
