# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'heapviewUI.ui'
#
# Created by: PyQt5 UI code generator 5.3.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_dockHeapWindow(object):
    def setupUi(self, dockHeapWindow):
        dockHeapWindow.setObjectName("dockHeapWindow")
        dockHeapWindow.resize(400, 300)
        dockHeapWindow.setFloating(True)
        self.dockWidgetContents = QtWidgets.QWidget()
        self.dockWidgetContents.setObjectName("dockWidgetContents")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.dockWidgetContents)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.layoutHeapView = QtWidgets.QHBoxLayout()
        self.layoutHeapView.setSpacing(0)
        self.layoutHeapView.setObjectName("layoutHeapView")
        self.horizontalLayout_2.addLayout(self.layoutHeapView)
        dockHeapWindow.setWidget(self.dockWidgetContents)

        self.retranslateUi(dockHeapWindow)
        QtCore.QMetaObject.connectSlotsByName(dockHeapWindow)

    def retranslateUi(self, dockHeapWindow):
        _translate = QtCore.QCoreApplication.translate
        dockHeapWindow.setWindowTitle(_translate("dockHeapWindow", "Heap View"))

