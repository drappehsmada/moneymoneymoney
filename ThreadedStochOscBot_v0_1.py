
'''Getting to the goodstuff now. This bot calculates the stochastic oscillator on the price data that it gets from the polo website
It also uses threading so that at anytime you can press 'b' or 's' to buy and sell respectively. Little more user control you know?

This one is actually probably the most effective bot so far in gauging price movement

BUG: This bot will work at first. then in about a day the "returnChartData" fucntion will begin to return all 0s I have no idea why but
its fucking annoying'''

import urllib
import urllib.request
import urllib.error
import json
import time
import hmac,hashlib
import sched
import logging
from collections import deque
import datetime
import calendar
from twython import Twython
import threading
import msvcrt

APP_KEY = '3jNrvoIVHTka4hEhgs20PtpJA'
APP_SECRET = 'xLGnwxk1UUsC4zZuOxFY5icWQ9z6tOoc4FIGktAG3yqL3AkYKD'
OAUTH_TOKEN = '710962636914085889-pFhrrI2sQUns3APm1Vx70PckIbYWzeV'
OAUTH_TOKEN_SECRET = 'mrAa4LiElyKXbJbjrRGBzfn69wJoxrmEhsJP6CGJrCCDH'

#insert key and secret here
POLO_API_KEY = 
POLO_SECRET = 

#globals
lastFourteenHigh = deque(maxlen=9)
lastFourteenLow = deque(maxlen=9)
KValueHistoricalValues = deque(maxlen=3)
currentDValue = 0
KValue = 0
lastPeriodHigh = 0
lastPeriodLow = 0
lastClose = 0
lastprice = 0
invested = False
initializationWindow = 0
timeout_counter = 0
tradeSpacer = 0
buyprice = 0
tickTimer = 300
testBalance = 100
unixTime = 0 

def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))

