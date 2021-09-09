from setuptools import (
    find_packages,
    setup,
)

import uma


with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

package_name = uma.PACKAGE_NAME

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name=package_name,
    version=uma.__version__,
    url="https://github.com/mh-superbox/unipi-mqtt-api",
    description=uma.PACKAGE_DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    license_files="LICENSE",
    author="Michael Hacker",
    author_email="mh@superbox.one",
    include_package_data=True,
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=requirements,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
    ],
)
