#!/usr/bin/env python3
# encoding:utf-8
import os
import sys
import threading
from Ui import Ui_Form
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer

class MainWindow(QWidget, Ui_Form):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        
        self.locale_path = '/etc/default/locale'
        self.locale_tmp = '/home/pi/locale'
        self.cmd = 'sudo locale-gen'

        self.current_language = ''
        self.start_value = 0
        self.finish = False

        self.pushButton_chinese.clicked.connect(lambda: self.button_clicked('chinese'))
        self.pushButton_english.clicked.connect(lambda: self.button_clicked('english'))
        
    def message_confirm(self, string):
        messageBox = QMessageBox()
        messageBox.setWindowTitle(' ')
        messageBox.setText(string)
        messageBox.addButton(QPushButton('OK'), QMessageBox.YesRole)
        messageBox.addButton(QPushButton('Cancel'), QMessageBox.NoRole)

        return messageBox.exec_() 
    
    def schedule(self):
        self.bar.setValue(self.start_value)
        if self.start_value < 99 and not self.finish:
            self.start_value += 1
        if self.finish:
            self.start_value = 0
            self.finish = False
            self.bar.setValue(100)
            self.timer.stop()
            self.bar.close()
            if self.current_language == 'zh':
                result = self.message_confirm('设置完成，重启后生效, 立刻重启？')
                if result == 0:
                    os.system('sudo reboot')
            else:
                result = self.message_confirm('Setup complete, it will take effect after restart, reboot now?')
                if result == 0:
                    os.system('sudo reboot')

    def button_clicked(self, name):
        result = 1
        if name == 'chinese':
            self.current_language = 'zh'
            result = self.message_confirm('确定?')
        else:
            self.current_language = 'en'
            result = self.message_confirm('sure?')
        
        if result == 0:
            self.bar = QProgressDialog(self)
            self.bar.setMinimum(0)
            self.bar.setMaximum(100)
            self.bar.setValue(self.start_value)
            
            self.timer = QTimer()
            self.timer.timeout.connect(self.schedule)
            self.timer.start(140)
            
            if self.current_language == 'zh':
                threading.Thread(target=self.write_data, args=('''LANG=zh_CN.UTF-8
LANGUAGE=zh_CN.UTF-8''',), daemon=True).start()
            else:
                threading.Thread(target=self.write_data, args=('''LANG=en_US.UTF-8
LANGUAGE=en_US.UTF-8''',), daemon=True).start()
        
    def write_data(self, data):

        f = open(self.locale_tmp, 'w')
        f.write(data)
        f.close()
        os.system('sudo mv ' + self.locale_tmp + ' ' + self.locale_path)
        os.system(self.cmd)
        self.finish = True

if __name__ == "__main__":  
    app = QApplication(sys.argv)
    myshow = MainWindow()
    myshow.show()
    sys.exit(app.exec_())
