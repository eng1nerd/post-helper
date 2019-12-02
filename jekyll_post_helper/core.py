"""
Jekyll post helper

Usage:
  post-helper -s SCHEMA_FILE
  post-helper -h
Options:
  -s SCHEMA_FILE --schema=SCHEMA_FILE       yaml file that describes posts
  -h --help                                 show this screen

"""

from docopt import docopt


def entry(*args, **kwargs):
    """
    Entrypoint function
    """
    args = docopt(__doc__)


if __name__ == "__main__":
    entry()
