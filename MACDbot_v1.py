'''This bot uses the MACD to monitor price trends. Idea is that as the MACD continues to increase thus does the price'''

import urllib
import urllib.request
import urllib.error
import json
import time
import hmac,hashlib
import sched
import logging
from collections import deque
from datetime import datetime
from twython import Twython

#twitter stuff that im not using
APP_KEY = '3jNrvoIVHTka4hEhgs20PtpJA'
APP_SECRET = 'xLGnwxk1UUsC4zZuOxFY5icWQ9z6tOoc4FIGktAG3yqL3AkYKD'
OAUTH_TOKEN = '710962636914085889-pFhrrI2sQUns3APm1Vx70PckIbYWzeV'
OAUTH_TOKEN_SECRET = 'mrAa4LiElyKXbJbjrRGBzfn69wJoxrmEhsJP6CGJrCCDH'

#polo api key and secret needed:
API_KEY =
API_SECRET =

historicalLong = deque(maxlen=18)
historicalShort = deque(maxlen=7)
MACDHistoricalValues = deque(maxlen=9)
lastprice = 0
LongEMA = 0
ShortEMA = 0
MACD_EMA = 0
MACD_Histo = 0
HistoDelta = 0 #change in the MACD Histo
invested = False
initializationWindow = 0
timeout_counter = 0
tradeSpacer = 0
buyprice = 0
tickTimer = 900 #15 minutes
testBalance = 100

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
    global historicalLong
    global historicalShort
    global MACDHistoricalValues
    global lastprice
    global initializationWindow
    global tradeSpacer
    if(initializationWindow < 18):
        initializationWindow += 1
        if(initializationWindow == 17):
            print ("INITIALIZED!")
    ticker = poloniex.returnTicker()
    if(ticker):
        lastprice = float(ticker["BTC_ETH"]["last"])
        historicalShort.appendleft(lastprice)
        historicalLong.appendleft(lastprice)
    technicalCalculations()
    b = poloniex.returnBalances()
    orders = poloniex.returnOpenOrders('BTC_ETH')
    print("current ShortEMA = " + "{0:.7f}".format(ShortEMA) + " | current LongEMA = " + "{0:.7f}".format(LongEMA) + " | current MACD EMA = " + "{0:.7f}".format(MACD_EMA) + " | current Histo = " + "{0:.7f}".format(MACD_Histo) + " | current price: " + str(lastprice))
    if(orders): #if there are open orders suspend trading until they are filled.
        print("there are open orders, no trading")
        logging.info('waiting for orders to clear')
        return
    if(initializationWindow == 18):
        if(tradeSpacer == 0):
            tradeLogic(tw, b, poloniex)
        else:    
            if(tradeSpacer == 3):
                tradeSpacer = 0
                return
            tradeSpacer += 1
        
            
    
   
def technicalCalculations(): #calculates LongEMA, ShortEMA, MACD_Histo and MACD_EMA
    global LongEMA
    global ShortEMA
    global MACDHistoricalValues
    global MACD_EMA
    global MACD_Histo
    global HistoDelta
    K1 = 2/((len(historicalLong))+1)
    K2 = 2/((len(historicalShort))+1)
    K3 = 2/((len(MACDHistoricalValues))+1)
    #EMA = Exponential moving average - just an average of the last x prices with a weighting towards the most recent
    #Short EMA more closely reflects current price than long EMA
    LongEMA = (lastprice*K1)+(LongEMA*(1-K1))
    ShortEMA = (lastprice*K2)+(ShortEMA*(1-K2))
    OldMACD = MACD_Histo
    #MACD is the difference between the short and long EMA, Greater distance means the price is making a more dramatic move. 
    MACD_Histo = ShortEMA-LongEMA
    HistoDelta = MACD_Histo-OldMACD
    MACDHistoricalValues.appendleft(MACD_Histo)
    #MACD_EMA acts as a signal line to monitor the movement of the MACD
    MACD_EMA = (MACD_Histo*K3)+(MACD_EMA*(1-K3))
    

    
def tradeLogic(tw, balances, polo):
    global invested
    global tradeSpacer
    global buyprice
    global tickTimer
    global testBalance
    #When the MACD > MACD_EMA then that means the price has stopped going down and has begun an upward climb. good time to buy
    if((MACD_Histo>MACD_EMA) and invested == False and HistoDelta>0): #if positive crossover and we are not already invested, buy!
        print("BUY ETH NOW " + str(datetime.now().time()))
        amount = 0.14/lastprice #testing amount... aka dont risk all the btc
        #amount = float(balances['BTC'])/lastprice
        '''not using the buy and sell methods in testing'''
        #polo.buy('BTC_ETH',lastprice,float("{0:.5f}".format(amount)))
        logging.info('buying ETH now at ' + str(datetime.now().time()) + ' for ' + str(lastprice) + ' btc')
        buyprice = lastprice
        invested = True
    #Opposite of above. I use the HistoDelta variable to assure that it is a strong movement. I dont want to be tricked by a single weak period. 
    elif(((MACD_Histo<MACD_EMA) and invested == True)): #if negative crossover and we are invested, sell!
        print("SELL ETH NOW " + str(datetime.now().time()))
        percentageChange = (((lastprice-buyprice)/buyprice)*100)-0.3 #percentage change minus fees
        testBalance = testBalance + (testBalance*percentageChange/100)
        #polo.sell('BTC_ETH',lastprice,balances['ETH']) 
        logging.info('selling ETH now at ' + str(datetime.now().time()) + ' at ' + str(lastprice) + ' btc | percentage change = ' + str(percentageChange) + ' | new balance = ' + str(testBalance)) 
        invested = False
        tradeSpacer = 1

    
def main():
    #initialize stuff
    twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
    polo = poloniex(API_KEY, API_SECRET)
    s = sched.scheduler(time.time, time.sleep)
    logging.basicConfig(filename='trade.log', level=logging.INFO)
    logging.info('start logging at ' + str(datetime.now().time()))
    functionLoop(polo, s, twitter)
    
    
if __name__ == "__main__":
    main()