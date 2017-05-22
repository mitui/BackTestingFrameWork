# encoding: UTF-8

import numpy as np
from strategyTemplate import StrategyTemplate
from datetime import datetime

from constants import *

########################################################################

class LoggingToFile():
    def __init__(self):
        self.f = open('catDualThurst_bar_data.dat', 'w')
        
    def logging(self, *log_list):
        now = datetime.now()
        str_list = [str(log) for log in log_list]
        merged_str = ' '.join(str_list)
        date_str = now.strftime('%Y-%m-%d %H:%M:%S')
        self.f.write(date_str + ':  ' + merged_str + '\n')
        self.f.flush()

class HistoryRecordGetter():
    def __init__(self):
        self.f = open('processed_data.dat', 'r')
        self.init_reading()
    
    def init_reading(self):
        self.recorders = {}
        section_name = ''
        for line in self.f:
            line = line.strip()
            if '[' in line:
                section_name = line[1:-1]
                self.recorders[section_name] = {}
            else:
                date_str, val = line.split('=')
                self.recorders[section_name][date_str] = float(val)
        print(self.recorders.keys())
    
    def getRecorderVal(self, section_name, date_str):
        return self.recorders[section_name][date_str]

class DualThrustTSG(StrategyTemplate):
    """基于30分钟K线的DualThrust策略"""
    className = 'DualThrustTSG'
    author = u'tusonggao'
    
    # 策略参数
    Length = 3
    
    buyRatio = 0.65           # 开多比例
    sellRatio = 0.8           # 开空比例
    takeProfitRatio = 2.0     # 止盈比例

    initDays = 20
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'Length',
                 'buyRatio',
                 'sellRatio',
                 'takeProfitRatio']    
    
    # 变量列表，保存了变量的名称
    varList = []  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DualThrustTSG, self).__init__(ctaEngine, setting)
        
        self.className = self.__class__.__name__
        self.buyEntryPrice = -1.0    # 记录做多的价格位
        self.sellEntryPrice = -1.0   # 记录做多的价格位
        self.currentBar = None
        self.lastBar = None          # 记录上一根bar
        # self.currentPosition = 0     # 当前仓位大小
        self.lots = 3                # 每次开仓大小
        self.actionRange = 0.0
        
        self.logging = LoggingToFile()
        self.recordGetter = HistoryRecordGetter()
    
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'catTurtle_tsg 策略初始化')
        
#        initData = self.loadBar(self.initDays)
#        for bar in initData:
#            self.onBar(bar)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'DualThrustTSG 策略启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'DualThrustTSG 策略停止')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线
        tickMinute = tick.datetime.minute
        
        if tickMinute != self.barMinute:    
            if self.bar:
                self.onBar(self.bar)
            
            bar = CtaBarData()              
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange
            
            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice
            
            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime    # K线的时间设为第一个Tick的时间
            
            self.bar = bar                  # 这种写法为了减少一层访问，加快速度
            self.barMinute = tickMinute     # 更新当前的分钟
            
        else:                               # 否则继续累加新的K线
            bar = self.bar                  # 写法同样为了加快速度
            
            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice
            

    def update_entry_price(self, bar):
        date_str = bar.datetime.strftime('%Y-%m-%d')
        HH = self.recordGetter.getRecorderVal('HH', date_str)
        HC = self.recordGetter.getRecorderVal('HC', date_str)
        LC = self.recordGetter.getRecorderVal('LC', date_str)
        LL = self.recordGetter.getRecorderVal('LL', date_str)
        if (HH-LC) > (HC-LL):
            action_Range = HH-LC
        else:
            action_Range = HC-LL            
        self.buyEntryPrice = bar.open + self.buyRatio*action_Range
        self.sellEntryPrice = bar.open - self.sellRatio*action_Range
        self.buyTakeProfitPrice = (self.buyEntryPrice + 
                           self.takeProfitRatio*action_Range)
        self.sellTakeProfitPrice = (self.sellEntryPrice - 
                            self.takeProfitRatio*action_Range)
        
    def check_open_positions(self, bar):
        if (self.buyEntryPrice>=bar.low and self.buyEntryPrice<=bar.high and 
               self.pos==0):
            if bar.open>self.buyEntryPrice:
                self.buy(bar.open, self.lots)
            else:
                self.buy(self.buyEntryPrice, self.lots)
#            self.currentPosition += self.lots
        if (self.sellEntryPrice>=bar.low and self.sellEntryPrice<=bar.high and 
               self.pos==0):
            if bar.open>self.sellEntryPrice:
                self.short(bar.open, self.lots)
            else:
                self.short(self.sellEntryPrice, self.lots)
