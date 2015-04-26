__author__ = 'kalmar'
import os
from ConfigParser import SafeConfigParser
import io

CONFIG_PATH = os.path.join(os.environ['HOME'], ".htconfig")

DEFAULT_SETTINGS = ("""
[main]
NEW_TERMINAL_COMMAND=xterm -e "[CMD];read"
TCP_WRAPPER_COMMAND=socat tcp-listen:[PORT],reuseaddr exec:"[CMD]"
[new trace]
USE_TCP_WRAPPER=False
TCP_WRAPPER_PORT=1337
START_DIR=.
COMMAND=
BITS=32
""")


class Settings(SafeConfigParser):
    def __init__(self, *args, **kwargs):
        SafeConfigParser.__init__(self, *args, **kwargs)
        self.load()
        print "Created"

    def save(self):
        self.write(open(CONFIG_PATH, "w"))

    def load(self):
        if not os.path.exists(CONFIG_PATH):
            self.restore()
            self.save()
        else:
            self.readfp(open(CONFIG_PATH, "r"))

    def restore(self):
        self.readfp(io.BytesIO(DEFAULT_SETTINGS))

settings = Settings(allow_no_value=True)