import os

__author__ = 'kalmar'
from PyQt5.QtWidgets import QDialog, QFileDialog
from ui.configureUI import Ui_dialogConfigure
from ui.newtraceUI import Ui_dialogNewTrace
from settings import settings


class ConfigureWindow(QDialog, Ui_dialogConfigure):
    def __init__(self, parent=None):
        super(ConfigureWindow, self).__init__(parent)
        self.initUi()

    def accept(self):
        settings.set('main', 'NEW_TERMINAL_COMMAND', self.textTerminalCmd.text())
        settings.set('main', 'TCP_WRAPPER_COMMAND', self.textTCPWrapper.text())
        super(ConfigureWindow, self).accept()

    def reject(self):
        super(ConfigureWindow, self).reject()

    def initUi(self):
        self.setupUi(self)
        self.connectEvents()
        self.textTerminalCmd.insert(settings.get('main', 'NEW_TERMINAL_COMMAND'))
        self.textTCPWrapper.insert(settings.get('main', 'TCP_WRAPPER_COMMAND'))

    def connectEvents(self):
        return


class NewTraceWindow(QDialog, Ui_dialogNewTrace):
    def __init__(self, parent):
        super(NewTraceWindow, self).__init__(parent)
        self.initUi()

    def initUi(self):
        self.setupUi(self)
        self.connectEvents()
        self.textExecutable.insert(settings.get('new trace', 'EXECUTABLE'))
        self.textArguments.insert(settings.get('new trace', 'ARGUMENTS_TEXT'))
        self.textArgumentsFile.insert(settings.get('new trace', 'ARGUMENTS_FILE'))
        self.textStartDirectory.insert(os.path.realpath(settings.get('new trace', 'START_DIR')))
        if settings.get('new trace', 'ARGUMENTS_USE_FILE') != 'False':
            self.checkBoxTakeArgumentsFromFile.click()
        else:
            self.checkBoxTakeArgumentsFromFile.click()
            self.checkBoxTakeArgumentsFromFile.click()

    def connectEvents(self):
        self.buttonNewTraceCancel.clicked.connect(self.reject)
        self.buttonRunTrace.clicked.connect(self.run)
        self.buttonSaveTraceSettings.clicked.connect(self.save)
        self.checkBoxTakeArgumentsFromFile.clicked.connect(self.checkBoxGetArgumentsFromFileClicked)
        self.buttonGetExecutableFile.clicked.connect(self.buttonGetExecutableFileClicked)
        self.buttonGetStartDirectory.clicked.connect(self.buttonGetStartDirectoryClicked)

    def buttonGetExecutableFileClicked(self):
        dialog = QFileDialog()
        dialog.setDirectory(self.textStartDirectory.text())
        path = dialog.getOpenFileName()
        if path[1]:
            self.textExecutable.setText(os.path.realpath(path[0]))

    def buttonGetStartDirectoryClicked(self):
        dialog = QFileDialog()
        dialog.setDirectory(self.textStartDirectory.text())
        path = dialog.getExistingDirectory()
        if path:
            self.textStartDirectory.setText(os.path.realpath(path))

    def checkBoxGetArgumentsFromFileClicked(self):
        if self.checkBoxTakeArgumentsFromFile.isChecked():
            self.textArguments.setDisabled(True)
            self.buttonGetArgumentsFile.setDisabled(False)
            self.textArgumentsFile.setDisabled(False)
        else:
            self.textArguments.setDisabled(False)
            self.buttonGetArgumentsFile.setDisabled(True)
            self.textArgumentsFile.setDisabled(True)

    def save(self):
        settings.set('new trace', 'EXECUTABLE', self.textExecutable.text())
        settings.set('new trace', 'ARGUMENTS_TEXT', self.textArguments.text())
        settings.set('new trace', 'ARGUMENTS_FILE', self.textArgumentsFile.text())
        settings.set('new trace', 'ARGUMENTS_USE_FILE', str(self.checkBoxTakeArgumentsFromFile.isChecked()))
        settings.set('new trace', 'START_DIR', os.path.realpath(self.textStartDirectory.text()))
        self.parent().status("Saved")

    def run(self):
        self.save()
        self.parent().traceFromExecutable()
        self.accept()
