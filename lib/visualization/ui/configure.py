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
        dialogConfigure.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(dialogConfigure)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(dialogConfigure)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(dialogConfigure)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.textTerminalCmd = QtWidgets.QLineEdit(dialogConfigure)
        self.textTerminalCmd.setText("")
        self.textTerminalCmd.setObjectName("textTerminalCmd")
        self.verticalLayout.addWidget(self.textTerminalCmd)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
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
        self.label.setText(_translate("dialogConfigure", "Command to run new terminal"))
        self.label_2.setText(_translate("dialogConfigure", "[CMD] for command to execute"))

