# -*- coding: utf-8 -*-
import collections
from .core import RaspiIOHandle
from .server import register_handle
from raspi_io.wireless import JoinNetwork, LeaveNetwork, GetNetworks
__all__ = ['WPASupplicantConfParser', 'WPASupplicantConfParserError', 'RaspiWirelessHandle']


class WPASupplicantConfParserError(Exception):
    pass


class WPASupplicantConfParser:
    def __init__(self, content):
        self._raw_content = content
        self._headers = list()
        self._networks = collections.OrderedDict()

        network_begin = False
        current = collections.OrderedDict()

        for line in self._raw_content.split("\n"):
            if not line:
                continue

            if line.startswith('network'):
                network_begin = True
                current = collections.OrderedDict()
                continue

            if not network_begin:
                self._headers.append(line)
                continue

            if network_begin and '}' in line:
                network_begin = False
                self._networks[current["ssid"]] = current
                continue

            if network_begin and "=" in line:
                k, v = line.strip().split("=")
                current[k] = v

    @property
    def header(self):
        return self._headers

    @property
    def network_list(self):
        return [x[1: -1] for x in self._networks.keys()]

    def dumps(self):
        header = "\n".join(self._headers)
        networks = "\n\n".join(["\n".join(["network={"] + ['\t{}={}'.format(k, v) for k, v in n.items()] + ["}"])
                                for n in self._networks.values()])
        return header + "\n\n" + networks

    def dump(self, fp):
        fp.write(self.dumps())

    def get_network(self, ssid):
        ssid = '"{}"'.format(ssid)
        return dict(self._networks.get(ssid)) if ssid in self._networks else None

    def add_network(self, **kwargs):
        if 'ssid' not in kwargs:
            raise WPASupplicantConfParserError("'ssid' is required")

        if not isinstance(kwargs.get('ssid'), str):
            raise WPASupplicantConfParserError("'ssid' must be a str")

        ssid = kwargs.get("ssid")
        if ssid in self.network_list:
            raise WPASupplicantConfParserError("'ssid' is existed")

        string_type = ('ssid', 'psk', 'id_str')
        values = ['"{}"'.format(v) if k in string_type else v for k, v in kwargs.items()]
        self._networks['"{}"'.format(ssid)] = collections.OrderedDict(dict(zip(kwargs.keys(), values)))
        return self.get_network(ssid)

    def delete_network(self, ssid):
        if ssid not in self.network_list:
            return

        self._networks.pop('"{}"'.format(ssid))


@register_handle
class RaspiWirelessHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    CATCH_EXCEPTIONS = (WPASupplicantConfParserError, OSError)
    WPA_CONFIG_PATH = '/etc/wpa_supplicant/wpa_supplicant.conf'

    def __init__(self):
        super(RaspiWirelessHandle, self).__init__()
        with open(self.WPA_CONFIG_PATH) as fp:
            content = fp.read()
        self.parser = WPASupplicantConfParser(content)

    @staticmethod
    def get_nodes():
        return [RaspiWirelessHandle.PATH]

    def get_wap_config_fp(self):
        return open(self.WPA_CONFIG_PATH, 'w')

    async def get_networks(self, ws, data):
        GetNetworks(**data)
        return self.parser.network_list

    async def join_network(self, ws, data):
        join = JoinNetwork(**data)

        keys = [k for k, v in join.dict.items() if v and k != 'handle']
        keys = sorted(keys, key=lambda x: x != 'ssid')
        values = [join.dict.get(k) for k in keys]

        self.parser.add_network(**dict(zip(keys, values)))
        self.parser.dump(self.get_wap_config_fp())
        return True

    async def leave_network(self, ws, data):
        leave = LeaveNetwork(**data)
        if leave.ssid not in self.parser.network_list:
            raise RuntimeError("Network: {!r} is not exist".format(leave.ssid))

        self.parser.delete_network(leave.ssid)
        self.parser.dump(self.get_wap_config_fp())
        return True
