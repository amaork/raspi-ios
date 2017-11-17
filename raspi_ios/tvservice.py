# -*- coding: utf-8 -*-
from pylibmmal import TVService
from .core import RaspiIOHandle
from raspi_io.tvservice import TVPower, TVStatus, TVGetModes, TVSetExplicit
__all__ = ['RaspiTVServiceHandle']


class RaspiTVServiceHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (TypeError, ValueError, RuntimeError)

    def __init__(self):
        super(RaspiTVServiceHandle, self).__init__()
        self.__tv = TVService()

    @staticmethod
    def get_nodes():
        return [RaspiTVServiceHandle.PATH]

    async def power_ctrl(self, ws, data):
        ctrl = TVPower(**data)
        self.__tv.set_preferred() if ctrl.power else self.__tv.power_off()
        return True

    async def get_modes(self, ws, data):
        req = TVGetModes(**data)
        return self.__tv.get_preferred_mode() if req.preferred else self.__tv.get_modes(req.group)

    async def get_status(self, ws, data):
        st = TVStatus(**data)
        return self.__tv.get_status()

    async def set_explicit(self, ws, data):
        req = TVSetExplicit(**data)
        self.__tv.set_preferred() if req.preferred else self.__tv.set_explicit(group=req.group, mode=req.mode)
        return True
