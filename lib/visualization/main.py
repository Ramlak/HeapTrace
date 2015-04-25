from __future__ import print_function
__author__ = 'kalmar'

import os

from PyQt5.QtWidgets import QMainWindow, QApplication, QDesktopWidget, qApp, QFileDialog
from PyQt5.QtCore import QProcess, QThread
from ui.mainUI import Ui_MainWindow
from utils.misc import randoms, BlockingFIFOReader, PopenAndCall


class HeapTrace(object):
    def __init__(self, filepath):
        self.filepath = filepath[0]
        self.fifopath = os.path.join(os.environ['TMPDIR'], randoms(9))
        self.reader = None
        self.thread = None
        self.proc = None

    def run(self, mainWindow):
        self.log = []
        self.mainWindow = mainWindow
        self.mainWindow.textLog.clear()
        os.mkfifo(self.fifopath)

        self.reader = BlockingFIFOReader(self.fifopath)
        self.thread = QThread()
        self.reader.moveToThread(self.thread)

        self.reader.got_line.connect(self.newTraceLine)
        self.thread.started.connect(self.reader.read_fifo)
        self.reader.finished.connect(self.on_reader_finished)
        self.thread.finished.connect(self.on_thread_finished)

        self.proc = PopenAndCall(" ".join(["/usr/bin/pin", "-t", "../pin/obj-intel64/heaptrace.so", "-o", self.fifopath, "--", self.filepath]), shell=True)
        self.proc.finished.connect(self.on_proc_finished)
        self.proc.start()

        self.thread.start()

    def newTraceLine(self, line):
        self.log.append(line)
        self.mainWindow.textLog.append(line + "\n")

    def on_proc_finished(self):
        self.mainWindow.status("Process finished")
        self.thread.requestInterruption()
        try:
            os.remove(self.fifopath)
        except Exception:
            pass

    def on_reader_finished(self):
        self.thread.quit()
        self.reader.fifo.close()
        self.reader.deleteLater()
        try:
            os.remove(self.fifopath)
        except Exception:
            pass

    def on_thread_finished(self):
        self.thread.deleteLater()


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.initUi()
        self.connectEvents()

    def initUi(self):
        self.setupUi(self)
        self.status(u"Ready")
        self.center()

    def connectEvents(self):
        self.actionExit.triggered.connect(qApp.quit)
        self.actionLive.triggered.connect(self.traceFromExecutable)

    def traceFromExecutable(self):
        self.currentTrace = HeapTrace(QFileDialog.getOpenFileName(self, 'Open file', os.environ['TMPDIR']))
        self.currentTrace.run(self)
        self.status("Starting {}".format(self.currentTrace.filepath))

    def center(self):
        frame = self.frameGeometry()
        frame.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(frame.topLeft())

    def status(self, msg):
        self.statusbar.showMessage(unicode(msg))


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    myapp = MainWindow()
    myapp.show()
    sys.exit(app.exec_())