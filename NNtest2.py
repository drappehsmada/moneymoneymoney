
'''The first real neural network attempt!

Dependancies: Pybrain, scipy, numpy'''

from pybrain.tools.shortcuts import buildNetwork
from pybrain.datasets import SupervisedDataSet
from pybrain.structure import TanhLayer
from pybrain.supervised.trainers import BackpropTrainer
from scipy.interpolate import interp1d
import urllib
import urllib.request
import urllib.error
import json
import time
import hmac,hashlib
import logging
import calendar
import time
import datetime
import sys
from collections import deque
import numpy as np
import math

POLO_API_KEY =
POLO_SECRET = 


#variables for stoch osc
lastFourteenHigh = deque(maxlen=9)
lastFourteenLow = deque(maxlen=9)
KValueHistoricalValues = deque(maxlen=3)
currentDValue = 0
KValue = 0

#variables for MACD
historicalLong = deque(maxlen=18)
historicalShort = deque(maxlen=7)
MACDHistoricalValues = deque(maxlen=9)
LongEMA = 0
ShortEMA = 0
MACD_EMA = 0
MACD_Line = 0
MACD_Histo = 0

#other global variables
ppr = deque([0,0,0],maxlen=3)

def calculateStchOsc(lastClose, lastHigh, lastLow):
    global KValue
    global currentDValue
    global lastFourteenHigh
    global lastFourteenLow
    lastFourteenHigh.appendleft(lastHigh)
    lastFourteenLow.appendleft(lastLow)
    lowestLow = min(lastFourteenLow)
    highestHigh = max(lastFourteenHigh)
    if((highestHigh - lowestLow) != 0):
        KValue = 100*((lastClose-lowestLow)/(highestHigh-lowestLow))
        KValueHistoricalValues.appendleft(KValue)
        currentDValue = sum(KValueHistoricalValues)/len(KValueHistoricalValues)

def calculateMACD(lastClose):
    global LongEMA
    global ShortEMA
    global MACDHistoricalValues
    global MACD_Line
    global MACD_EMA
    global MACD_Histo
    historicalLong.appendleft(lastClose)
    historicalShort.appendleft(lastClose)
    K1 = 2/((len(historicalLong))+1)
    K2 = 2/((len(historicalShort))+1)
    K3 = 2/((len(MACDHistoricalValues))+1)
    LongEMA = (lastClose*K1)+(LongEMA*(1-K1))
    ShortEMA = (lastClose*K2)+(ShortEMA*(1-K2))
    MACD_Line = ShortEMA-LongEMA
    MACDHistoricalValues.appendleft(MACD_Line)
    MACD_EMA = (MACD_Histo*K3)+(MACD_EMA*(1-K3))
    MACD_Histo = MACD_Line - MACD_EMA

'''check out the pybrain documentation on how to build a dataset! In this iteration im using a 5 input 1 output dataset where the inputs are
MACD, Stoch Osc and the 3 previous prices and the output is price. This is an area of research and tinkering, I don't know what inputs are best correlated with
the price and I don't know if I should even be using the price as an output. Would it be better to just classify the output as up or down?? Or try to 
estimate the delta? Remains to be seen.
''' 
def buildDataSet(timeCat, length):
    ds = SupervisedDataSet(5,1) #initialize dataset (inputs, outputs)
    MACDvalueArray = np.array([0])
    KValueArray = np.array([0])
    priceArray = np.array([0])
    polo = poloniex(POLO_API_KEY, POLO_SECRET)
    if(timeCat == "days"):
        startTime = datetime.datetime.utcnow() + datetime.timedelta(days=length)
    elif(timeCat == "hours"):
        startTime = datetime.datetime.utcnow() + datetime.timedelta(hours=length)
    unixTime = calendar.timegm(startTime.utctimetuple())
    endTime = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
    chartData = polo.returnChartData(unixTime,endTime,300) #get all our data! start time, end time, period
    ia = np.array([0,0,0,0,0]) #heres our input array
    ta = np.array([0]) #and the output
    for i in chartData:
        #calculate our indicators
        calculateMACD(i['close']) 
        calculateStchOsc(i['close'],i['high'],i['low'])
        MACDvalueArray = np.vstack((MACDvalueArray,MACD_Histo))
        KValueArray = np.vstack((KValueArray,KValue))
        priceArray = np.vstack((priceArray,i['close']))
    #delete the first one because its all 0s
    MACDvalueArray = np.delete(MACDvalueArray,0,0) 
    KValueArray = np.delete(KValueArray,0,0)
    priceArray = np.delete(priceArray,0,0)
    MACD_max = max(MACDvalueArray)
    MACD_min = min(MACDvalueArray)
    K_max = max(KValueArray)
    K_min = min(KValueArray)
    price_max = max(priceArray)
    price_min = min(priceArray)
    #make a scaling function... Neural nets work better if all the input values are in the same range. Here we map to values between 0,1
    m = interp1d([MACD_min[0],MACD_max[0]],[0,1])
    k = interp1d([K_min[0],K_max[0]],[0,1])
    p = interp1d([price_min[0],price_max[0]],[0,1])
    #result = interp1d([0,1],[price_min[0],price_max[0]])
    for i in range(0,priceArray.size):
        scaledM = float(m(MACDvalueArray[i]))
        scaledK = float(k(KValueArray[i]))
        scaledP = float(p(priceArray[i]))
        #build the input and output arrays
        ia = np.vstack((ia,[scaledM,scaledK,ppr[0],ppr[1],ppr[2]]))
        ta = np.vstack((ta,[scaledP]))
        #this is a queue that keeps the last 3 values, appendleft for FIFO action
        ppr.appendleft(scaledP)
    np.savetxt('test1.out',ia,delimiter=',')
    #delete first 15 values because thats how long the MACD takes to get initialized to proper values
    for i in range(0,15):
        ia = np.delete(ia,0,0)
        ta = np.delete(ta,0,0)
    np.savetxt('test2.out',ia,delimiter=',') #this was just for testing, outputs all data to text file
    assert (ia.shape[0] == ta.shape[0]) #make sure input and output are same size
    ds.setField('input',ia)
    ds.setField('target',ta)
    print(str(len(ds))) #print out how many data points we have
    return ds
        
        
def main():
    trainingSet = buildDataSet("days", -1) #build data set. 
    net = buildNetwork(5,3,1,bias=True,hiddenclass=TanhLayer)
    trainer = BackpropTrainer(net,trainingSet,verbose=True)
    testSet = buildDataSet("hours", -6) #build another set for testing/validating
    #In my testing 4000 epochs has been enough to almost reach the lowest error without taking all day.
    #You could use trainUntilConvergence() but that takes all night and does only minimally better
    trainer.trainEpochs(4000)  
    #net.activateOnDataset(testSet)
    trainer.testOnData(testSet, verbose = True) # test on the data set.

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
        
    def returnChartData(self,start,end,period):
        try:
            ret = urllib.request.urlopen(urllib.request.Request('https://poloniex.com/public?command=returnChartData&currencyPair=BTC_ETH&start=' + str(start) + '&end=' + str(end) + '&period=' + str(period)))
            str_response = ret.read().decode('utf-8')
            return json.loads(str_response)
        except Exception:
            print("time out error! try again!")
            logging.info('just timed out, will try again.')

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

if __name__ == '__main__':
    main()