from send_message import wxpusher_send
import time
from stock_utils import StockDataLoader
from concurrent.futures import ThreadPoolExecutor, as_completed


# 核心指标计算（以文献9的Python源码为基础）
def calculate_signals(data):
    # 确保数据按时间正序排列
    data = data.sort_values('trade_date')
    
    # 计算均线系统
    data['MA5'] = data['close'].rolling(5).mean()
    data['MA10'] = data['close'].rolling(10).mean()
    data['MA20'] = data['close'].rolling(20).mean()
    
    # MACD指标
    data['DIF'] = data['close'].ewm(span=12).mean() - data['close'].ewm(span=26).mean()
    data['DEA'] = data['DIF'].ewm(span=9).mean()
    data['MACD'] = (data['DIF'] - data['DEA']) * 2
    
    # 主力线与散户线（简化版，完整逻辑参考文献9）
    data['主力线'] = data['close'].rolling(27, min_periods=1).apply(lambda x: (x.iloc[-1]-x.min())/(x.max()-x.min())*100 if len(x)>0 else 0).ewm(span=3).mean()
    data['散户线'] = data['主力线'].ewm(span=3).mean()
    
    return data

# 信号触发条件
def check_buy_signal(data):
    latest = data.iloc[-1]
    # 条件1：均线金叉且站稳20日线
    cond1 = (latest['MA5'] > latest['MA10']) and (latest['close'] > latest['MA20'])
    # 条件2：成交量达标
    cond2 = latest['volume'] > 1.5 * data['volume'].rolling(5).mean().iloc[-1]
    # 条件3：MACD动能转强
    cond3 = (latest['MACD'] > 0) and (latest['MACD'] > data['MACD'].iloc[-2])
    # 条件4：主力控盘
    cond4 = (latest['主力线'] > latest['散户线']) and (latest['主力线'] > 20)
    
    return cond1 and cond2 and cond3 and cond4


# 止损与止盈条件判断（需维护持仓记录）
def check_sell_signal(data, entry_price, lowest_price):
    latest = data.iloc[-1]
    
    # 条件1：止损触发（跌破买入后最低价3%）
    stop_loss_cond = latest['close'] < lowest_price * 0.97
    
    # 条件2：均线死叉（5日线下穿10日线）
    ma_death_cross = (data['MA5'].iloc[-2] > data['MA10'].iloc[-2]) and (data['MA5'].iloc[-1] < data['MA10'].iloc[-1])
    
    # 条件3：MACD高位死叉（DIF下穿DEA且处于零轴上方）
    macd_death = (latest['DIF'] < latest['DEA']) and (latest['DIF'] > 0)
    
    # 条件4：成交量放量下跌（当日跌幅>3%且成交量>前5日均量1.2倍）
    volume_cond = (latest['close'] < latest['open'] * 0.97) and (latest['volume'] > data['volume'].rolling(5).mean().iloc[-1] * 1.2)
    
    # 条件5：K线形态
    bearish_pattern, pattern_name = detect_bearish_candlestick(data)
    
    if bearish_pattern:
        print(f"检测到看跌形态: {pattern_name}")
    
    return stop_loss_cond or ma_death_cross or macd_death or volume_cond or bearish_pattern

def detect_bearish_candlestick(data):
    """
    检测多种看跌K线形态
    返回: (bool, str) - (是否检测到形态, 形态名称)
    """
    # 获取最近的K线数据
    last_k = data.tail(5)
    
    # 计算实体和影线
    last_k['body'] = last_k['close'] - last_k['open']
    last_k['upper_shadow'] = last_k['high'] - last_k[['open', 'close']].max(axis=1)
    last_k['lower_shadow'] = last_k[['open', 'close']].min(axis=1) - last_k['low']
    last_k['body_size'] = abs(last_k['body'])
    
    # 1. 黄昏之星形态
    if len(last_k) >= 3:
        k1, k2, k3 = last_k.iloc[-3:].values
        if (k1['body'] > 0 and  # 第一天阳线
            abs(k2['body']) < k1['body_size'] * 0.3 and  # 第二天十字星
            k3['body'] < 0 and  # 第三天阴线
            k3['body_size'] > k1['body_size'] * 0.5):  # 第三天实体够大
            return True, "黄昏之星形态"
    
    # 2. 乌云盖顶
    if len(last_k) >= 2:
        k1, k2 = last_k.iloc[-2:].values
        if (k1['body'] > 0 and  # 第一天阳线
            k2['open'] > k1['close'] and  # 第二天高开
            k2['close'] < (k1['open'] + k1['close'])/2):  # 第二天收盘价低于前一天实体中点
            return True, "乌云盖顶形态"
    
    # 3. 三只乌鸦
    if len(last_k) >= 3:
        last_3 = last_k.iloc[-3:]
        if (all(last_3['body'] < 0) and  # 连续三根阴线
            all(last_3['body_size'] > last_3['body_size'].mean() * 0.7)):  # 实体都较大
            return True, "三只乌鸦形态"
    
    # 4. 吊颈线
    if len(last_k) >= 1:
        k = last_k.iloc[-1]
        if (k['lower_shadow'] > k['body_size'] * 2 and  # 下影线长
            k['upper_shadow'] < k['body_size'] * 0.1):  # 上影线短
            return True, "吊颈线形态"
    
    return False, "无看跌形态"

