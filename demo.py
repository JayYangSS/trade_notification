# -*- coding: utf-8 -*-
import backtrader as bt
import tushare as ts
import pandas as pd
import requests
import time
from datetime import datetime


TUSHARE_TOKEN = 'aa36663e24c9eb442c397fc58e25c06d0cfd16d99620e96604ab9253'
# ================== 微信通知模块 ==================
def wxpusher_send(message):
    """使用WxPusher发送通知（需提前注册获取token）"""
    url = "http://wxpusher.zjiecode.com/api/send/message"
    headers = {'Content-Type': 'application/json'}
    data = {
        "appToken": "AT_zAb5ylTsmXVGpTtUmdcNFAlkUZZW5Fa8",  # 请确认这是您的正确token
        "content": message,
        "contentType": 1,
        "uids": ["UID_4BCMVhDdzLPqVg55NgAVnUkKPDO3"]        # 请确认这是您的正确UID
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            print(f"微信通知发送成功: {message}")
        else:
            print(f"微信通知发送失败: {response.text}")
    except Exception as e:
        print(f"微信通知发送异常: {str(e)}")

# ================== 主升浪策略类 ==================
class MainWaveStrategy(bt.Strategy):
    params = (
        ('ma_short', 5),
        ('ma_long', 20),
        ('rsi_period', 14),
        ('vol_ratio', 1.5)
    )

    def __init__(self):
        # 指标计算
        self.ma5 = bt.indicators.SMA(self.data.close, period=self.p.ma_short)
        self.ma20 = bt.indicators.SMA(self.data.close, period=self.p.ma_long)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(self.data.close)
        self.volume_ma5 = bt.indicators.SMA(self.data.volume, period=5)
        
        # 状态跟踪
        self.order = None
        self.entry_price = None
        self.lowest_after_entry = None

    def next(self):
        # 跳过非交易时间（9:30-11:30, 13:00-15:00）
        dt = self.datas[0].datetime.datetime(0)
        if not self.is_trading_time(dt):
            return

        # 买入信号条件
        buy_signal = (
            self.ma5[0] > self.ma20[0] and                    # 5日线上穿20日线
            self.data.volume[0] > self.volume_ma5[0]*self.p.vol_ratio and  # 量能达标
            self.macd.macd[0] > self.macd.signal[0] and       # MACD金叉
            self.rsi[0] < 70 and                              # 防止超买
            not self.position                                 # 无持仓
        )

        # 卖出信号条件
        sell_signal = (
            self.position and (
                self.data.close[0] < self.lowest_after_entry * 0.97 or  # 止损
                self.ma5[0] < self.ma20[0] or                          # 趋势反转
                self.rsi[0] > 80                                      # 超卖
            )
        )

        # 执行买入
        if buy_signal:
            self.order = self.buy(size=self.broker.getcash() // self.data.close[0])
            self.entry_price = self.data.close[0]
            self.lowest_after_entry = self.data.low[0]
            wxpusher_send(f"🚀 买入信号触发 @ {dt.strftime('%Y-%m-%d %H:%M')}\n"
                         f"价格: {self.data.close[0]:.2f}, RSI: {self.rsi[0]:.2f}")

        # 执行卖出
        elif sell_signal:
            self.order = self.sell(size=self.position.size)
            wxpusher_send(f"🛑 卖出信号触发 @ {dt.strftime('%Y-%m-%d %H:%M')}\n"
                         f"价格: {self.data.close[0]:.2f}, 盈利: {self.position.pnlcomm:.2f}")

        # 更新最低价（用于止损）
        if self.position:
            self.lowest_after_entry = min(self.lowest_after_entry, self.data.low[0])

    def is_trading_time(self, dt):
        """判断是否为A股交易时间"""
        time_now = dt.time()
        am_start = datetime.strptime("09:30:00", "%H:%M:%S").time()
        am_end = datetime.strptime("11:30:00", "%H:%M:%S").time()
        pm_start = datetime.strptime("13:00:00", "%H:%M:%S").time()
        pm_end = datetime.strptime("15:00:00", "%H:%M:%S").time()
        return (am_start <= time_now <= am_end) or (pm_start <= time_now <= pm_end)

# ================== 回测执行模块 ==================

def init_tushare():
    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    return pro

if __name__ == '__main__':
    # 初始化引擎
    cerebro = bt.Cerebro()
    
    # 加载数据（示例使用Tushare，需自行获取token）
    #pro = ts.pro_api('TUSHARE_TOKEN')  # 替换为你的Tushare token
    pro = init_tushare()
    df = pro.daily(ts_code='600519.SH', start_date='20200101', end_date='20231231')
    df = df.sort_values('trade_date')
    df['datetime'] = pd.to_datetime(df['trade_date'])
    df.set_index('datetime', inplace=True)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    # 添加策略
    cerebro.addstrategy(MainWaveStrategy)

    # 设置初始资金和手续费
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    # 添加测试推送
    print("开始回测...")
    wxpusher_send("🔄 回测开始运行...")
    
    # 运行回测
    print('初始资金: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    print('最终资金: %.2f' % final_value)
    
    # 发送回测结果
    profit = final_value - 100000.0
    wxpusher_send(f"📊 回测完成\n初始资金: 100000.00\n最终资金: {final_value:.2f}\n盈利: {profit:.2f}")

    # 可视化结果
    cerebro.plot(style='candlestick', volume=False)