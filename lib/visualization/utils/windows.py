from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
import os
from utils.heap import BT, heap_op_type_t

__author__ = 'kalmar'
from PyQt5.QtWidgets import QDialog, QFileDialog, QDockWidget, QWidget
from ui.configureUI import Ui_dialogConfigure
from ui.newtraceUI import Ui_dialogNewTrace
from ui.heapviewUI import Ui_dockHeapWindow
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
        self.spinBoxWrapperPort.setValue(int(settings.get('new trace', 'TCP_WRAPPER_PORT')))
        if settings.get('new trace', 'ARGUMENTS_USE_FILE') != 'False':
            self.checkBoxTakeArgumentsFromFile.click()
        else:
            self.checkBoxTakeArgumentsFromFile.click()
            self.checkBoxTakeArgumentsFromFile.click()
        if settings.get('new trace', 'USE_TCP_WRAPPER') != 'False':
            self.checkBoxUseWrapper.click()
        else:
            self.checkBoxUseWrapper.click()
            self.checkBoxUseWrapper.click()

    def connectEvents(self):
        self.buttonNewTraceCancel.clicked.connect(self.reject)
        self.buttonRunTrace.clicked.connect(self.run)
        self.buttonSaveTraceSettings.clicked.connect(self.save)
        self.checkBoxTakeArgumentsFromFile.clicked.connect(self.checkBoxGetArgumentsFromFileClicked)
        self.buttonGetExecutableFile.clicked.connect(self.buttonGetExecutableFileClicked)
        self.buttonGetStartDirectory.clicked.connect(self.buttonGetStartDirectoryClicked)
        self.checkBoxUseWrapper.clicked.connect(self.checkBoxUseWrapperClicked)

    def checkBoxUseWrapperClicked(self):
        if self.checkBoxUseWrapper.isChecked():
            self.spinBoxWrapperPort.setDisabled(False)
        else:
            self.spinBoxWrapperPort.setDisabled(True)

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
        settings.set('new trace', 'TCP_WRAPPER_PORT', str(self.spinBoxWrapperPort.value()))
        settings.set('new trace', 'USE_TCP_WRAPPER', str(self.checkBoxUseWrapper.isChecked()))
        self.parent().status("Saved")

    def run(self):
        self.save()
        self.parent().traceFromExecutable()
        self.accept()


counter = 0


class Block(QWidget):
    def __init__(self, packet):
        super(Block, self).__init__()
        self.packet = packet
        self.setAutoFillBackground(True)
        self.parsePacket()
        self.setColor()

    def mouseDoubleClickEvent(self, event):
        self.status = (self.status + 1) % 3
        self.setColor()

    def parsePacket(self):
        code = self.packet.code
        if code == heap_op_type_t.PKT_FREE:
            self.status = BT.FREE
            self.base_addr = self.packet.args[0]
        elif code == heap_op_type_t.PKT_IDLE:
            self.status = BT.UNALLOCATED
        else:
            self.status = BT.ALLOCATED
            self.base_addr = self.packet.return_value

    def new_packet(self, packet):
        self.packet = packet
        self.parsePacket()
        self.setColor()

    def setColor(self):
        if self.status == BT.FREE:
            color = Qt.red
        elif self.status == BT.ALLOCATED:
            color = Qt.green
        elif self.status == BT.UNALLOCATED:
            color = Qt.black
        pallete = QPalette()
        pallete.setColor(QPalette.Background, color)
        self.setPalette(pallete)
        self.update()

    def setFree(self):
        self.status = BT.FREE
        self.setColor()

    def setAllocated(self):
        self.status = BT.ALLOCATED
        self.setColor()

    def setUnallocated(self):
        self.status = BT.UNALLOCATED
        self.setColor()

    def isFree(self):
        return self.status == BT.FREE

    def isAllocated(self):
        return self.status == BT.ALLOCATED


class HeapWindow(QDockWidget, Ui_dockHeapWindow):
    def __init__(self, parent):
        super(HeapWindow, self).__init__(parent)
        self.initUi()

    def initUi(self):
        self.setupUi(self)
        self.connectEvents()

    def push_new_block(self, block):
        self.layoutHeapView.addChildWidget(block)

    def connectEvents(self):
        pass