import os
import json
import stat
import tarfile
import pathlib
import hashlib
import datetime
from raspi_ios.version import version


if __name__ == '__main__':
    dist = 'dist'
    name = 'raspi_io_server'
    boot_script = 'boot_apps.sh'
    release_file = 'release.json'
    path = os.path.join(dist, name)

    try:
        desc = dict(
            date=str(datetime.datetime.fromtimestamp(pathlib.Path(path).stat().st_mtime)),
            md5=hashlib.md5(open(path, "rb").read()).hexdigest(),
            name=os.path.basename(path),
            size=os.path.getsize(path),
            version=float(version),
            desc="",
            url=""
        )

        with open(os.path.join(dist, release_file), 'w', encoding='utf-8') as fp:
            json.dump(desc, fp, indent=4)

        with open(os.path.join(dist, boot_script), 'w', encoding='utf-8') as fp:
            fp.write('#!/bin/sh\n\n')
            fp.write('root=/usr/local/sbin/scripts\n')
            fp.write('cd $root\n')
            fp.write('for app in `ls $root`\n')
            fp.write('do\n')
            fp.write('\techo "Boot $app"\n')
            fp.write('\t./$app\n')
            fp.write('done\n')

        os.chmod(path=os.path.join(dist, boot_script),
                 mode=stat.S_IXUSR | stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH | stat.S_IWRITE)

        with tarfile.open(os.path.join(dist, '{}_release_{}.tar'.format(name, version)), 'w:tar') as tar:
            tar.add(os.path.join(dist, name))
            tar.add(os.path.join(dist, boot_script))
            tar.add(os.path.join(dist, release_file))

    except (OSError, ValueError, AttributeError) as e:
        print("Generate {!r} release desc failed: {}".format(path, e))
