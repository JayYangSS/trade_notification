import adata
import pandas as pd
from datetime import datetime, timedelta
from functools import lru_cache

class StockDataLoader:
    def __init__(self):
        """适用于adata 2.8.4的稳定版数据加载工具"""
        self.stock_list = self._load_base_stocks()
        self.etf_list = self._load_etf_stocks()

    def _load_base_stocks(self):
        """加载A股基础信息（正确方法）"""
        try:
            # 使用正确的API获取股票列表
            df = adata.stock.info.all_code()
            
            # 过滤ST股票
            df = df[~df['short_name'].str.contains('ST|PT|退', na=False)]
            # 过滤北交所股票
            df = df[df['exchange'] != 'BJ']
            # 添加交易所后缀
            df['full_code'] = df.apply(
                lambda row: f"{row['stock_code']}.{row['exchange']}", axis=1
            )
            print(f"成功加载{len(df)}只股票信息（已剔除ST|PT|退市股票）")
            return df
        except Exception as e:
            print(f"股票列表加载失败: {str(e)}")
            return pd.DataFrame()

    def _load_etf_stocks(self):
        """加载ETF列表（正确方法）"""
        try:
            df = adata.fund.info.all_etf_exchange_traded_info()
            return [f"{sym}.SH" for sym in df['fund_code'].tolist()]
        except:
            return []

    def get_stock_list(self, include_etf=False):
        """获取证券代码列表"""
        base_list = self.stock_list['full_code'].tolist() if not self.stock_list.empty else []
        return base_list + self.etf_list if include_etf else base_list

    def get_stock_data(self, stock_code, days=250):
        """获取行情数据（已验证方法）"""
        try:
            code = stock_code.split('.')[0]
            # 使用正确的数据接口
            res_df = adata.stock.market.get_market(stock_code=code, k_type=1, start_date='2021-01-01')
        
            # 重命名列以匹配原有代码
            df = res_df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount',
                'date': 'trade_date'
            })
            return df
        except Exception as e:
            print(f"获取股票{stock_code}数据失败: {e}")
            return None
        
    def get_stock_name(self, stock_code):
        """获取股票名称"""
        try:
            # 从stock_list中查找对应的股票代码
            code = stock_code.split('.')[0]  # 移除交易所后缀
            stock_info = self.stock_list[self.stock_list['stock_code'] == code]
            if not stock_info.empty:
                return stock_info['short_name'].iloc[0]
            return "未知"
        except Exception as e:
            print(f"获取股票{stock_code}名称失败: {e}")
            return "未知"

# 使用示例
if __name__ == "__main__":
    # 初始化（如需代理：stock_utils = EnhancedStockUtils(proxy='your_proxy:port')）
    stock_utils = StockDataLoader()
    
    # 获取全市场股票列表（含ETF）
    all_stocks = stock_utils.get_stock_list(include_etf=True)
    print(f"获取到{len(all_stocks)}个标的")
    
    # 获取个股历史数据
    df = stock_utils.get_stock_data('000001.SZ')
    print(f"平安银行历史数据：\n{df.tail()}")
    
    # 获取指数数据
    index_df = stock_utils.get_index_data('000001.SH')  # 上证指数
    print(f"上证指数数据：\n{index_df.tail()}")