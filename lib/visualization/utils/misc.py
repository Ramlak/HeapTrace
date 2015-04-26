__author__ = 'kalmar'

import string
import random
import os
import subprocess
import threading
from settings import settings
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QProcess
from select import select


def getcmd():
    cmd = ""
    cmd += "cd {};".format(os.path.realpath(settings.get('new trace', 'START_DIR')))
    print settings.get('new trace', 'USE_TCP_WRAPPER')
    if settings.get('new trace', 'USE_TCP_WRAPPER') == 'False':
        cmd += settings.get('main', 'TCP_WRAPPER_COMMAND').replace('[CMD]', os.path.realpath(settings.get('new trace', 'COMMAND'))).replace('[PORT]', settings.get('new trace', 'TCP_WRAPPER_PORT'))
    else:
        cmd += settings.get('main', 'NEW_TERMINAL_COMMAND').replace('[CMD]', os.path.realpath(settings.get('new trace', 'COMMAND')))

    return cmd


def randoms(count, alphabet=string.lowercase):
    return ''.join(random.choice(alphabet) for _ in xrange(count))


class BlockingFIFOReader(QObject):

    """A worker which reads commands from a FIFO endlessly."""

    got_line = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, filename):
        super(BlockingFIFOReader, self).__init__()
        self.filename = filename
        self.fifo = None

    def read_fifo(self):
        # We open as R/W so we never get EOF and have to reopen the pipe.
        # See http://www.outflux.net/blog/archives/2008/03/09/using-select-on-a-fifo/
        # We also use os.open and os.fdopen rather than built-in open so we can
        # add O_NONBLOCK.
        self.buffer = ""
        self.fifo = os.fdopen(os.open(self.filename, os.O_RDWR | os.O_NONBLOCK), 'r')
        while True:
            ready_r, ready_w, ready_e = select([self.fifo], [], [], 1)
            if ready_r:
                lines = self.readPipeLines()
                for line in lines:
                    self.got_line.emit(line.rstrip())
            if QThread.currentThread().isInterruptionRequested():
                self.finished.emit()
                return

    def readPipeLines(self):
        lines = []
        while True:
            try:
                self.buffer += self.fifo.read(1)
                if self.buffer.endswith("\n"):
                    lines.append(self.buffer.rstrip())
                    self.buffer = ""
            except IOError as e:
                if e.errno == 11:
                    return lines
                else:
                    raise e


class PopenAndCall(QObject):

    finished = pyqtSignal()

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        super(PopenAndCall, self).__init__()

    def start(self, heaptrace):
        self.heaptrace. = heaptrace
        threading.Thread(target=self.runInThread, args=[]).start()

    def runInThread(self):
        proc = subprocess.Popen(*self.args, **self.kwargs)
        proc.wait()
        self.finished.emit()