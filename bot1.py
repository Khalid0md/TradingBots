# region imports
import numpy as np
from AlgorithmImports import *
# endregion

class VirtualYellowGreenBat(QCAlgorithm):

    def Initialize(self):
        self.SetCash(100000)
        self.SetStartDate(2017, 9, 1)
        self.SetEndDate(2020, 9, 1)

        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol

        self.lookback = 20
        self.ceiling, self.floor = 30, 10

        self.initialStopRisk = 0.98
        self.trailingStopRisk  =  0.9

        self.Schedule.On(self.DateRules.EveryDay(self.symbol), \
            self.TimeRules.AfterMarketOpen(self.symbol, 20), \
                Action(self.EveryMarketOpen))
        

    def OnData(self, data: Slice):
        self.Plot("Data chart", self.symbol,  self.Securities[self.symbol].Close)

    def EveryMarketOpen(self):
        # to adjust length of lookback, compare 30 day volatility today to 30 dayvol yesterday, adjust accordingly
        close = self.History(self.symbol, 31, Resolution.Daily)["close"]
        todayvol  = np.std(close[1:31]) #day 31 is today
        yesterdayvol = np.std(close[0:30]) #day 30 is yesterday
        deltavol = (todayvol - yesterdayvol) / todayvol #normalized difference
        self.lookback = round(self.lookback * (1 +  deltavol))
        
        if self.lookback > self.ceiling:
            self.lookback = self.ceiling
        elif self.lookback < self.floor:
            self.lookback = self.floor
        
        #is a breakout happening? are we higher than all daily high's from loookback?
        self.highs = self.History(self.symbol, self.lookback, Resolution.Daily)["high"]

        #if we are not in an open position and todays close is higher than the  max close in highs
        if not self.Securities[self.symbol].Invested and \
        self.Securities[self.symbol].Close >= max(self.highs[:-1]):#leaving out last data point, don't want to compare yesterdays high with yesterdays close
            self.SetHoldings(self.symbol, 1) 
            #buy SPY at market price with 100% of holdings
            self.breakoutlvl = max(self.highs[:-1])
            self.highestPrice = self.breakoutlvl

        #implement the trailing stop loss
        if self.Securities[self.symbol].Invested:
            #if we don't have a stop loss already, create 2% stop loss
            if not self.Transactions.GetOpenOrders(self.symbol):
                self.stopMarketTicket = self.StopMarketOrder(self.symbol, \
                     -self.Portfolio[self.symbol].Quantity, \
                        self.initialStopRisk * self.breakoutlvl)

            #turn it into a trailing stop loss

            #raise stop loss when security makes new highs
            if self.Securities[self.symbol].Close > self.highestPrice and  \
                    self.initialStopRisk * self.breakoutlvl < self.Securities[self.symbol].Close * self.trailingStopRisk:
                self.highestPrice = self.Securities[self.symbol].Close
                updateFields = UpdateOrderFields()
                updateFields.StopPrice = self.Securities[self.symbol].Close * self.trailingStopRisk
                response = self.stopMarketTicket.Update(updateFields)
                
                if response.IsSuccess:
                    self.Debug("Trailing stop price updated, new: " + str(updateFields.StopPrice))

                self.Plot("Data Chart", "Stop Price", self.stopMarketTicket.Get(OrderField.StopPrice))