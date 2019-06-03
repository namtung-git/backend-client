"""
    Wirepas Gateway Client
    ======================

    Installation script

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
import codecs
import os
import re
import glob

from setuptools import setup, find_packages

with open("README.md") as f:
    long_description = f.read()

with open("LICENSE") as f:
    license = f.read()


def filter(flist, rules=["private", ".out"]):
    for f in flist:
        for rule in rules:
            if rule in f:
                flist.pop(flist.index(f))
    return flist


def get_list_files(root, flist=None):
    if flist is None:
        flist = list()

    for path, subdirs, files in os.walk(root):
        for name in files:
            flist.append(os.path.join(path, name))
    return flist


def get_absolute_path(*args):
    """ Transform relative pathnames into absolute pathnames """
    directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(directory, *args)


def get_requirements(*args):
    """ Get requirements requirements.txt """
    requirements = set()
    with open(get_absolute_path(*args)) as handle:
        for line in handle:
            # Strip comments.
            line = re.sub(r"^#.*|\s#.*", "", line)
            # Ignore empty lines
            if line and not line.isspace():
                requirements.add(re.sub(r"\s+", "", line))
    return sorted(requirements)


setup(
    name="wirepas_backend_client",
    version="1.1.0",
    description="Wirepas backend client",
    long_description=long_description,
    author="Wirepas Oy",
    author_email="techsupport@wirepas.com",
    url="https://github.com/wirepas/backend-client",
    license="Apache-2",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python :: 3",
    ],
    keywords="wirepas connectivity iot mesh",
    packages=find_packages(exclude=["contrib", "docs", "tests", "examples"]),
    install_requires=get_requirements("requirements.txt"),
    include_package_data=True,
    data_files=[
        (
            "./wirepas_backend_client-extras/package",
            [
                "LICENSE",
                "README.md",
                "requirements.txt",
                "wirepas_backend_client/example_settings.yml",
                "wirepas_backend_client/certs/extwirepas.pem",
                "wirepas_backend_client/messages/diag_cbor_id.json",
                "setup.py",
            ],
        )
    ],
    entry_points={
        "console_scripts": [
            "wm-gw-cli=wirepas_backend_client.__main__:gw_cli",
            "wm-wnt-viewer=wirepas_backend_client.__main__:wnt_client",
            "wm-wpe-viewer=wirepas_backend_client.__main__:wpe_client",
        ]
    },
)
