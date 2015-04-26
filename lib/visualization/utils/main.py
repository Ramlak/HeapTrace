from utils.heaptrace import HeapTrace

__author__ = 'kalmar'

from PyQt5.QtWidgets import QMainWindow, QApplication, QDesktopWidget, qApp, QInputDialog, QDialog
from ui.mainUI import Ui_MainWindow
from utils.windows import ConfigureWindow
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
        self.actionLive.triggered.connect(self.traceFromExecutable)
        self.actionConfigure.triggered.connect(self.showConfigurationDialog)
        self.actionKill.triggered.connect(self.killCurrentTrace)

    def killCurrentTrace(self):
        if self.currentTrace:
            self.currentTrace.kill()

    def showConfigurationDialog(self):
        window = ConfigureWindow(self)
        window.show()

    def traceFromExecutable(self):
        path = QInputDialog.getText(self, u'Input', u"Command to run")
        if not path[0] or not path[1]:
            return

        settings.set('new trace', 'COMMAND', path[0])
        self.currentTrace = HeapTrace(self)
        self.currentTrace.run()
        self.status("Starting {}".format(settings.get('new trace', 'COMMAND')))

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