class poloniex:
    def __init__(self, APIKey, Secret):
        self.APIKey = APIKey
        self.Secret = Secret

    def post_process(self, before):
        after = before

        # Add timestamps if there isnt one but is a datetime
        if('return' in after):
            if(isinstance(after['return'], list)):
                for x in xrange(0, len(after['return'])):
                    if(isinstance(after['return'][x], dict)):
                        if('datetime' in after['return'][x] and 'timestamp' not in after['return'][x]):
                            after['return'][x]['timestamp'] = float(createTimeStamp(after['return'][x]['datetime']))
                            
        return after

    def api_query(self, command, req={}):
        global timeout_counter
        if(command == "returnTicker" or command == "return24Volume"):
            try:
                ret = urllib.request.urlopen(urllib.request.Request('https://poloniex.com/public?command=' + command))
                str_response = ret.read().decode('utf-8')
                timeout_counter = 0
                return json.loads(str_response)
            except Exception:
                print("time out error! try again!")
                timeout_counter+=1
                logging.info('just timed out, will try again. attempt number: ' + str(timeout_counter))
        elif(command == "returnOrderBook"):
            ret = urllib.request.urlopen(urllib.request.Request('http://poloniex.com/public?command=' + command + '&currencyPair=' + str(req['currencyPair'])))
            return json.loads(ret.read())
        elif(command == "returnMarketTradeHistory"):
            ret = urllib.request.urlopen(urllib.request.Request('http://poloniex.com/public?command=' + "returnTradeHistory" + '&currencyPair=' + str(req['currencyPair'])))
            return json.loads(ret.read())
        else:
            req['command'] = command
            req['nonce'] = int(time.time()*1000)
            post_data = urllib.parse.urlencode(req)
            binary_data = post_data.encode('utf-8')

            sign = hmac.new(self.Secret, post_data, hashlib.sha512).hexdigest()
            headers = {
                'Sign': sign,
                'Key': self.APIKey
            }
            try:
                ret = urllib.request.urlopen(urllib.request.Request('https://poloniex.com/tradingApi', binary_data, headers))
                str_response = ret.read().decode('utf-8')
                jsonRet = json.loads(str_response)
                timeout_counter = 0
                return self.post_process(jsonRet)
            except Exception:
                print("time out error! try again!")
                timeout_counter+=1
                logging.info('just timed out, will try again. attempt number: ' + str(timeout_counter))


    def returnTicker(self):
        return self.api_query("returnTicker")

    def return24Volume(self):
        return self.api_query("return24Volume")
        
    def returnChartData(self):
        global timeout_counter
        global unixTime
        startTime = datetime.datetime.utcnow() + datetime.timedelta(minutes=-5)
        unixTime = calendar.timegm(startTime.utctimetuple())
        startunixTime = int(unixTime)+300
        try:
            ret = urllib.request.urlopen(urllib.request.Request('https://poloniex.com/public?command=returnChartData&currencyPair=BTC_ETH&start=' + str(unixTime-1) + '&end=' + str(startunixTime) + '&period=' + str(300)))
            str_response = ret.read().decode('utf-8')
            timeout_counter = 0
            return json.loads(str_response)
        except Exception:
            print("time out error! try again!")
            timeout_counter+=1
            logging.info('just timed out, will try again. attempt number: ' + str(timeout_counter))

    def returnOrderBook (self, currencyPair):
        return self.api_query("returnOrderBook", {'currencyPair': currencyPair})

    def returnMarketTradeHistory (self, currencyPair):
        return self.api_query("returnMarketTradeHistory", {'currencyPair': currencyPair})


    # Returns all of your balances.
    # Outputs: 
    # {"BTC":"0.59098578","LTC":"3.31117268", ... }
    def returnBalances(self):
        return self.api_query('returnBalances')

    # Returns your open orders for a given market, specified by the "currencyPair" POST parameter, e.g. "BTC_XCP"
    # Inputs:
    # currencyPair  The currency pair e.g. "BTC_XCP"
    # Outputs: 
    # orderNumber   The order number
    # type          sell or buy
    # rate          Price the order is selling or buying at
    # Amount        Quantity of order
    # total         Total value of order (price * quantity)
    def returnOpenOrders(self,currencyPair):
        return self.api_query('returnOpenOrders',{"currencyPair":currencyPair})


    # Returns your trade history for a given market, specified by the "currencyPair" POST parameter
    # Inputs:
    # currencyPair  The currency pair e.g. "BTC_XCP"
    # Outputs: 
    # date          Date in the form: "2014-02-19 03:44:59"
    # rate          Price the order is selling or buying at
    # amount        Quantity of order
    # total         Total value of order (price * quantity)
    # type          sell or buy
    def returnTradeHistory(self,currencyPair):
        return self.api_query('returnTradeHistory',{"currencyPair":currencyPair})

    # Places a buy order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If successful, the method will return the order number.
    # Inputs:
    # currencyPair  The curreny pair
    # rate          price the order is buying at
    # amount        Amount of coins to buy
    # Outputs: 
    # orderNumber   The order number
    def buy(self,currencyPair,rate,amount):
        return self.api_query('buy',{"currencyPair":currencyPair,"rate":rate,"amount":amount})

    # Places a sell order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If successful, the method will return the order number.
    # Inputs:
    # currencyPair  The curreny pair
    # rate          price the order is selling at
    # amount        Amount of coins to sell
    # Outputs: 
    # orderNumber   The order number
    def sell(self,currencyPair,rate,amount):
        return self.api_query('sell',{"currencyPair":currencyPair,"rate":rate,"amount":amount})

    # Cancels an order you have placed in a given market. Required POST parameters are "currencyPair" and "orderNumber".
    # Inputs:
    # currencyPair  The curreny pair
    # orderNumber   The order number to cancel
    # Outputs: 
    # succes        1 or 0
    def cancel(self,currencyPair,orderNumber):
        return self.api_query('cancelOrder',{"currencyPair":currencyPair,"orderNumber":orderNumber})

    # Immediately places a withdrawal for a given currency, with no email confirmation. In order to use this method, the withdrawal privilege must be enabled for your API key. Required POST parameters are "currency", "amount", and "address". Sample output: {"response":"Withdrew 2398 NXT."} 
    # Inputs:
    # currency      The currency to withdraw
    # amount        The amount of this coin to withdraw
    # address       The withdrawal address
    # Outputs: 
    # response      Text containing message about the withdrawal
    def withdraw(self, currency, amount, address):
        return self.api_query('withdraw',{"currency":currency, "amount":amount, "address":address})
                
        
def functionLoop(poloniex, sched, tw):
    sc = sched
    while True: #run forever
        sc.enter(tickTimer,1,tick, (poloniex, tw,))
        sc.run()
  
def tick(poloniex, tw):
    global lastFourteenHigh
    global lastFourteenLow
    global lastprice
    global lastPeriodHigh
    global lastPeriodLow
    global lastClose
    global initializationWindow
    global tradeSpacer
    if(initializationWindow < 9):
        initializationWindow += 1
        if(initializationWindow == 9):
            print ("INITIALIZED!")
    ticker = poloniex.returnTicker()
    chartData = poloniex.returnChartData() #get chart data 
    if(chartData):
        print(chartData)
        #print(str(unixTime-1) + " " + str(unixTime+300) + " " + str(calendar.timegm(datetime.datetime.utcnow().utctimetuple())))
        lastPeriodHigh = chartData[0]['high']
        lastPeriodLow = chartData[0]['low']
        lastClose = chartData[0]['close']
        lastFourteenHigh.appendleft(lastPeriodHigh)
        lastFourteenLow.appendleft(lastPeriodLow)
    if(ticker):
        lastprice = float(ticker["BTC_ETH"]["last"])
    technicalCalculations()
    b = poloniex.returnBalances()
    orders = poloniex.returnOpenOrders('BTC_ETH')
    print("Last Period High = " + str(lastPeriodHigh) + " | last Period Low = " + str(lastPeriodLow) + " | %K Value = " + str(KValue) + " | %D Value = " + str(currentDValue) + " | Last Close: " + str(lastClose))
    if(orders): #if there are open orders suspend trading until they are filled.
        print("there are open orders, no trading")
        logging.info('waiting for orders to clear')
        return
    if(initializationWindow == 9):
        if(tradeSpacer == 0):
            tradeLogic(tw, b, poloniex)
        else:    
            if(tradeSpacer == 3):
                tradeSpacer = 0
                return
            tradeSpacer += 1
        
            
    
