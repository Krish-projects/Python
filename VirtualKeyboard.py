from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import datetime

# print ("Virtual keyboard.py first call startin at : startupTime",datetime.datetime.now())

class KeyButton(QtWidgets.QPushButton):
    sigKeyButtonClicked = QtCore.pyqtSignal()

    def __init__(self, key):
        super(KeyButton, self).__init__()

        self._key = key
        self._activeSize = QtCore.QSize(50,50)
        self.clicked.connect(self.emitKey)
        


    def emitKey(self):
        self.sigKeyButtonClicked.emit()

   
    def sizeHint(self):
        return QtCore.QSize(40,40)


class VirtualKeyboard(QWidget):

    sigInputString = QtCore.pyqtSignal(str)
    sigKeyButtonClicked = QtCore.pyqtSignal(str)


    def __init__(self, data, password_flag, log_q):
        LOWER = 0
        CAPITAL = 1       
        self.log_q = log_q
        self.password_flag = password_flag
        super(VirtualKeyboard, self).__init__()
        VirtualKeyboard.setGeometry(self, 0, 32, 480, 250)
        self.globalLayout = QtWidgets.QVBoxLayout(self)
        self.keysLayout = QtWidgets.QGridLayout()
        self.buttonLayout = QtWidgets.QHBoxLayout()

        self.keyListByLines = [
                ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
                ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', '='],
                ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '`', '-', '+'],
            ]


        self.inputString = data
        self.state = CAPITAL
        self.Control = LOWER

        self.capsButton = QtWidgets.QPushButton()
        self.capsButton.setText('abc')
        self.capsButton.setFixedHeight(50)
        self.capsButton.setFixedWidth(50)

        self.backButton = QtWidgets.QPushButton()
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap('Backspace.jpg'))
        self.backButton.setIcon(icon)
        self.backButton.setIconSize(QSize(40,27))
        self.backButton.setFixedHeight(50)
        self.backButton.setFixedWidth(50)

        
        self.okButton = QtWidgets.QPushButton()
        self.okButton.setText('OK')
        self.okButton.setFixedHeight(50)
        self.okButton.setFixedWidth(70)

        self.cancelButton = QtWidgets.QPushButton()
        self.cancelButton.setText("Cancel")
        self.cancelButton.setFixedHeight(50)
        self.cancelButton.setFixedWidth(80)

        self.controlButton = QtWidgets.QPushButton()
        self.controlButton.setText("123")
        self.controlButton.setFixedHeight(50)
        self.controlButton.setFixedWidth(50)

        self.spaceButton = QtWidgets.QPushButton()
        self.spaceButton.setText("   ")
        self.spaceButton.setFixedHeight(50)
        self.spaceButton.setFixedWidth(120)

        

        self.inputLine = QtWidgets.QLineEdit()
        self.inputLine.setText(self.inputString)


        for lineIndex, line in enumerate(self.keyListByLines):
            for keyIndex, key in enumerate(line):
                buttonName = "keyButton" + key.capitalize()
                self.__setattr__(buttonName, KeyButton(key))
                self.keysLayout.addWidget(self.getButtonByKey(key), self.keyListByLines.index(line), line.index(key))
                self.getButtonByKey(key).setText(key)
             
                self.getButtonByKey(key).sigKeyButtonClicked.connect(lambda v=key: self.addInputByKey(v))
              
                self.keysLayout.setColumnMinimumWidth(keyIndex, 20)
            self.keysLayout.setRowMinimumHeight(lineIndex, 20)

        self.capsButton.clicked.connect(self.switchState)
        self.backButton.clicked.connect(self.backspace)
        self.spaceButton.clicked.connect(self.space)
        self.okButton.clicked.connect(self.emitInputString) 
        self.cancelButton.clicked.connect(self.emitCancel)
        self.controlButton.clicked.connect(self.control)

        self.buttonLayout.addWidget(self.backButton)
        self.buttonLayout.addWidget(self.capsButton)
        self.buttonLayout.addWidget(self.controlButton)
        self.buttonLayout.addWidget(self.spaceButton)
        self.buttonLayout.addWidget(self.cancelButton)
        self.buttonLayout.addWidget(self.okButton)
        self.globalLayout.addWidget(self.inputLine)
        self.globalLayout.addLayout(self.keysLayout)

        self.globalLayout.addLayout(self.buttonLayout)
       

    def getButtonByKey(self, key):
        return getattr(self, "keyButton" + key.capitalize())

    def getLineForButtonByKey(self, key):
        return [key in keyList for keyList in self.keyListByLines].index(True)

    def switchState(self):
        self.state = not self.state
        if self.state == 1:
            
            self.log_q.put(["debug","VK",'Caps Virtual keyboard enabled'])
            self.keyListByLines1 = [
                    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
                    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', '='],
                    ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '.', '-', '+'],
                ]
            for lineIndex, line in enumerate(self.keyListByLines1):
                for keyIndex, key in enumerate(line):
                    buttonName = "keyButton" + key.capitalize()
                    self.__setattr__(buttonName, KeyButton(key))
                    self.keysLayout.addWidget(self.getButtonByKey(key), self.keyListByLines1.index(line), line.index(key))
                    self.getButtonByKey(key).setText(key)
                 
                    self.getButtonByKey(key).sigKeyButtonClicked.connect(lambda v=key: self.addInputByKey(v))
                  
                    self.keysLayout.setColumnMinimumWidth(keyIndex, 20)
                self.keysLayout.setRowMinimumHeight(lineIndex, 20)

            self.capsButton.setText('abc')
        else:

            self.log_q.put(["debug","VK",'Lower case Virtual keyboard enabled'])

            self.keyListByLines = [
                    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
                    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '_'],
                    ['z', 'x', 'c', 'v', 'b', 'n', 'm', '.', '|', '-'],
                ]
            for lineIndex, line in enumerate(self.keyListByLines):
                for keyIndex, key in enumerate(line):
                    buttonName = "keyButton" + key.capitalize()
                    self.__setattr__(buttonName, KeyButton(key))
                    self.keysLayout.addWidget(self.getButtonByKey(key), self.keyListByLines.index(line), line.index(key))
                    self.getButtonByKey(key).setText(key)
                 
                    self.getButtonByKey(key).sigKeyButtonClicked.connect(lambda v=key: self.addInputByKey(v))
                  
                    self.keysLayout.setColumnMinimumWidth(keyIndex, 20)
                self.keysLayout.setRowMinimumHeight(lineIndex, 20)
            self.capsButton.setText('ABC')

    def control(self):
        self.Control = not self.Control
        if self.Control == 1:
            self.capsButton.setEnabled(False)
            self.log_q.put(["debug","VK",'Control character Virtual keyboard enabled'])
            self.keyListByLines2 = [
                    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                    ['!', '@', '#', '$', '%', '^', '&&', '*', '(', ')'],
                    ['/', ';', ':', '[', ']', '{', '}', '<', '>', '?'],
                ]
            for lineIndex, line in enumerate(self.keyListByLines2):
                for keyIndex, key in enumerate(line):
                    buttonName = "keyButton" + key.capitalize()
                    self.__setattr__(buttonName, KeyButton(key))
                    self.keysLayout.addWidget(self.getButtonByKey(key), self.keyListByLines2.index(line), line.index(key))
                    self.getButtonByKey(key).setText(key)
                 
                    self.getButtonByKey(key).sigKeyButtonClicked.connect(lambda v=key: self.addInputByKey(v))
                  
                    self.keysLayout.setColumnMinimumWidth(keyIndex, 20)
                self.keysLayout.setRowMinimumHeight(lineIndex, 20)
            if self.capsButton.text() == 'ABC':
                self.controlButton.setText('abc')
            else:
                self.controlButton.setText('ABC')
                
        else:
            self.state = not self.state
            self.switchState()
            self.capsButton.setEnabled(True)
            self.controlButton.setText('123')
            
    def clearInput(self):
        self.inputString = ''
        self.inputLine.setText(self.inputString)

    def addInputByKey(self, key):
        self.inputString += (key.lower(), key.capitalize())[self.state]
        self.inputLine.setText(self.inputString)
        if self.password_flag:
            self.inputLine.setEchoMode(self.inputLine.Password)


    def backspace(self):
        self.log_q.put(["debug","VK",'BACKSPACE hit in Virtual Keyboard'])
        self.inputLine.backspace()
        self.inputString = self.inputString[:-1]

    def space(self):
        self.log_q.put(["debug","VK",'SPACE hit in Virtual Keyboard'])
        self.inputString += ' '
        self.inputLine.setText(self.inputString)

    def emitInputString(self, Line):
        self.log_q.put(["debug","VK",'Virtual Keyboard hidden after clicking OK']) 
        self.sigInputString.emit(self.inputLine.text())        
        Line = self.inputString
        self.close()

    def emitCancel(self):
        self.log_q.put(["warning","VK",'Virtual Keyboard hidden after clicking CANCEL'])       
        self.close()

    def sizeHint(self):
        return QtCore.QSize(150,200)
        