
'''My first bot, calculates Short EMA (exponential moving average) and Long SMA (simple moving average),
Idea is that when the EMA crosses the SMA a trade signal is initiated - a cross above means increasing trend
a cross below means decreasing trend. This works in the long term, but kinda falls apart for short term trading. 
the price is too volatile.'''


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

#twitter stuff
APP_KEY = '3jNrvoIVHTka4hEhgs20PtpJA'
APP_SECRET = 'xLGnwxk1UUsC4zZuOxFY5icWQ9z6tOoc4FIGktAG3yqL3AkYKD'
OAUTH_TOKEN = '710962636914085889-pFhrrI2sQUns3APm1Vx70PckIbYWzeV'
OAUTH_TOKEN_SECRET = 'mrAa4LiElyKXbJbjrRGBzfn69wJoxrmEhsJP6CGJrCCDH'

#insert key+secret to make go
API_KEY =
API_SECRET =

#globals
historicalValues25 = deque(maxlen=20)
historicalValues10 = deque(maxlen=10)
lastprice = 0
currentSMA = 0
currentEMA = 0
invested = False
initializationWindow = 0
timeout_counter = 0
buyprice = 0
tickTime = 300 #length of each period (seconds)
testBalance = 100 #testing balance, lets give it 100


def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))

#polo api in a nice python wrapper    
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
                return json.loads(str_response)
                timeout_counter = 0
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
        sc.enter(tickTime,1,tick, (poloniex, tw,))
        sc.run()
  
def tick(poloniex, tw):
    global historicalValues25
    global historicalValues10
    global lastprice
    global initializationWindow
    #initialization is 20 periods (length of long sma)
    if(initializationWindow < 20):
        initializationWindow += 1
        if(initializationWindow == 19):
            print ("INITIALIZED!")
    #get latest price data from web - returns JSON
    ticker = poloniex.returnTicker()
    if(ticker):
        lastprice = float(ticker["BTC_ETH"]["last"])
        historicalValues10.appendleft(lastprice)
        historicalValues25.appendleft(lastprice)
    calculateSMA()
    calculateEMA()
    #balances and orders is important if the bot is live because we don't want to do anything if we have unfilled orders. Not important in testing
    b = poloniex.returnBalances()
    orders = poloniex.returnOpenOrders('BTC_ETH')
    print("current SMA = " + "{0:.7f}".format(currentSMA) + " | current EMA = " + "{0:.7f}".format(currentEMA) + " | current price: " + str(lastprice))
    #if(orders): #if there are open orders suspend trading until they are filled.
    #    print("there are open orders, no trading")
    #    logging.info('waiting for orders to clear')
    #    return
    if(initializationWindow == 20):
        tradeLogic(tw, b, poloniex)
    
    
def calculateSMA():
    global currentSMA
    currentSMA = sum(historicalValues25)/len(historicalValues25)
   

def calculateEMA():
    global currentEMA
    K = 2/((len(historicalValues10))+1)
    currentEMA = (lastprice*K)+(currentEMA*(1-K))
    
def tradeLogic(tw, balances, polo):
    global invested
    global buyprice
    global tickTime
    global testBalance
    if((currentEMA>currentSMA) and invested == False): #if positive crossover and we are not already invested, buy!
        print("BUY ETH NOW " + str(datetime.now().time()))
        amount = float(balances['BTC'])/lastprice
        #polo.buy('BTC_ETH',lastprice,float("{0:.5f}".format(amount)))
        logging.info('buying ETH now at ' + str(datetime.now().time()) + ' for ' + str(lastprice) + ' btc  | current balance: ' + balances['BTC'])
        buyprice = lastprice
        invested = True
    elif((currentEMA<currentSMA) and invested == True): #if negative crossover and we are invested, sell!
        print("SELL ETH NOW " + str(datetime.now().time()))
        percentageChange = (((lastprice-buyprice)/buyprice)*100)-0.3
        testBalance = testBalance + (testBalance*percentageChange/100) #update test balance -- profit??
        #polo.sell('BTC_ETH',lastprice,balances['ETH']) 
        logging.info('selling ETH now at ' + str(datetime.now().time()) + ' at ' + str(lastprice) + ' btc | percentage change = ' + str(percentageChange) + ' | new balance = ' + str(testBalance)) 
        invested = False

    
def main():
    #initialize stuff
    twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
    polo = poloniex(API_KEY, API_SECRET)
    s = sched.scheduler(time.time, time.sleep)
    logging.basicConfig(filename='trade1.log', level=logging.INFO)
    logging.info('start logging at ' + str(datetime.now().time()))
    #start loop!
    functionLoop(polo, s, twitter)
    
    
if __name__ == "__main__":
    main()