#the stochastic oscillator works on the principal that when price is moving up, it tends to close near the high point of the period,
#when it is moving down, it closes near the bottom. The K value is a representation of that. the D value is a short EMA that follows the K value
#we use crossovers as a signal to buy or sell. 

#Also, a value over 80 is considered over bought and means the price is likely to go down soon. A value below 20 is the opposite.    
def technicalCalculations(): 
    global KValue
    global currentDValue
    lowestLow = min(lastFourteenLow)
    highestHigh = max(lastFourteenHigh)
    #if(lowestLow == 0):
    #    print (str(unixTime))
    if((highestHigh - lowestLow) != 0):
        KValue = 100*((lastClose-lowestLow)/(highestHigh-lowestLow))
        KValueHistoricalValues.appendleft(KValue)
        currentDValue = sum(KValueHistoricalValues)/len(KValueHistoricalValues)
    #    print("\thighest high: " + str(highestHigh) + " | lowest low: " + str(lowestLow))
    

    
def tradeLogic(tw, balances, polo):
    global invested
    global tradeSpacer
    global buyprice
    global tickTimer
    global testBalance
    if((currentDValue<KValue) and invested == False and currentDValue < 20): 
        print("BUY ETH NOW " + str(datetime.datetime.now().time()))
        #amount = 0.14/lastprice #testing amount... aka dont risk all the btc
        #amount = float(balances['BTC'])/lastprice
        #polo.buy('BTC_ETH',lastprice,float("{0:.5f}".format(amount)))
        logging.info('buying ETH now at ' + str(datetime.datetime.now().time()) + ' for ' + str(lastprice) + ' btc')
        buyprice = lastprice
        invested = True
    elif((currentDValue>KValue) and invested == True and currentDValue > 70 and KValue < 93): 
        print("SELL ETH NOW " + str(datetime.datetime.now().time()))
        percentageChange = (((lastprice-buyprice)/buyprice)*100)-0.3 #percentage change minus fees
        testBalance = testBalance + (testBalance*percentageChange/100)
        #polo.sell('BTC_ETH',lastprice,balances['ETH']) 
        logging.info('selling ETH now at ' + str(datetime.datetime.now().time()) + ' at ' + str(lastprice) + ' btc | percentage change = ' + str(percentageChange) + ' | new balance = ' + str(testBalance)) 
        invested = False
        tradeSpacer = 1

#perform a buy action outside of the normal schedule
def user_directed_buy():
    global invested
    global buyprice
    global testBalance
    if(invested == False):
        polo = poloniex(POLO_API_KEY, POLO_SECRET)
        ticker = polo.returnTicker()
        if(ticker):
            lastprice = float(ticker["BTC_ETH"]["last"])
            print("USER DIRECTED BUY")
            logging.info('User directed buy at ' + str(datetime.datetime.now().time()) + ' for ' + str(lastprice) + ' btc')
            buyprice = lastprice
            invested = True
        else:
            print("could not return ticker please try again")
    else:
        print("already invested, sell first")

#perform a sell action outside of normal schedule         
def user_directed_sell():
    global invested
    global buyprice
    global testBalance
    if(invested == True):
        polo = poloniex(POLO_API_KEY, POLO_SECRET)
        ticker = polo.returnTicker()
        if(ticker):
            lastprice = float(ticker["BTC_ETH"]["last"])
            percentageChange = (((lastprice-buyprice)/buyprice)*100)-0.3 #percentage change minus fees
            testBalance = testBalance + (testBalance*percentageChange/100)
            print("USER DIRECTED SELL")
            logging.info('User directed sell at ' + str(datetime.datetime.now().time()) + ' at ' + str(lastprice) + ' btc | percentage change = ' + str(percentageChange) + ' | new balance = ' + str(testBalance))
            buyprice = lastprice
            invested = False
        else:
            print("could not return ticker please try again")
    else:
        print("not invested, buy first")

        
def process_user_input(key):
    if (key == b'b'):
        user_directed_buy()
    elif(key == b's'):
        user_directed_sell()
    elif(key == b'x'):
        print("exiting")
        exit('leaving thread')
        
def key_capturing():
    #loop forever waiting for input
    while True:
        process_user_input(msvcrt.getch())
    
def main():
    userThread = threading.Thread(target=key_capturing).start() #start thread
    twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
    polo = poloniex(POLO_API_KEY, POLO_SECRET)
    s = sched.scheduler(time.time, time.sleep)
    logging.basicConfig(filename='trade.log', level=logging.INFO)
    logging.info('start logging at ' + str(datetime.datetime.now().time()))
    functionLoop(polo, s, twitter)
    
    
if __name__ == "__main__":
    main()