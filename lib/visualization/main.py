__author__ = 'kalmar'

import os

from PyQt5.QtWidgets import QMainWindow, QApplication, QDesktopWidget, qApp, QFileDialog
from ui.mainUI import Ui_MainWindow
from utils.misc import randoms


class HeapTrace(object):
    def __init__(self, filepath):
        self.filepath = filepath[0]
        self.pipepath = os.path.join(os.environ['TMPDIR'], randoms(9))
        print self.pipepath, self.filepath


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