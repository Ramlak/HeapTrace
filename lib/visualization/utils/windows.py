__author__ = 'kalmar'
from PyQt5.QtWidgets import QDialog
from ui.configure import Ui_dialogConfigure
from settings import settings


class ConfigureWindow(QDialog, Ui_dialogConfigure):
    def __init__(self, parent=None):
        super(ConfigureWindow, self).__init__(parent)
        self.initUi()
        self.connectEvents()

    def accept(self):
        settings.terminal_command = self.textTerminalCmd.text()
        settings.saveToFile()
        super(ConfigureWindow, self).reject()

    def reject(self):
        super(ConfigureWindow, self).reject()

    def initUi(self):
        self.setupUi(self)
        self.textTerminalCmd.insert(settings.terminal_command)

    def connectEvents(self):
        return
