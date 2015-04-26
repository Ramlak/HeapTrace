__author__ = 'kalmar'
from PyQt5.QtWidgets import QDialog
from ui.configureUI import Ui_dialogConfigure
from settings import settings


class ConfigureWindow(QDialog, Ui_dialogConfigure):
    def __init__(self, parent=None):
        super(ConfigureWindow, self).__init__(parent)
        self.initUi()
        self.connectEvents()

    def accept(self):
        settings.set('main', 'NEW_TERMINAL_COMMAND', self.textTerminalCmd.text())
        super(ConfigureWindow, self).accept()

    def reject(self):
        super(ConfigureWindow, self).reject()

    def initUi(self):
        self.setupUi(self)
        self.textTerminalCmd.insert(settings.get('main', 'NEW_TERMINAL_COMMAND'))

    def connectEvents(self):
        return
