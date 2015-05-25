from utils.heaptrace import HeapTrace

__author__ = 'kalmar'

from PyQt5.QtWidgets import QMainWindow, QApplication, QDesktopWidget, qApp, QInputDialog, QDialog
from ui.mainUI import Ui_MainWindow
from utils.windows import ConfigureWindow, NewTraceWindow, HeapWindow
from settings import settings


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.initUi()
        self.connectEvents()
        self.currentTrace = None

    def initUi(self):
        self.setupUi(self)
        self.status(u"Ready")
        frame = self.frameGeometry()
        frame.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(frame.topLeft())

    def connectEvents(self):
        self.actionExit.triggered.connect(qApp.quit)
        self.actionLive.triggered.connect(self.showNewTraceDialog)
        self.actionConfigure.triggered.connect(self.showConfigurationDialog)
        self.actionKill.triggered.connect(self.killCurrentTrace)
        self.actionShowHeap.triggered.connect(self.showHeapWindow)

    def showHeapWindow(self):
        heapWindow = HeapWindow(self)
        heapWindow.show()

    def killCurrentTrace(self):
        if self.currentTrace:
            self.currentTrace.kill()

    def showConfigurationDialog(self):
        configureWindow = ConfigureWindow(self)
        configureWindow.show()

    def showNewTraceDialog(self):
        newTraceWindow = NewTraceWindow(self)
        newTraceWindow.show()

    def traceFromExecutable(self):
        if not settings.get('new trace', 'EXECUTABLE'):
            self.status("[!] No executable provided")
            return
        self.currentTrace = HeapTrace(self)
        self.currentTrace.run()
        self.status("Starting {}".format(settings.get('new trace', 'EXECUTABLE')))

    def status(self, msg):
        self.statusbar.showMessage(unicode(msg))

    def cleanup(self):
        self.killCurrentTrace()
        settings.save()


if __name__ == "__main__":
    import sys
    import atexit
    app = QApplication(sys.argv)
    myapp = MainWindow()
    myapp.show()
    atexit.register(myapp.cleanup)
    sys.exit(app.exec_())