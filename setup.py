from pathlib import Path
from typing import Optional

from setuptools import setup

dependencies: dict = {}

with Path("requirements.txt").open(encoding="utf-8") as reqs:
    # pylint: disable=invalid-name
    group: Optional[str] = None

    for line in reqs.read().split("\n"):
        if not line:
            group = None
        elif line.startswith("# install:"):
            group = line.split(":")[1]
            dependencies[group] = []
        elif not line.startswith("#") and group:
            dependencies[group].append(line)
    # pylint: enable=invalid-name

install_req = dependencies["required"]
del dependencies["required"]

setup(
    install_requires=install_req,
    extras_require=dependencies,
    package_data={
        "unipi-control": ["py.typed"],
    },
)
