# -*- coding: utf-8 -*-
import os
import hashlib
from pylibmmal import MmalGraph, LCD, HDMI
from .core import RaspiIOHandle
from raspi_io.graph import GraphInit, GraphClose, GraphHeader, GraphProperty
__all__ = ['RaspiMmalGraphHandle']


class RaspiMmalGraphHandle(RaspiIOHandle):
    __graph = None
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (TypeError, ValueError, RuntimeError)

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
        graph_data = bytes()
        header = GraphHeader(**data)

        # Receive graph binary data
        for i in range(header.slices):
            temp = await ws.recv()
            graph_data += temp

        # Check graph size
        if len(graph_data) != header.size:
            raise ValueError("data size do not matched")

        # Check graph md5
        if hashlib.md5(graph_data).hexdigest() != header.md5:
            raise ValueError("data md5 checksum do not matched")

        # Save graph to a temporary file
        file_path = os.path.join("/tmp", "{}.{}".format(header.md5, header.format))
        with open(file_path, "wb") as fp:
            fp.write(graph_data)

        # Display graph via mmal
        self.__graph.open(file_path)
        # Remove graph
        os.remove(file_path)
        return True

    async def close(self, ws, data):
        req = GraphClose(**data)
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
