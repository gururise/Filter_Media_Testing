from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtCore import pyqtSignal
import sys
import json
import time
import paho.mqtt.client as mqtt

USERNAME = "username"
PASSWORD = "password"
SERVER = "mqtt_server"
TOPIC = "sensors/pmsensor/count"
PORT = 1883

class Ui(QtWidgets.QMainWindow):
    valChange = pyqtSignal(object, name='valChanged')

    def __init__(self):
        # Call the inherited classes __init__ method
        super(Ui, self).__init__()
        uic.loadUi('main.ui', self)  # Load the .ui file

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(USERNAME, password=PASSWORD)
        self.client.connect_async(SERVER, PORT, 60)
        self.last_update = time.time()

        self.textUpdateFreq = self.findChild(QtWidgets.QPlainTextEdit, 'ufPlainTextEdit')
        self.textTopic = self.findChild(QtWidgets.QPlainTextEdit, 'plainTextEdit')
        self.textTopic.document().setPlainText(TOPIC)
        
        # ButtonsFind the button with the name "connectButton"
        self.button = self.findChild(QtWidgets.QPushButton, 'connectButton')
        self.button.clicked.connect(self.connectButtonPressed)
        self.resetButton = self.findChild(QtWidgets.QPushButton, 'resetButton')
        self.resetButton.clicked.connect(self.resetButtonPressed)

        self.freezeCheck = self.findChild(QtWidgets.QCheckBox, 'freeze_checkBox')
        self.freezeCheck.stateChanged.connect(self.freezeChecked)
        self.valChange.connect(self.handle_change)

        # Realtime Display PB
        self.lcd0_3 = self.findChild(QtWidgets.QLCDNumber, 'lcd0_3')
        self.lcd0_5 = self.findChild(QtWidgets.QLCDNumber, 'lcd0_5')
        self.lcd1_0 = self.findChild(QtWidgets.QLCDNumber, 'lcd1_0')
        self.lcd2_5 = self.findChild(QtWidgets.QLCDNumber, 'lcd2_5')
        self.lcd5_0 = self.findChild(QtWidgets.QLCDNumber, 'lcd5_0')
        self.lcd_10 = self.findChild(QtWidgets.QLCDNumber, 'lcd_10')

        # EMA Display PB
        self.lcd0_3a = self.findChild(QtWidgets.QLCDNumber, 'lcd0_3a')
        self.lcd0_5a = self.findChild(QtWidgets.QLCDNumber, 'lcd0_5a')
        self.lcd1_0a = self.findChild(QtWidgets.QLCDNumber, 'lcd1_0a')
        self.lcd2_5a = self.findChild(QtWidgets.QLCDNumber, 'lcd2_5a')
        self.lcd5_0a = self.findChild(QtWidgets.QLCDNumber, 'lcd5_0a')
        self.lcd_10a = self.findChild(QtWidgets.QLCDNumber, 'lcd_10a')

        self.lcd_pm1 = self.findChild(QtWidgets.QLCDNumber, 'lcd_pm1')
        self.lcd_pm10 = self.findChild(QtWidgets.QLCDNumber, 'lcd_pm10')
        self.lcd_pm25 = self.findChild(QtWidgets.QLCDNumber, 'lcd_pm25')

        self.pData = []
        for idx in range(6):
            self.pData.append([])

        self.show()  # Show the GUI
    
    def calc_ema(self, s, n):
        """
        returns an n period exponential moving average for
        the time series s

        s is a list ordered from oldest (index 0) to most
        recent (index -1)
        n is an integer

        returns a numeric array of the exponential
        moving average
        """
        #s = array(s)
        ema = []
        j = 1

        #get n sma first and calculate the next n period ema
        sma = sum(s[:n]) / n
        multiplier = 2 / float(1 + n)
        ema.append(sma)

        #EMA(current) = ( (Price(current) - EMA(prev) ) x Multiplier) + EMA(prev)
        ema.append(((s[n] - sma) * multiplier) + sma)

        #now calculate the rest of the values
        for i in s[n+1:]:
            tmp = ((i - ema[j]) * multiplier) + ema[j]
            j = j + 1
            ema.append(tmp)
        return ema

    def freezeChecked(self, state):
        if state:
            self.valChange.disconnect()
        else:
            self.valChange.connect(self.handle_change)


    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        print("Subscribed to topic: " + self.textTopic.document().toPlainText())

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        #client.subscribe("seapine/upstairs/tasmota_A860E1/tele/SENSOR")
        client.subscribe(self.textTopic.document().toPlainText(),0)

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        #print(msg.payload)
        print(msg.topic+" "+str(msg.payload.decode('utf-8')))
        obj = json.loads(msg.payload)
        self.valChange.emit(obj)
        '''
        self.pData[0].append(int(obj['PMS']['B03']))
        self.pData[1].append(int(obj['PMS']['B05']))
        self.pData[2].append(int(obj['PMS']['B1']))
        self.pData[3].append(int(obj['PMS']['B25']))
        self.pData[4].append(int(obj['PMS']['B5']))
        self.pData[5].append(int(obj['PMS']['B10']))
        # display real-time values for PB
        self.lcd0_3.display(self.pData[0][len(self.pData[0])-1])
        self.lcd0_5.display(self.pData[1][len(self.pData[1])-1])
        self.lcd1_0.display(self.pData[2][len(self.pData[2])-1])
        self.lcd2_5.display(self.pData[3][len(self.pData[3])-1])
        self.lcd5_0.display(self.pData[4][len(self.pData[4])-1])
        self.lcd_10.display(self.pData[5][len(self.pData[5])-1])

        #self.pData.append([])
        ema = []
        for idx in range(6):
            ema.append([])

        if (len(self.pData) > 15):
            for idx in range(6):
                ema[idx] = self.calc_ema(self.pData[idx], 15)
            self.lcd0_3a.display(ema[0][len(ema[0])-1])
            self.lcd0_5a.display(ema[1][len(ema[1])-1])
            self.lcd1_0a.display(ema[2][len(ema[2])-1])
            self.lcd2_5a.display(ema[3][len(ema[3])-1])
            self.lcd5_0a.display(ema[4][len(ema[4])-1])
            self.lcd_10a.display(ema[5][len(ema[5])-1])
        else:
            self.lcd0_3a.display(self.pData[0][len(self.pData[0])-1])
            self.lcd0_5a.display(self.pData[1][len(self.pData[1])-1])
            self.lcd1_0a.display(self.pData[2][len(self.pData[2])-1])
            self.lcd2_5a.display(self.pData[3][len(self.pData[3])-1])
            self.lcd5_0a.display(self.pData[4][len(self.pData[4])-1])
            self.lcd_10a.display(self.pData[5][len(self.pData[5])-1])

        if (len(self.pData) > 60):
            for idx in range(6):
                del self.pData[idx][0]

        self.lcd_pm1.display(int(obj['PMS']['P1']))
        self.lcd_pm25.display(int(obj['PMS']['P25']))
        self.lcd_pm10.display(int(obj['PMS']['P10']))

        hz = 1/(time.time() - self.last_update)
        self.textUpdateFreq.document().setPlainText("{0:.3f}".format(hz) + " Hz")
        self.last_update = time.time()
        '''

    def handle_change(self, obj):
        self.pData[0].append(int(obj['PMS']['B03']))
        self.pData[1].append(int(obj['PMS']['B05']))
        self.pData[2].append(int(obj['PMS']['B1']))
        self.pData[3].append(int(obj['PMS']['B25']))
        self.pData[4].append(int(obj['PMS']['B5']))
        self.pData[5].append(int(obj['PMS']['B10']))
        # display real-time values for PB

        self.lcd0_3.display(self.pData[0][len(self.pData[0])-1])
        self.lcd0_5.display(self.pData[1][len(self.pData[1])-1])
        self.lcd1_0.display(self.pData[2][len(self.pData[2])-1])
        self.lcd2_5.display(self.pData[3][len(self.pData[3])-1])
        self.lcd5_0.display(self.pData[4][len(self.pData[4])-1])
        self.lcd_10.display(self.pData[5][len(self.pData[5])-1])
        
        ema = []
        for idx in range(6):
            ema.append([])

        if (len(self.pData[0]) > 30):
            for idx in range(6):
                ema[idx] = self.calc_ema(self.pData[idx], 30)
            print(ema)
            self.lcd0_3a.display(ema[0][len(ema[0])-1])
            self.lcd0_5a.display(ema[1][len(ema[1])-1])
            self.lcd1_0a.display(ema[2][len(ema[2])-1])
            self.lcd2_5a.display(ema[3][len(ema[3])-1])
            self.lcd5_0a.display(ema[4][len(ema[4])-1])
            self.lcd_10a.display(ema[5][len(ema[5])-1])
        else:
            self.lcd0_3a.display(self.pData[0][len(self.pData[0])-1])
            self.lcd0_5a.display(self.pData[1][len(self.pData[1])-1])
            self.lcd1_0a.display(self.pData[2][len(self.pData[2])-1])
            self.lcd2_5a.display(self.pData[3][len(self.pData[3])-1])
            self.lcd5_0a.display(self.pData[4][len(self.pData[4])-1])
            self.lcd_10a.display(self.pData[5][len(self.pData[5])-1])

        if (len(self.pData[0]) > 60):
            for idx in range(6):
                del self.pData[idx][0]

        self.lcd_pm1.display(int(obj['PMS']['P1']))
        self.lcd_pm25.display(int(obj['PMS']['P25']))
        self.lcd_pm10.display(int(obj['PMS']['P10']))

        hz = 1/(time.time() - self.last_update)
        self.textUpdateFreq.document().setPlainText(
            "{0:.3f}".format(hz) + " Hz")
        self.last_update = time.time()

    def quit(self):
        self.commTerminate()
        self.client.loop_stop()
        self.client.disconnect()
        QtWidgets.QApplication.quit()

    def connectButtonPressed(self):
        # connect button has been pressed
        print("connectButtonPressed")
        self.button.setEnabled(False)

        self.client.loop_start()
    
    def resetButtonPressed(self):
        self.pData.clear()
        for idx in range(6):
            self.pData.append([])



# Create an instance of QtWidgets.QApplication
app = QtWidgets.QApplication(sys.argv)

window = Ui()  # Create an instance of our class
app.exec_()  # Start the application