def process_single_stock(stock_code, data_fetcher):
    """处理单只股票的函数"""
    try:
        # 获取股票数据
        data = data_fetcher(stock_code)
        if data is None or data.empty:
            return None
            
        data = calculate_signals(data)
        
        # 检查买入信号
        if check_buy_signal(data):
            return {
                'code': stock_code,
                'name': stock_utils.get_stock_name(stock_code),
                'price': data['close'].iloc[-1],
                'reason': get_buy_reason(data)
            }
    except Exception as e:
        print(f"处理股票 {stock_code} 时出错: {str(e)}")
    return None

def monitor_market(stock_list, data_fetcher, output_num=2, max_workers=10):
    """
    并发监控全市场股票
    
    参数:
    stock_list: 股票代码列表
    data_fetcher: 获取股票数据的函数
    output_num: 最大输出数量
    max_workers: 最大线程数
    """
    buy_signals = []
    processed_count = 0
    total_stocks = len(stock_list)
    
    print(f"开始并发处理{total_stocks}只股票...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_stock = {
            executor.submit(process_single_stock, stock, data_fetcher): stock 
            for stock in stock_list
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_stock):
            processed_count += 1
            if processed_count % 100 == 0:  # 每处理100只股票打印一次进度
                elapsed = time.time() - start_time
                print(f"已处理: {processed_count}/{total_stocks} "
                      f"耗时: {elapsed:.2f}秒 "
                      f"平均: {elapsed/processed_count:.3f}秒/只")
            
            result = future.result()
            if result:
                buy_signals.append(result)
                if len(buy_signals) >= output_num:
                    break
    
    # 发送买入信号通知
    if buy_signals:
        send_buy_signals(buy_signals)
    
    elapsed = time.time() - start_time
    print(f"处理完成! 总耗时: {elapsed:.2f}秒, 平均: {elapsed/total_stocks:.3f}秒/只")

def get_buy_reason(data):
    """获取买入信号触发的具体原因"""
    latest = data.iloc[-1]
    reasons = []
    
    if latest['MA5'] > latest['MA10'] and latest['close'] > latest['MA20']:
        reasons.append("均线金叉且站稳20日线")
    
    if latest['volume'] > 1.5 * data['volume'].rolling(5).mean().iloc[-1]:
        reasons.append("成交量放大")
        
    if latest['MACD'] > 0 and latest['MACD'] > data['MACD'].iloc[-2]:
        reasons.append("MACD动能转强")
        
    if latest['主力线'] > latest['散户线'] and latest['主力线'] > 20:
        reasons.append("主力持续控盘")
        
    return "、".join(reasons)

def get_sell_reason(data):
    """获取卖出信号触发的具体原因"""
    latest = data.iloc[-1]
    reasons = []
    
    # 检查各种卖出条件并记录原因
    if latest['MA5'] < latest['MA10']:
        reasons.append("均线死叉")
    
    if latest['DIF'] < latest['DEA'] and latest['DIF'] > 0:
        reasons.append("MACD高位死叉")
    
    bearish_pattern, pattern_name = detect_bearish_candlestick(data)
    if bearish_pattern:
        reasons.append(f"出现{pattern_name}")
        
    return "、".join(reasons)

def send_buy_signals(signals):
    """发送买入信号通知"""
    message = "🚀 买入信号提醒\n\n"
    for signal in signals:
        message += f"股票：{signal['name']}({signal['code']})\n"
        message += f"当前价：{signal['price']:.2f}\n"
        message += f"触发原因：{signal['reason']}\n"
        message += "------------------------\n"
    
    wxpusher_send(message)

def send_sell_signals(signals):
    """发送卖出信号通知"""
    message = "⚠️ 卖出信号提醒\n\n"
    for signal in signals:
        message += f"股票：{signal['name']}({signal['code']})\n"
        message += f"当前价：{signal['price']:.2f}\n"
        message += f"盈亏：{signal['profit']:.2f}%\n"
        message += f"触发原因：{signal['reason']}\n"
        message += "------------------------\n"
    
    wxpusher_send(message)



if __name__ == "__main__":
    print("正在初始化股票监控系统...")
    # 获取股票列表
    stock_utils = StockDataLoader()
    stock_list = stock_utils.get_stock_list()
    print(f"成功获取{len(stock_list)}只股票")
    
    # 定时运行市场监控
    while True:
        print(f"开始新一轮市场扫描 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        monitor_market(stock_list, stock_utils.get_stock_data, output_num=10000, max_workers=20)
        print("扫描完成，等待下一轮...")
        time.sleep(300)  # 5分钟扫描一次
