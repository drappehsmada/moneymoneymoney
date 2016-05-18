
'''My baby so far lol. Highly recommend downloading pyQt to run it. Need to have BotUI.py and polo_api.py in same folder to run.
Just a stochastic oscillator like the threadedStochOscBot but without the buggy api call. This one uses a thread to get the realtime price ticker.
By monitoring that it constructs its own price data. '''

import sys
from PyQt4 import QtCore, QtGui
from BotUI import Ui_MainWindow
from polo_api import poloniex
from autobahn.asyncio.wamp import ApplicationSession
from autobahn.asyncio.wamp import ApplicationRunner
from asyncio import coroutine
import asyncio
import re
import threading
import msvcrt
import logging
import sched
import time
import datetime
from collections import deque

#insert polo key and secret here
POLO_API_KEY = 
POLO_SECRET = 


wnd = 0
highValue = 0
lowValue = 1 #will need to be changed if ETH is ever worth more than 1 BTC lol
open = 0
close = 0

def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))

#GUI class
class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent = None):
        super (MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.QuitButton.clicked.connect(QtCore.QCoreApplication.instance().quit)

#Application class, where all the processing happens        
class App(QtCore.QObject):
    
    lastFourteenHigh = deque(maxlen=9)
    lastFourteenLow = deque(maxlen=9)
    KValueHistoricalValues = deque(maxlen=3)
    currentDValue = 0
    KValue = 0
    invested = False
    buyprice = 0
    testBalance = 100
    initializationWindow = 0
    lifetimePercentChange = 0.0
    tradeFlag = False
    
    def __init__(self):
        global wnd
        QtCore.QObject.__init__(self)
        self.sc = PeriodScheduler(self)
        self.t = QtCore.QThread()
        self.sc.moveToThread(self.t)
        self.sc.updateBot.connect(self.updateValues)
        self.t.started.connect(self.sc.startSchedulerFunct)
        self.t.start()
        wnd.ui.BalanceVal.setText(str(self.testBalance))
        wnd.ui.P_LVal.setText(str(self.lifetimePercentChange))
        wnd.ui.BuyButton.clicked.connect(self.userDirectedBuy)
        wnd.ui.pushButton_3.clicked.connect(self.userDirectedSell)


        
    def updateValues(self):
        global open
        global close
        global highValue
        global lowValue
        global wnd
        wnd.ui.OpenVal.setText(str(open))
        wnd.ui.CloseVal.setText(str(close))
        wnd.ui.HighVal.setText(str(highValue))
        wnd.ui.LowVal.setText(str(lowValue))
        self.lastFourteenHigh.appendleft(highValue)
        self.lastFourteenLow.appendleft(lowValue)
        self.technicalCalculations()
        if(self.initializationWindow < 9):
            self.initializationWindow += 1
            if(self.initializationWindow == 9):
                wnd.ui.Log_field.appendPlainText("Initialized at: " + str(datetime.datetime.now().time()))
        else:
            self.tradeLogic()
        if(self.lifetimePercentChange > 0):
            wnd.ui.P_LVal.setStyleSheet("color: rgb(0, 255, 0)")
        elif(self.lifetimePercentChange < 0):
            wnd.ui.P_LVal.setStyleSheet("color: rgb(255, 0, 0)")
        wnd.ui.P_LVal.setText(str(self.lifetimePercentChange))
        wnd.ui.BalanceVal.setText(str(self.testBalance))
        #if(self.tradeFlag == True):
        #    wnd.ui.K_field.setStyleSheet("font-weight: bold")
        #if(self.tradeFlag == False):
        #    wnd.ui.K_field.setStyleSheet("font-weight: normal")
        wnd.ui.Close_field.appendPlainText(str("{0:.8f}".format(close)))
        wnd.ui.K_field.appendPlainText(str("{0:.7f}".format(self.KValue)))
        wnd.ui.D_field.appendPlainText(str("{0:.7f}".format(self.currentDValue)))
        open = 0
        close = 0
        highValue = 0
        lowValue = 1
        
    def technicalCalculations(self):
        lowestLow = min(self.lastFourteenLow)
        highestHigh = max(self.lastFourteenHigh)
        if((highestHigh - lowestLow) != 0):
            self.KValue = 100*((close-lowestLow)/(highestHigh-lowestLow))
            self.KValueHistoricalValues.appendleft(self.KValue)
            self.currentDValue = sum(self.KValueHistoricalValues)/len(self.KValueHistoricalValues)
    
    def tradeLogic(self):
        polo = poloniex(POLO_API_KEY, POLO_SECRET)
        b = polo.returnBalances()
        if((self.currentDValue<self.KValue) and self.invested == False and self.currentDValue < 40): #if positive crossover and we are not already invested, buy!
            wnd.ui.Log_field.appendPlainText(str(datetime.datetime.now().time()) + " BUY | PRICE: " + str(close))
            print("BUY ETH NOW " + str(datetime.datetime.now().time()))
            #amount = 0.14/lastprice #testing amount... aka dont risk all the btc
            #amount = float(balances['BTC'])/lastprice
            #polo.buy('BTC_ETH',lastprice,float("{0:.5f}".format(amount)))
            logging.info('buying ETH now at ' + str(datetime.datetime.now().time()) + ' for ' + str(close) + ' btc')
            self.buyprice = close
            self.invested = True
         #   self.tradeFlag = True
        elif((self.currentDValue>self.KValue) and self.invested == True and self.currentDValue > 70 and self.KValue < 93): #if negative crossover and we are invested, sell!
            print("SELL ETH NOW " + str(datetime.datetime.now().time()))
            percentageChange = (((close-self.buyprice)/self.buyprice)*100)-0.3 #percentage change minus fees
            self.testBalance = self.testBalance + (self.testBalance*percentageChange/100)
            self.lifetimePercentChange = ((self.testBalance-100)/100)*100
            #if(percentageChange < -0.8):
            #    polo.sell('BTC_ETH',buyprice,balances['ETH']) 
            #    logging.info('selling ETH now at ' + str(datetime.now().time()) + ' at ' + str(buyprice) + ' btc | percentage change = fees')
            #else:
            #polo.sell('BTC_ETH',lastprice,balances['ETH']) 
            wnd.ui.Log_field.appendPlainText(str(datetime.datetime.now().time()) + " SELL | PRICE: " + str(close))
            logging.info('selling ETH now at ' + str(datetime.datetime.now().time()) + ' at ' + str(close) + ' btc | percentage change = ' + str(percentageChange) + ' | new balance = ' + str(self.testBalance)) 
            self.invested = False
         #   self.tradeFlag = True
        
    def userDirectedSell(self):
        if(self.invested == True):
            print("SELL ETH NOW " + str(datetime.datetime.now().time()))
            percentageChange = (((close-self.buyprice)/self.buyprice)*100)-0.3 #percentage change minus fees
            self.testBalance = self.testBalance + (self.testBalance*percentageChange/100)
            self.lifetimePercentChange = ((self.testBalance-100)/100)*100
            wnd.ui.Log_field.appendPlainText(str(datetime.datetime.now().time()) + " SELL | PRICE: " + str(close))
            logging.info('selling ETH now at ' + str(datetime.datetime.now().time()) + ' at ' + str(close) + ' btc | percentage change = ' + str(percentageChange) + ' | new balance = ' + str(self.testBalance)) 
            self.invested = False
        else:
            wnd.ui.Log_field.appendPlainText(str(datetime.datetime.now().time()) + " Not invested yet, buy first")
            
    def userDirectedBuy(self):
        if(self.invested == False):
            wnd.ui.Log_field.appendPlainText(str(datetime.datetime.now().time()) + " USER DIRECTED BUY | PRICE: " + str(close))
            print("BUY ETH NOW " + str(datetime.datetime.now().time()))
            logging.info('User directed BUY at ' + str(datetime.datetime.now().time()) + ' for ' + str(close) + ' btc')
            self.buyprice = close
            self.invested = True
        else:
            wnd.ui.Log_field.appendPlainText(str(datetime.datetime.now().time()) + " Already invested, sell first")

#scheduler class. All it does is send a signal back to the application every 5 minutes so that it updates.            
class PeriodScheduler(QtCore.QThread):
    
    updateBot = QtCore.pyqtSignal()
    
    def __init__(self, parent):
        QtCore.QThread.__init__(self)
        #parent.startScheduler.connect(self.startSchedulerFunct)
        
    def SendUpdateValues(self):
        self.updateBot.emit() #send signal back up to main thread
     
    def startSchedulerFunct(self):
        print ("starting scheduler")
        s = sched.scheduler(time.time, time.sleep)
        while True:
            s.enter(300,1,self.SendUpdateValues,)
            s.run()

#ticker class, monitors the realtime polo api for price changes.            
class PriceTicker(ApplicationSession):
    def onConnect(self):
        self.join(self.config.realm)
        
    def onLeave(self, details):
        print("disconnecting!")
        self.disconnect()
    
    def onDisconnect(self):
        try:
            loop = asyncio.get_event_loop()
            loop.stop()
        except Exception as e:
            logging.exception("message")
    
    @coroutine
    def onJoin(self, details):
        def onTicker(*args):
            global wnd
            global open
            global close
            global highValue
            global lowValue
            msg = args[0]
            if 'BTC_ETH' in msg:
                #print(args)
                try:
                    wnd.ui.LastVal.setText(str(args[1]))
                    close = float(args[1])
                    if(open == 0):
                        open = float(args[1])
                    if(float(args[1])>highValue):
                        highValue = float(args[1])
                    if(float(args[1])<lowValue):
                        lowValue = float(args[1])    
                        
                except Exception as e:
                    logging.exception(e)
        try:
            self.subscription = yield from self.subscribe(onTicker, 'ticker')
        except Exception as e:
            print("Could not subscribe to topic:", e)        
 


#thread the ticker runs in  
def tickerThread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ticker = ApplicationRunner("wss://api.poloniex.com:443", "realm1")
    ticker.run(PriceTicker)


#start the ticker thread. Space for other threads    
def setupThreads():
    t_thread = threading.Thread(target=tickerThread)
    t_thread.daemon = True
    t_thread.start()

    
def main():
    global wnd
    logging.basicConfig(filename='debug.log', level=logging.INFO)
    logging.info('start logging at ' + str(datetime.datetime.now().time()))
    app = QtGui.QApplication(sys.argv) #code that im not sure what it does just has to be there lol
    wnd = MainWindow() #set up Gui
    setupThreads() #start Ticker
    wnd.show() #show gui
    a = App() #start application
    wnd.ui.Log_field.appendPlainText("Begin trading at " + str(datetime.datetime.now().time())) #log the start time
    sys.exit(app.exec_())
    
    
if __name__ == '__main__':
    main()