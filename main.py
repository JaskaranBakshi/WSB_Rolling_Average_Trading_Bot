from AlgorithmImports import *
from QuantConnect.Data.Custom.Quiver import *

class QuiverWallStreetBetsDataAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2018, 1, 1)
        self.SetEndDate(2021, 6, 1)
        self.SetCash(100000)
        
        symbols = [Symbol.Create("SPY", SecurityType.Equity, Market.USA)]
        self.AddUniverseSelection(ManualUniverseSelectionModel(symbols))
        
        self.AddAlpha(WallStreamBetsAlphaModel())
        
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        
        self.AddRiskManagement(NullRiskManagementModel())
        
        self.SetExecution(VolumeWeightedAveragePriceExecutionModel())
        

class WallStreamBetsAlphaModel(AlphaModel):
    
    symbol_data_by_symbol = {}

    def __init__(self, mentions_threshold=5):
        self.mentions_threshold = mentions_threshold
        
    def Update(self, algorithm, data):
        insights = [] # stores the insight of each ticker
        
        # go through all tickers in the universe for the bot
        for report in data.Get(QuiverWallStreetBets).Values:
            #figure out rolling averages
            bef = self.symbol_data_by_symbol[report.Symbol.Underlying].time_ticker # store the average mentions from before this current time slice
            sum_v = bef*self.symbol_data_by_symbol[report.Symbol.Underlying].symb_mentions # get the total sum of mentions before this current time slice
            self.symbol_data_by_symbol[report.Symbol.Underlying].time_ticker += 1 # increase the amount of time blocks by 1
            sum_v += report.Mentions # total sum of mentions to current time
            # the below calculates the new average mentions for the specific ticker
            self.symbol_data_by_symbol[report.Symbol.Underlying].symb_mentions = sum_v/self.symbol_data_by_symbol[report.Symbol.Underlying].time_ticker
            
            # once the average has been calculated we can compare to the threshold set above and give the alpha
            # an insight of whether the ticker will go up or down
            if self.symbol_data_by_symbol[report.Symbol.Underlying].symb_mentions > self.mentions_threshold:
                target_direction = InsightDirection.Up
            elif self.symbol_data_by_symbol[report.Symbol.Underlying].symb_mentions < self.mentions_threshold:
                target_direction = InsightDirection.Down
            else:
                target_direction = None

            try:
                self.symbol_data_by_symbol[report.Symbol.Underlying].target_direction = target_direction
            except:
                continue
        try:
            for symbol, symbol_data in self.symbol_data_by_symbol.items():
                # Ensure we have security data for the current Slice
                if not (data.ContainsKey(symbol) and data[symbol] is not None):
                    continue
                
                if symbol_data.target_direction is not None:
                    insights += [Insight.Price(symbol, timedelta(1), symbol_data.target_direction)]
                    symbol_data.target_direction = None
        except:
            return insights

        return insights
            
    def OnSecuritiesChanged(self, algorithm, changes):
        for security in changes.AddedSecurities:
            symbol = security.Symbol
            self.symbol_data_by_symbol[symbol] = SymbolData(algorithm, symbol)
        
        for security in changes.RemovedSecurities:
            symbol_data = self.symbol_data_by_symbol.pop(security.Symbol, None)
            if symbol_data:
                symbol_data.dispose()

class SymbolData:
    target_direction = None
    symb_mentions = 0 # rolling average
    time_ticker = 0 # number of time slices passed
    
    def __init__(self, algorithm, symbol):
        self.algorithm = algorithm
        
        # Requesting data
        self.quiver_wsb_symbol = algorithm.AddData(QuiverWallStreetBets, symbol).Symbol
        
        # Historical data
        history = algorithm.History(QuiverWallStreetBets, self.quiver_wsb_symbol, 60, Resolution.Daily)
        algorithm.Debug(f"We got {len(history)} items from our history request for {symbol} Quiver WallStreetBets data")
        
    def dispose(self):
        # Unsubscribe from the Quiver WallStreetBets feed for this security
        self.algorithm.RemoveSecurity(self.quiver_wsb_symbol)