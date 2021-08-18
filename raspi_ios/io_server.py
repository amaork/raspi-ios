# -*- coding: utf-8 -*-
from .server import RaspiIOServer, get_registered_handles


if __name__ == "__main__":
    server = RaspiIOServer()
    for handle in get_registered_handles():
        server.register(handle)

    server.run_forever()
