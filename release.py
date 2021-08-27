import os
import json
import stat
import tarfile
from raspi_ios.version import version
from raspi_ios.app_manager import GogsSoftwareReleaseDesc


if __name__ == '__main__':
    dist = 'dist'
    name = 'raspi_io_server'
    path = os.path.join(dist, name)
    package_name = '{}_release_{}.tar'.format(name, version)

    readme = 'readme'
    boot_script = 'boot_apps.sh'
    release_file = 'release.json'
    package_file_list = (name, readme, boot_script, release_file)
    rc_local_launch_cmd = 'mkdir /tmp/rios && cp /usr/local/sbin/raspi_io_server ' \
                          '/tmp/rios && cd /tmp/rios && ./raspi_io_server && /usr/local/sbin/boot_apps.sh'

    try:
        # Generate release.json
        desc = GogsSoftwareReleaseDesc.generate(path, version)
        with open(os.path.join(dist, release_file), 'w', encoding='utf-8') as fp:
            json.dump(desc.dict, fp, indent=4)

        # Generate boot_args.sh
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

        # Generate readme
        with open(os.path.join(dist, readme), 'w', encoding='utf-8') as fp:
            fp.write("1. first extract {!r} to '/usr/local/sbin'\n".format(package_name))
            fp.write("2. then add {!r} to '/etc/rc.local'\n".format(rc_local_launch_cmd))

        # Pack to release package
        pwd = os.getcwd()
        os.chdir(dist)
        with tarfile.open(package_name, 'w:tar') as tar:
            for file in package_file_list:
                tar.add(file)

        os.chdir(pwd)
    except (OSError, ValueError, AttributeError) as e:
        print("Generate {!r} release desc failed: {}".format(path, e))
