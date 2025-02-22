from stock_utils import StockDataLoader
from strategy import monitor_market
import time

if __name__ == "__main__":
    print("正在初始化股票监控系统...")
    # 获取股票列表
    stock_utils = StockDataLoader()
    stock_list = stock_utils.get_stock_list()
    print(f"成功获取{len(stock_list)}只股票")
    
    # 定时运行市场监控
    while True:
        print(f"开始新一轮市场扫描 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        monitor_market(stock_list, stock_utils.get_stock_data, output_num=5, max_workers=20)
        print("扫描完成，等待下一轮...")
        time.sleep(300)  # 5分钟扫描一次