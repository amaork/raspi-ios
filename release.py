import os
import json
import pathlib
import hashlib
import datetime
from raspi_ios.version import version


if __name__ == '__main__':
    dist = 'dist'
    name = 'raspi_io_server'
    path = os.path.join(dist, name)

    try:
        desc = dict(
            date=str(datetime.datetime.fromtimestamp(pathlib.Path(path).stat().st_mtime)),
            md5=hashlib.md5(open(path, "rb").read()).hexdigest(),
            name=os.path.basename(path),
            size=os.path.getsize(path),
            version=version,
            desc="",
            url=""
        )

        with open(os.path.join(dist, 'release.json'), 'w', encoding='utf-8') as fp:
            json.dump(desc, fp, indent=4)

    except (OSError, ValueError, AttributeError) as e:
        print("Generate {!r} release desc failed: {}".format(path, e))