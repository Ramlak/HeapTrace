from PyQt5.QtCore import QThread
import os
from utils.misc import randoms, getcmd, PopenAndCall, PinCommunication

__author__ = 'kalmar'


class HeapTrace(object):
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.reader = None
        self.thread = None
        self.proc = None

    def run(self):
        self.log = []
        self.mainWindow.textLog.clear()
        self.reader = PinCommunication('localhost', 12345)
        self.thread = QThread()
        self.reader.moveToThread(self.thread)
        self.reader.got_heap_op.connect(self.newHeapOperation)
        self.thread.started.connect(self.reader.read_fifo)
        self.reader.finished.connect(self.on_reader_finished)
        self.thread.finished.connect(self.on_thread_finished)
        invocation = PopenAndCall(getcmd(self.fifopath), shell=False)
        invocation.finished.connect(self.on_proc_finished)
        invocation.start(self)
        self.thread.start()

    def kill(self):
        if self.thread:
            self.thread.quit()
        if self.proc:
            self.proc.kill()

    def newHeapOperation(self, line):
        self.log.append(line)
        self.mainWindow.textLog.append(line)

    def on_proc_finished(self):
        self.proc = None
        self.mainWindow.status("Process finished ({} lines)".format(len(self.log)))
        self.thread.requestInterruption()
        try:
            os.remove(self.fifopath)
        except Exception:
            pass

    def on_reader_finished(self):
        self.kill()
        self.reader.fifo.close()
        self.reader.deleteLater()
        try:
            os.remove(self.fifopath)
        except Exception:
            pass

    def on_thread_finished(self):
        self.thread.deleteLater()
        self.thread = None