# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'configure.ui'
#
# Created by: PyQt5 UI code generator 5.3.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_dialogConfigure(object):
    def setupUi(self, dialogConfigure):
        dialogConfigure.setObjectName("dialogConfigure")
        dialogConfigure.resize(502, 399)
        self.verticalLayout = QtWidgets.QVBoxLayout(dialogConfigure)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget = QtWidgets.QWidget(dialogConfigure)
        self.widget.setObjectName("widget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_2 = QtWidgets.QLabel(self.widget)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.label_4 = QtWidgets.QLabel(self.widget)
        self.label_4.setObjectName("label_4")
        self.verticalLayout_2.addWidget(self.label_4)
        self.verticalLayout.addWidget(self.widget)
        spacerItem = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)
        self.label = QtWidgets.QLabel(dialogConfigure)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.textTerminalCmd = QtWidgets.QLineEdit(dialogConfigure)
        self.textTerminalCmd.setText("")
        self.textTerminalCmd.setObjectName("textTerminalCmd")
        self.verticalLayout.addWidget(self.textTerminalCmd)
        self.label_3 = QtWidgets.QLabel(dialogConfigure)
        self.label_3.setObjectName("label_3")
        self.verticalLayout.addWidget(self.label_3)
        self.textTCPWrapper = QtWidgets.QLineEdit(dialogConfigure)
        self.textTCPWrapper.setObjectName("textTCPWrapper")
        self.verticalLayout.addWidget(self.textTCPWrapper)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.buttonBox = QtWidgets.QDialogButtonBox(dialogConfigure)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(dialogConfigure)
        self.buttonBox.accepted.connect(dialogConfigure.accept)
        self.buttonBox.rejected.connect(dialogConfigure.reject)
        QtCore.QMetaObject.connectSlotsByName(dialogConfigure)

    def retranslateUi(self, dialogConfigure):
        _translate = QtCore.QCoreApplication.translate
        dialogConfigure.setWindowTitle(_translate("dialogConfigure", "Configuration"))
        self.widget.setToolTip(_translate("dialogConfigure", "<html><head/><body><p>Symbols to substitute</p></body></html>"))
        self.widget.setWhatsThis(_translate("dialogConfigure", "<html><head/><body><p>These symbols will be substituted by corresponding values</p></body></html>"))
        self.label_2.setText(_translate("dialogConfigure", "[CMD] for command to execute"))
        self.label_4.setText(_translate("dialogConfigure", "[PORT] for TCP wrapper port"))
        self.label.setText(_translate("dialogConfigure", "Command to run new terminal"))
        self.label_3.setText(_translate("dialogConfigure", "Command to run TCP wrapper"))