#            self.currentPosition -= self.lots
    
    def check_close_positions_take_profit(self, bar):
        if (self.pos>0 and self.buyTakeProfitPrice>=bar.low and 
              self.buyTakeProfitPrice<=bar.high):
            if bar.open>self.buyTakeProfitPrice:
                self.sell(bar.open, self.lots)
            else:
                self.sell(self.buyTakeProfitPrice, self.lots)
#            self.currentPosition -= self.lots
        if (self.pos<0 and self.sellTakeProfitPrice>=bar.low and 
              self.sellTakeProfitPrice<=bar.high):
            if bar.open<self.sellTakeProfitPrice:
                self.cover(bar.open, self.lots)
            else:
                self.cover(self.sellEntryPrice, self.lots)
#            self.currentPosition += self.lots
    
    def close_positions_end_of_day(self, bar):
        if self.pos > 0:
            self.sell(bar.close, self.lots)
#            self.currentPosition -= self.lots
        if self.pos < 0:
            self.cover(bar.close, self.lots)
#            self.currentPosition += self.lots        
        
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.lastBar = self.currentBar
        self.currentBar = bar
        
        date_str = bar.datetime.strftime('%Y-%m-%d')
        if date_str<='2010-04-22':
            return
            
        if self.isEndOfDay(bar):
            self.close_positions_end_of_day(bar)            
        elif self.isStartOfDay(bar):            
            self.update_entry_price(bar)
        self.check_open_positions(bar)
        self.check_close_positions_take_profit(bar)   
        
        self.putEvent()
        
    
    #----------------------------------------------------------------------
    def isEndOfDay(self, bar):
        next_bar = self.getDataByOffset(bar, 1)
        if next_bar==None:
            return True
        else:
            date_str = bar.datetime.strftime('%Y-%m-%d')
            next_date_str = next_bar.datetime.strftime('%Y-%m-%d')
            if date_str!=next_date_str:
                return True
            else:
                return False              
    
    #----------------------------------------------------------------------
    def isStartOfDay(self, bar):
        if self.lastBar==None:
            print('get the first bar')
            return True
            
        date_str = bar.datetime.strftime('%Y-%m-%d')
        last_date_str = self.lastBar.datetime.strftime('%Y-%m-%d')
        if date_str!=last_date_str:
            return True
        else:
            return False

        
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    
######################################################################
class OrderManagementDemo(StrategyTemplate):
    """基于tick级别细粒度撤单追单测试demo"""
    
    className = 'OrderManagementDemo'
    author = u'用Python的交易员'
    
    # 策略参数
    initDays = 10   # 初始化数据所用的天数
    
    # 策略变量
    bar = None
    barMinute = EMPTY_STRING
    
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(OrderManagementDemo, self).__init__(ctaEngine, setting)
                
        self.lastOrder = None
        self.orderType = ''
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略初始化')
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略停止')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""

        # 建立不成交买单测试单        
        if self.lastOrder == None:
            self.buy(tick.lastprice - 10.0, 1)

        # CTA委托类型映射
        if (self.lastOrder != None and self.lastOrder.direction == u'多' and 
              self.lastOrder.offset == u'开仓'):
            self.orderType = u'买开'

        elif (self.lastOrder != None and self.lastOrder.direction == u'多' and 
                  self.lastOrder.offset == u'平仓'):
            self.orderType = u'买平'

        elif (self.lastOrder != None and self.lastOrder.direction == u'空' and 
                  self.lastOrder.offset == u'开仓'):
            self.orderType = u'卖开'

        elif (self.lastOrder != None and self.lastOrder.direction == u'空' and 
                 self.lastOrder.offset == u'平仓'):
            self.orderType = u'卖平'
                
        # 不成交，即撤单，并追单
        if self.lastOrder != None and self.lastOrder.status == u'未成交':
            self.cancelOrder(self.lastOrder.vtOrderID)
            self.lastOrder = None
        elif self.lastOrder != None and self.lastOrder.status == u'已撤销':
        # 追单并设置为不能成交            
            self.sendOrder(self.orderType, self.tick.lastprice - 10, 1)
            self.lastOrder = None
            
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        pass
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        self.lastOrder = order
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass


if __name__=='__main__':
    recordGetter = HistoryRecordGetter()
    val = recordGetter.getRecorderVal('LL', '2010-08-25')
    print(val)
    