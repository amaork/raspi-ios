# -*- coding: utf-8 -*-
import os
import json
import psutil
import codecs
import pathlib
import hashlib
import tarfile
import datetime
import requests
import ipaddress
import concurrent.futures
from pyquery import PyQuery
from contextlib import closing
import requests_toolbelt.adapters
import xml.etree.ElementTree as XmlElementTree
from typing import List, Callable, Optional, Dict

from .core import RaspiIOHandle
from .server import register_handle
from raspi_io.core import RaspiMsgDecodeError
from raspi_io.app_manager import AppDescription, InstallApp, UninstallApp, \
    AppState, GetAppState, FetchUpdate, OnlineUpdate, LocalUpdate
__all__ = ['RaspiAppManagerHandle', 'GogsSoftwareReleaseDesc', 'RepoRelease']


class HttpRequestException(Exception):
    def __init__(self, code, desc):
        super(HttpRequestException, self).__init__(Exception)
        self.code = code
        self.desc = desc


class HttpRequest(object):
    HTTP_OK = 200
    HTTP_Forbidden = 403
    HTTP_Unauthorized = 401

    TOKEN_NAME = "token"

    def __init__(self, token_name: str = TOKEN_NAME, source_address: str = "", timeout: float = 5.0):
        self._timeout = timeout
        self.__token_name = token_name
        self._section = requests.Session()

        try:
            source_address = str(ipaddress.ip_address(source_address))
            new_source = requests_toolbelt.adapters.source.SourceAddressAdapter(source_address)
            self._section.mount("http://", new_source)
            self._section.mount("https://", new_source)
        except ValueError:
            pass

        self._section.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
        }

    @property
    def timeout(self) -> float:
        return self._timeout

    @property
    def token_name(self) -> str:
        return self.__token_name[:]

    @staticmethod
    def is_response_ok(res: requests.Response) -> bool:
        return res.status_code == HttpRequest.HTTP_OK

    @staticmethod
    def get_token_from_text(text: str, name: str = TOKEN_NAME) -> str:
        doc = PyQuery(text.encode())
        return doc('input[name="{}"]'.format(name)).attr("value").strip()

    def get_token(self, url: str) -> str:
        res = self.section_get(url)
        if not self.is_response_ok(res):
            return ""

        return self.get_token_from_text(res.text, self.__token_name)

    def section_get(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self._section.get(url, **kwargs)

    def section_post(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self._section.post(url, **kwargs)

    def login(self, url: str,
              login_data: dict,
              headers: Optional[dict] = None,
              require_token: bool = False, verify: bool = False) -> requests.Response:
        if require_token:
            login_data[self.token_name] = self.get_token(url)

        res = self.section_post(url, data=login_data, headers=headers, verify=verify)
        res.raise_for_status()
        return res


class GogsRequestException(HttpRequestException):
    pass


class DynamicObjectError(Exception):
    pass


class DynamicObjectEncodeError(DynamicObjectError):
    pass


class DynamicObjectDecodeError(DynamicObjectError):
    pass


class DynamicObject(object):
    _check = dict()
    _properties = set()

    def __init__(self, **kwargs):
        try:
            for key in self._properties:
                if kwargs.get(key) is None:
                    raise KeyError("do not found key:{!r}".format(key))

            self.__dict__.update(**kwargs)

        except (TypeError, KeyError, ValueError) as e:
            raise DynamicObjectDecodeError("Decode {!r} error:{}".format(self.__class__.__name__, e))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.__dict__ == other.__dict__

    def __len__(self):
        return len(self._properties)

    def __repr__(self):
        return self.dumps()

    def __iter__(self):
        for key in sorted(self.__dict__.keys()):
            yield key

    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except KeyError:
            msg = "'{0}' object has no attribute '{1}'"
            raise AttributeError(msg.format(type(self).__name__, name))

    @property
    def dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def properties(cls) -> List[str]:
        return list(cls._properties)

    def xml(self, tag: str) -> XmlElementTree.Element:
        element = XmlElementTree.Element(tag)
        for k, v in self.dict.items():
            element.set("{}".format(k), "{}".format(v))
        return element

    def dumps(self) -> str:
        """Encode data to a dict string

        :return:
        """
        return json.dumps(self.__dict__)

    def update(self, data):
        if not isinstance(data, (dict, DynamicObject)):
            raise DynamicObjectEncodeError('DynamicObject update require {!r} or {!r} not {!r}'.format(
                dict.__name__, DynamicObject.__name__, data.__class__.__name__))

        data = data.dict if isinstance(data, DynamicObject) else data
        for k, v in data.items():
            if k not in self._properties:
                raise DynamicObjectEncodeError("Unknown key: {}".format(k))

            if not isinstance(v, type(self.__dict__[k])):
                raise DynamicObjectEncodeError("New value {!r} type is not matched: new({!r}) old({!r})".format(
                    k, v.__class__.__name__, self.__dict__[k].__class__.__name__))

            if k in self._check and hasattr(self._check.get(k), "__call__") and not self._check.get(k)(v):
                raise DynamicObjectEncodeError("Key {!r} new value {!r} check failed".format(k, v))

            self.__dict__[k] = v


class RepoRelease(DynamicObject):
    _properties = {'name', 'date', 'desc', 'attachment'}

    @property
    def raw_desc(self) -> str:
        return self.desc[1] if len(self.desc) == 2 else ""

    @property
    def html_desc(self) -> str:
        return self.desc[0] if len(self.desc) == 2 else ""

    def attachments(self) -> List[str]:
        return list(self.attachment.keys())

    def get_attachment_url(self, name: str) -> str:
        return self.attachment.get(name, "")


class GogsRequest(HttpRequest):
    TOKEN_NAME = "_csrf"

    def __init__(self, host: str, username: str, password: str, source_address: str = "", timeout: float = 5):
        super(GogsRequest, self).__init__(token_name=self.TOKEN_NAME, source_address=source_address, timeout=timeout)
        self.__host = host
        self.__username = username

        login_url = "{}/user/login".format(host)
        login_data = DynamicObject(user_name=username, password=password)
        try:
            login_response = self.login(login_url, login_data.dict, require_token=True)
            if login_response.url == login_url:
                doc = PyQuery(login_response.text)
                raise GogsRequestException(self.HTTP_Forbidden, doc('p').text().strip())
            self.__token = self.get_token_from_text(login_response.text, self.TOKEN_NAME)
        except requests.RequestException as err:
            raise GogsRequestException(err.response.status_code, err.response.text)

    def get_repo_url(self, repo: str) -> str:
        return "{}/{}".format(self.__host, repo)

    def download(self, name: str, url: str, timeout: int = 60,
                 callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Download file or attachment
        :param name: download file save path
        :param url: download url
        :param timeout: download timeout
        :param callback: callback(name: str) -> None
        :return: success return ture
        """
        try:
            with closing(self.section_get(url, timeout=timeout)) as response:
                with open(name, "wb") as file:
                    file.write(response.content)
        except (OSError, requests.RequestException) as e:
            print("Download {} failed: {}".format(url, e))
            return False

        if hasattr(callback, "__call__"):
            callback(name)

        return True

    def stream_download(self, name: str, url: str, size: int, chunk_size: int = 1024 * 32,
                        timeout: int = 60, callback: Optional[Callable[[float, str], bool]] = None) -> bool:
        """
        Stream download a file from gogs server
        :param name: download path
        :param url: download url
        :param size: download file size in bytes
        :param chunk_size: download chunk size in bytes
        :param timeout: download timeout
        :param callback: download progress callback
        :return: success return true, failed return false
        """
        try:
            if not isinstance(size, int) or not size:
                print("{!r} stream download must specific download file size".format(self.__class__.__name__))
                return False

            download_size = 0
            chunk_size = chunk_size if size > chunk_size else 1024
            chunk_size = chunk_size if size > chunk_size else 1
            with closing(self.section_get(url, timeout=timeout, stream=True)) as response:
                with open(name, "wb") as file:
                    for data in response.iter_content(chunk_size=chunk_size):
                        file.write(data)
                        download_size += len(data)

                        if hasattr(callback, "__call__"):
                            info = "{}K/{}K".format(download_size // 1024, size // 1024)
                            if not callback(round(download_size / size * 100, 2), info):
                                print("Download canceled")
                                return False
        except (OSError, requests.RequestException) as e:
            print("Download {} failed: {}".format(url, e))
            return False

        return True

    def download_package(self, package: dict, path: str,
                         timeout: int = 60, parallel: bool = True,
                         max_workers: int = 4, ignore_error: bool = True,
                         callback: Optional[Callable[[str, float], bool]] = None) -> Dict[str, bool]:
        """
        Download an a pack of file
        :param package: Package to download, package is dict include multi-files name is key url is value
        :param path: Download path, path should be a directory
        :param parallel: Thread pool parallel download parallel download
        :param max_workers: Thread pool max workers
        :param timeout: Download timeout for single file
        :param ignore_error: If set ignore error, when error occurred will ignore error continue download
        :param callback: Callback function, callback(downloaded_file_name: str, download_progress: int) -> bool if
        callback return false mean's canceled, one serial download support this feature
        :return: Success return each file download result, dict key is file name, value is download result
        """
        download_result = dict(zip(package.keys(), [False] * len(package)))
        download_files = list(package.keys())
        download_count = len(download_files)

        def download_callback(name: str) -> bool:
            if not hasattr(callback, "__call__"):
                return True

            # Remove already downloaded file from list
            filename = os.path.basename(name)
            if filename not in download_files:
                return True
            else:
                download_files.remove(filename)

            # Calc download progress
            download_progress = round(100 - len(download_files) / download_count * 100, 2)
            return callback(name, download_progress)

        # Check download path if is not exist create it
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except (OSError, FileExistsError) as err:
            raise GogsRequestException(404, "Download attachment error: {}".format(err))

        if parallel:
            # Thread pool parallel download attachment
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                result = [pool.submit(self.download, **DynamicObject(name=os.path.join(path, name), url=url,
                                                                     timeout=timeout, callback=download_callback).dict)
                          for name, url in package.items()]

            # Get each file download result
            for name, ret in zip(package.keys(), result):
                download_result[name] = ret.result() if ret.result() is not None else False
        else:
            for name, url in package.items():
                ret = self.download(name=os.path.join(path, name), url=url, timeout=timeout)
                download_result[name] = ret

                # Callback and if return false means cancel download
                if not download_callback(os.path.join(path, name)):
                    break

                if ret or ignore_error:
                    continue
                else:
                    break

        return download_result

    def get_repo_releases(self, repo: str) -> List[RepoRelease]:
        releases = list()
        release_url = "{}/releases".format(self.get_repo_url(repo))

        try:
            response = self.section_get(release_url)
            response.raise_for_status()

            doc = PyQuery(response.text)
            for item in doc("#release-list")(".grid").items():
                name = item("h3")("a").text().strip()
                date = item(".time-since").attr("title")
                desc = str(item(".desc")), item(".desc").text()

                attachment = dict()
                for a in item(".download").items():
                    for package in a(".octicon-package").items():
                        package_name = package.next().text()
                        package_href = package.next().attr("href")
                        attachment[package_name] = "{}{}".format(self.__host, package_href)

                releases.append(RepoRelease(name=name, date=date, desc=desc, attachment=attachment))

            return releases
        except requests.RequestException as e:
            print("get_repo_releases exception: {}".format(e))
            return list()

    def upload_repo_avatar(self, repo_path: str, avatar: str, timeout: Optional[float] = None):
        avatar_url = "{}/{}/settings/avatar".format(self.__host, repo_path)
        avatar_from_data = DynamicObject(
            _csrf=(None, self.__token), avatar=(os.path.basename(avatar), open(avatar, "rb"))
        )
        ret = self._section.post(avatar_url, files=avatar_from_data.dict, timeout=timeout or self._timeout)
        ret.raise_for_status()


class GogsSoftwareReleaseDesc(DynamicObject):
    _default_path = "release.json"
    _properties = {'name', 'desc', 'size', 'date', 'md5', 'version', 'url'}

    def check(self):
        return self.name and self.size and self.md5 and self.url

    @classmethod
    def default(cls):
        return GogsSoftwareReleaseDesc(name="", desc="", size=0, date="", md5="", version=0.0, url="")

    @classmethod
    def generate(cls, path: str, version: float):
        """
        Generate #path specified software release desc
        :param path: software path
        :param version: software version
        :return: success return True
        """
        try:
            desc = GogsSoftwareReleaseDesc(
                date=str(datetime.datetime.fromtimestamp(pathlib.Path(path).stat().st_mtime)),
                md5=hashlib.md5(open(path, "rb").read()).hexdigest(),
                name=os.path.basename(path),
                size=os.path.getsize(path),
                version=version,
                desc="",
                url=""
            )

            return desc
        except (OSError, ValueError, DynamicObjectEncodeError, AttributeError) as e:
            print("Generate {!r} release desc failed: {}".format(path, e))
            return None


@register_handle
class RaspiAppManagerHandle(RaspiIOHandle):
    PATH = __name__.split('.')[-1]
    APP_ROOT = '/opt/raspi_io_apps'
    RELEASE_FILE_NAME = 'release.json'
    DESCRIPTION_FILE_NAME = 'description.json'

    IO_SERVER_NAME, IO_SERVER_PATH = "raspi_io_server", "/usr/local/sbin"
    APP_LAUNCH_SCRIPT_DIR = os.path.join(IO_SERVER_PATH, 'scripts')

    CATCH_EXCEPTIONS = (ValueError, IndexError, AttributeError,
                        RuntimeError, PermissionError, OSError, HttpRequestException)

    def __init__(self):
        super(RaspiAppManagerHandle, self).__init__()

    @staticmethod
    def get_nodes():
        return [RaspiAppManagerHandle.PATH]

    def check_app(self, app_name):
        """Check app env

        :param app_name: app_name
        :return: success return app description info failed raise exception
        """
        path = self.get_app_dir(app_name)

        try:
            with codecs.open(os.path.join(path, self.DESCRIPTION_FILE_NAME), "r", "utf-8") as fp:
                app_desc = AppDescription(**json.load(fp))

            if app_name != app_desc.app_name:
                raise RuntimeError('App name mismatching')

            return app_desc
        except FileNotFoundError:
            raise RuntimeError('App {!r} is not exist'.format(app_name))
        except (TypeError, RaspiMsgDecodeError) as e:
            raise RuntimeError('Load app desc file error: {}'.format(e))

    def get_app_dir(self, app_name):
        return os.path.join(self.APP_ROOT, app_name)

    def get_app_size(self, app_name):
        total_size = 0
        for dir_name, _, filenames in os.walk(self.get_app_dir(app_name)):
            for f in filenames:
                name = os.path.join(dir_name, f)
                if not os.path.islink(name):
                    total_size += os.path.getsize(name)

        return total_size

    def decompress_package(self, package):
        try:
            # Unpack local update package
            fmt = os.path.splitext(package)[-1][1:]
            with tarfile.open(os.path.join(self.TEMP_DIR, package), 'r:{}'.format(fmt)) as tar:
                tar.extractall(self.TEMP_DIR)

            return self.TEMP_DIR
        except (tarfile.TarError, IOError, OSError) as e:
            raise RuntimeError("Decompress package {!r} failed: {}".format(package, e))

    def verify_app(self, download_path, exe_name):
        """Verify app success return software release info

        :param download_path: app data file and release json file file path
        :param exe_name: app executable name
        :return: app release json
        """
        error_msg = "Verify app failed: {error}"
        release_json_file = os.path.join(download_path, self.RELEASE_FILE_NAME)

        try:
            # Get app release json file
            with codecs.open(release_json_file, "r", "utf-8") as fp:
                release_info = json.load(fp)
        except FileNotFoundError:
            raise RuntimeError(error_msg.format(error="do not found {}".format(release_json_file)))
        except json.JSONDecodeError as err:
            raise RuntimeError(error_msg.format(error="decode {!r} failed: {}".format(release_json_file, err)))

        # According to release json file verify data package md5 checksum
        data_package = release_info.get("name")
        release_data_file = os.path.join(download_path, data_package)

        try:
            if hashlib.md5(open(release_data_file, "rb").read()).hexdigest() != release_info.get("md5"):
                raise RuntimeError(error_msg.format(error="{!r} md5sum mismatching".format(data_package)))
        except FileNotFoundError:
            raise RuntimeError(error_msg.format(error="do not found: {}".format(data_package)))

        # Verify app executable file is in the package
        if os.path.splitext(release_data_file)[-1] == '.bz2':
            with tarfile.open(release_data_file, 'r:bz2') as tar:
                if exe_name not in [os.path.basename(x) for x in tar.getnames()]:
                    raise RuntimeError(error_msg.format(error="do not found executable file"))
        else:
            if exe_name != os.path.basename(release_data_file):
                raise RuntimeError(error_msg.format(error="do not found executable file"))

        return release_info

    def update_app(self, release_info, update_path):
        """Decompress release_info specified tar package to update_path specified directory"""
        try:
            # Killall app first
            app_name = os.path.splitext(release_info.get("name"))[0]
            if app_name != self.IO_SERVER_NAME:
                os.system("killall {}".format(app_name))

            # First decompress software
            src = os.path.join(self.TEMP_DIR, release_info.get('name'))
            if os.path.splitext(src)[-1] == '.bz2':
                tar = tarfile.open(src, 'r:bz2')
                tar.extractall(update_path)
                tar.close()
            else:
                os.system("cp {} {}".format(src, update_path))

            # Check if app is success installed
            os.system("sync")
            app_path = os.path.join(update_path, app_name)
            if not os.path.isfile(app_path):
                raise RuntimeError("Do not found app in update package")

            # Then save software release info
            try:
                with codecs.open(os.path.join(update_path, self.RELEASE_FILE_NAME), "w", "utf-8") as fp:
                    json.dump(release_info, fp)
            except json.JSONDecodeError as e:
                raise RuntimeError("{}".format(e))

            # Make app executable
            os.system("chmod u+x {}".format(app_path))

            # Set timer reboot system
            self.reboot_system(3.0)
            return release_info
        except (tarfile.TarError, IOError, OSError) as e:
            raise RuntimeError("Decompress software failed: {}".format(e))

    async def install_app(self, ws, data):
        install = InstallApp(**data)
        app_desc = AppDescription(**install.app_desc)
        app_dir = self.get_app_dir(app_desc.app_name)
        install_package = os.path.join(self.TEMP_DIR, install.package)

        if not os.path.isfile(install_package):
            raise RuntimeError("App install package: {!r} do not exist".format(install_package))

        if os.path.isdir(app_dir):
            raise RuntimeError("App {!r} already installed, please check".format(app_desc.app_name))

        path = self.decompress_package(install_package)
        release_info = self.verify_app(path, app_desc.exe_name)

        # Create app install dir and create boot script and description file
        os.makedirs(self.APP_LAUNCH_SCRIPT_DIR, mode=0o755, exist_ok=True)
        os.makedirs(self.get_app_dir(app_desc.app_name), mode=0o755, exist_ok=True)

        try:
            with codecs.open(os.path.join(app_dir, self.DESCRIPTION_FILE_NAME), "w", "utf-8") as fp:
                json.dump(app_desc.dict, fp)
        except json.JSONDecodeError as e:
            raise RuntimeError("{}".format(e))

        if app_desc.autostart:
            launch_script = os.path.join(self.APP_LAUNCH_SCRIPT_DIR, "{}.sh".format(app_desc.app_name))
            with open(launch_script, "w") as fp:
                fp.write('#!/bin/sh\n\n')
                fp.write("cd {} && ./{} {} &\n".format(app_dir, app_desc.exe_name, app_desc.boot_args))

            os.system("chmod u+x {}".format(launch_script))
        return self.update_app(release_info, app_dir)

    async def uninstall_app(self, ws, data):
        uninstall = UninstallApp(**data)
        app_desc = self.check_app(uninstall.app_name)

        os.system("rm -rf {}".format(self.get_app_dir(app_desc.app_name)))
        os.system("rm {}".format(os.path.join(self.APP_LAUNCH_SCRIPT_DIR, "{}.sh".format(app_desc.app_name))))
        return True

    async def fetch_update(self, ws, data):
        fetch = FetchUpdate(**data)
        gogs_request = GogsRequest(**fetch.auth)

        repo_releases = gogs_request.get_repo_releases(fetch.repo_name)
        if not repo_releases:
            raise RuntimeError("Do not fetch anything, please check name")

        release_list = list()
        for release in repo_releases:
            if not isinstance(release, RepoRelease):
                continue

            if self.RELEASE_FILE_NAME not in release.attachments():
                continue

            try:
                response = gogs_request.section_get(release.get_attachment_url(self.RELEASE_FILE_NAME))
                if not GogsRequest.is_response_ok(response):
                    continue

                desc = GogsSoftwareReleaseDesc.default()
                try:
                    desc.update(json.loads(response.content))
                except TypeError:
                    desc.update(json.loads(response.content.decode()))

                desc.update(DynamicObject(desc=release.html_desc))
                desc.update(DynamicObject(url=release.get_attachment_url(desc.name)))

                release_list.append((release.dict, desc.dict))
            except (IndexError, ValueError, AttributeError, DynamicObjectEncodeError) as e:
                print("{!r} get_releases error {}".format(self.__class__.__name__, e))
                continue

        return release_list[0] if fetch.newest else release_list

    async def online_update(self, ws, data):
        update = OnlineUpdate(**data)
        gogs_request = GogsRequest(**update.auth)

        # Check app first
        app_desc = self.check_app(update.app_name)

        try:
            # Download app release
            release = RepoRelease(**update.release)
            result = gogs_request.download_package(release.attachment, self.TEMP_DIR, timeout=update.timeout)
        except Exception as e:
            return RuntimeError("Download failed: {}".format(e))

        # Check download result
        if not all(result.values()):
            raise RuntimeError("Download failed: {}".format(result))

        release_info = self.verify_app(self.TEMP_DIR, app_desc.exe_name)
        return self.update_app(release_info, self.get_app_dir(update.app_name))

    async def local_update(self, ws, data):
        update = LocalUpdate(**data)
        if update.app_name == self.IO_SERVER_NAME:
            exe_name, update_path = self.IO_SERVER_NAME, self.IO_SERVER_PATH
        else:
            update_path = self.get_app_dir(update.app_name)
            exe_name = self.check_app(update.app_name).exe_name

        path = self.decompress_package(update.package)
        release_info = self.verify_app(path, exe_name)
        return self.update_app(release_info, update_path)

    async def get_app_list(self, ws, data):
        return os.listdir(self.APP_ROOT)

    async def get_app_state(self, ws, data):
        state = GetAppState(**data)
        app_desc = self.check_app(state.app_name)

        app_name = app_desc.app_name
        app_dir = self.get_app_dir(app_name)
        app_exe_file = os.path.join(app_dir, app_desc.exe_name)
        release_file = os.path.join(app_dir, self.RELEASE_FILE_NAME)

        if not os.path.isfile(release_file):
            raise RuntimeError("Do not found release file: {}".format(release_file))

        try:
            with codecs.open(release_file, "r", "utf-8") as fp:
                release_info = json.load(fp)

            state = "Running" if os.path.basename(app_exe_file) in (p.name() for p in psutil.process_iter()) else "Stop"

            return AppState(app_name=app_name,
                            version=release_info['version'],
                            release_date=release_info['date'],
                            size=self.get_app_size(app_name),
                            md5=hashlib.md5(open(app_exe_file, 'rb').read()).hexdigest(), state=state).dict
        except KeyError as e:
            raise RuntimeError("Release file format error: {}".format(e))
        except json.JSONDecodeError as e:
            raise RuntimeError("Load release file error: {}".format(e))
