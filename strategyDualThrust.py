# encoding: UTF-8

import numpy as np
from ctaBase import *
from ctaTemplate import CtaTemplate
from ctaTemplate import logging
from datetime import datetime

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

class DualThrustTSG(CtaTemplate):
    """����30����K�ߵ�DualThrust����"""
    className = 'DualThrustTSG'
    author = u'tusonggao'
    
    # ���Բ���
    Length = 3
    
    buyRatio = 0.65           # �������
    sellRatio = 0.8           # ���ձ���
    takeProfitRatio = 2.0     # ֹӯ����

    initDays = 20
    
    # �����б������˲���������
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'Length',
                 'buyRatio',
                 'sellRatio',
                 'takeProfitRatio']    
    
    # �����б������˱���������
    varList = []  

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DualThrustTSG, self).__init__(ctaEngine, setting)
        
        self.className = self.__class__.__name__
        self.buyEntryPrice = -1.0    # ��¼����ļ۸�λ
        self.sellEntryPrice = -1.0   # ��¼����ļ۸�λ
        self.currentBar = None
        self.lastBar = None          # ��¼��һ��bar
        # self.currentPosition = 0     # ��ǰ��λ��С
        self.lots = 3                # ÿ�ο��ִ�С
        self.actionRange = 0.0
        
        self.logging = LoggingToFile()
        self.recordGetter = HistoryRecordGetter()
    
        
    #----------------------------------------------------------------------
    def onInit(self):
        """��ʼ�����ԣ��������û��̳�ʵ�֣�"""
        self.writeCtaLog(u'catTurtle_tsg ���Գ�ʼ��')
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """�������ԣ��������û��̳�ʵ�֣�"""
        self.writeCtaLog(u'DualThrustTSG ��������')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """ֹͣ���ԣ��������û��̳�ʵ�֣�"""
        self.writeCtaLog(u'DualThrustTSG ����ֹͣ')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """�յ�����TICK���ͣ��������û��̳�ʵ�֣�"""
        # ����K��
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
            bar.datetime = tick.datetime    # K�ߵ�ʱ����Ϊ��һ��Tick��ʱ��
            
            self.bar = bar                  # ����д��Ϊ�˼���һ����ʣ��ӿ��ٶ�
            self.barMinute = tickMinute     # ���µ�ǰ�ķ���
            
        else:                               # ��������ۼ��µ�K��
            bar = self.bar                  # д��ͬ��Ϊ�˼ӿ��ٶ�
            
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
        """�յ�Bar���ͣ��������û��̳�ʵ�֣�"""
        self.lastBar = self.currentBar
        self.currentBar = bar
        
        date_str = bar.datetime.strftime('%Y-%m-%d')
        if date_str<='2010-04-22':
            return
            
        last_date_str = self.lastBar.datetime.strftime('%Y-%m-%d')
        next_date_str = self.getDataByOffset(bar, 1)
        if self.isEndOfDay(bar):
            self.close_positions_end_of_day(bar)
            
        if date_str != last_date_str:
            
            self.update_entry_price(bar)
        self.check_open_positions(bar)
        self.check_close_positions_take_profit(bar)   
        
        self.putEvent()
        
    
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
                
    
    def isStartOfDay(self, bar):
        
        
        
        
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """�յ�ί�б仯���ͣ��������û��̳�ʵ�֣�"""
        # ����������ϸ����ί�п��ƵĲ��ԣ����Ժ���onOrder
        pass
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """�յ��ɽ����ͣ��������û��̳�ʵ�֣�"""
        # ����������ϸ����ί�п��ƵĲ��ԣ����Ժ���onOrder
        pass
    
    
######################################################################
class OrderManagementDemo(CtaTemplate):
    """����tick����ϸ���ȳ���׷������demo"""
    
    className = 'OrderManagementDemo'
    author = u'��Python�Ľ���Ա'
    
    # ���Բ���
    initDays = 10   # ��ʼ���������õ�����
    
    # ���Ա���
    bar = None
    barMinute = EMPTY_STRING
    
    
    # �����б������˲���������
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']
    
    # �����б������˱���������
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
        """��ʼ�����ԣ��������û��̳�ʵ�֣�"""
        self.writeCtaLog(u'˫EMA��ʾ���Գ�ʼ��')
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """�������ԣ��������û��̳�ʵ�֣�"""
        self.writeCtaLog(u'˫EMA��ʾ��������')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """ֹͣ���ԣ��������û��̳�ʵ�֣�"""
        self.writeCtaLog(u'˫EMA��ʾ����ֹͣ')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """�յ�����TICK���ͣ��������û��̳�ʵ�֣�"""

        # �������ɽ��򵥲��Ե�        
        if self.lastOrder == None:
            self.buy(tick.lastprice - 10.0, 1)

        # CTAί������ӳ��
        if (self.lastOrder != None and self.lastOrder.direction == u'��' and 
              self.lastOrder.offset == u'����'):
            self.orderType = u'��'

        elif (self.lastOrder != None and self.lastOrder.direction == u'��' and 
                  self.lastOrder.offset == u'ƽ��'):
            self.orderType = u'��ƽ'

        elif (self.lastOrder != None and self.lastOrder.direction == u'��' and 
                  self.lastOrder.offset == u'����'):
            self.orderType = u'����'

        elif (self.lastOrder != None and self.lastOrder.direction == u'��' and 
                 self.lastOrder.offset == u'ƽ��'):
            self.orderType = u'��ƽ'
                
        # ���ɽ�������������׷��
        if self.lastOrder != None and self.lastOrder.status == u'δ�ɽ�':
            self.cancelOrder(self.lastOrder.vtOrderID)
            self.lastOrder = None
        elif self.lastOrder != None and self.lastOrder.status == u'�ѳ���':
        # ׷��������Ϊ���ܳɽ�            
            self.sendOrder(self.orderType, self.tick.lastprice - 10, 1)
            self.lastOrder = None
            
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """�յ�Bar���ͣ��������û��̳�ʵ�֣�"""
        pass
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """�յ�ί�б仯���ͣ��������û��̳�ʵ�֣�"""
        # ����������ϸ����ί�п��ƵĲ��ԣ����Ժ���onOrder
        self.lastOrder = order
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """�յ��ɽ����ͣ��������û��̳�ʵ�֣�"""
        # ����������ϸ����ί�п��ƵĲ��ԣ����Ժ���onOrder
        pass


if __name__=='__main__':
    recordGetter = HistoryRecordGetter()
    val = recordGetter.getRecorderVal('LL', '2010-08-25')
    print(val)
    