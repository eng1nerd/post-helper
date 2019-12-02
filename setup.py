# -*- coding: utf-8 -*-

import io
import os
import sys
import codecs
from distutils.core import Command, setup
from shutil import rmtree
from typing import List, Dict, Any

from setuptools import find_packages

PACKAGE_NAME = "jekyll-post-helper"
PY_PACKAGE_NAME = PACKAGE_NAME.replace("-", "_")
DESCRIPTION = "It prepares posts for publishing on photography blog that is based on Jekyll."
GIT_URL = "https://github.com/eng1nerd/jekyll-post-helper"
EMAIL = "vladimir@enginerd.io"
AUTHOR = "Vladimir Loskutov"
KEYWORDS = "jekyll, blogging, photos"
REQUIRES_PYTHON = ">=3.5.0"
VERSION = "0.0.1" # Jiggle Version Was Here

REQUIRED: List[str] = []

EXTRAS: Dict[str, Any] = {}

here = os.path.abspath(os.path.dirname(__file__))

# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

about: Dict[str, str] = {}
if not VERSION:
    with open(os.path.join(here, PY_PACKAGE_NAME, "__version__.py")) as f:  # type: ignore
        exec(f.read(), about)
else:
    about["__version__"] = VERSION


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []  # type: ignore

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel distribution…")
        os.system("{0} setup.py sdist bdist_wheel".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine…")
        os.system("twine upload dist/*")

        self.status("Pushing git tags…")
        os.system("git tag v{0}".format(about["__version__"]))
        os.system("git push --tags")

        sys.exit()


setup(
    name=PACKAGE_NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=GIT_URL,
    packages=find_packages(exclude=("tests",)),
    entry_points={"console_scripts": ["post-helper=jekyll_post_helper.core:entry"],},
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    license="MIT",
    keywords=KEYWORDS,
    classifiers=[
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    cmdclass={"upload": UploadCommand,},
)
