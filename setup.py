# -*- coding: utf-8 -*-
import sys
import os.path
import setuptools

NAME = 'raspi_ios'
root_dir = os.path.abspath(os.path.dirname(__file__))

readme_file = os.path.join(root_dir, 'README.md')
with open(readme_file) as f:
    long_description = f.read()

version_module = os.path.join(root_dir, NAME, 'version.py')
with open(version_module) as f:
    exec(f.read())

py_version = sys.version_info[:2]

if py_version < (3, 5):
    raise Exception("raspi_ios requires Python >= 3.5")

packages = [NAME]


setuptools.setup(
    name=NAME,
    version=version,
    description="Raspberry pi websocket io server",
    long_description=long_description,
    url='https://github.com/amaork/raspi-ios',
    author='Amaork',
    author_email='amaork@gmail.com',
    license='MIT',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
    ],
    packages=packages,
    extras_require={
        ':python_version>="3.5"': ['asyncio', 'websockets', 'RPi.GPIO', 'pyserial', 'raspi_io>=0.0.7'],
    },
)