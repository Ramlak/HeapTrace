from Queue import Queue
from PyQt5.QtCore import QThread
import os
import signal
from settings import settings
from utils.misc import getcmd, PopenAndCall, PinCommunication
from utils.windows import HeapWindow

__author__ = 'kalmar'


class HeapTrace(object):
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.reader = None
        self.thread = None
        self.proc = None

    def run(self):
        self.log = []
        self.bits = int(settings.get('new trace', 'BITS'))
        self.mainWindow.textLog.clear()
        invocation = PopenAndCall(getcmd(self.bits), shell=False)
        invocation.finished.connect(self.on_proc_finished)
        invocation.started.connect(self.on_proc_started)
        invocation.start(self)

    def kill(self):
        if self.thread:
            self.thread.quit()
        if self.proc:
            self.proc.terminate()
        try:
            os.kill(self.pin_proc, signal.SIGKILL)
        except Exception:
            pass

    def newHeapOperation(self, packet):
        self.log.append(packet)
        self.mainWindow.textLog.append(packet.text_dump() + "\n")

    def on_proc_started(self):
        self.mainWindow.status("Process started")
        self.events = Queue(maxsize=0)
        self.reader = PinCommunication('localhost', 12345, self.bits, self.events)
        self.thread = QThread()
        self.reader.moveToThread(self.thread)
        self.reader.got_heap_op.connect(self.newHeapOperation)
        self.reader.pin_PID.connect(self.on_pin_pid_received)
        self.thread.started.connect(self.reader.event_loop)
        self.reader.finished.connect(self.on_reader_finished)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def on_pin_pid_received(self, pid):
        self.pin_proc = pid
        self.heapView = HeapWindow(self.mainWindow)
        self.heapView.show()

    def on_proc_finished(self):
        if self.thread:
            self.thread.quit()
        self.proc = None
        self.kill()
        self.mainWindow.status("Process finished ({} lines)".format(len(self.log)))

    def on_reader_finished(self):
        self.kill()
        self.reader.deleteLater()

    def on_thread_finished(self):
        self.thread.deleteLater()
        self.thread = None