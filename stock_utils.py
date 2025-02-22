import adata as ad

class StockUtils:
    def __init__(self):
        """初始化StockUtils类"""
        self.client = ad.stock  # 初始化AData股票客户端
        
    def get_stock_list(self):
        """获取全市场股票列表
        
        Returns:
            list: 股票代码列表，格式如 ['000001.SZ', '600000.SH']
        """
        try:
            # 使用AData获取股票列表
            stocks = ad.stock.info.all_code()
            # 转换代码格式
            stock_list = []
            for _, row in stocks.iterrows():
                code = row.stock_code  # 使用code字段而不是symbol
                if code.startswith('6'):
                    stock_list.append(f"{code}.SH")
                elif code.startswith(('0', '3')):  # 增加对创业板的支持
                    stock_list.append(f"{code}.SZ")
            return stock_list
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return []

    def get_stock_data(self, stock_code):
        """获取单只股票的历史数据"""
        try:
            symbol = stock_code.split('.')[0]  # 去掉.SH或.SZ后缀
            # 使用正确的API调用方式获取日线数据
            df = self.client.market.daily(symbol=symbol)
            # 重命名列以匹配原有代码
            df = df.rename(columns={
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

    def get_holding_stocks(self):
        """获取持仓股票列表（示例）"""
        return []  # 返回空列表，实际使用时需要实现持仓管理

    def get_position_info(self, stock_code):
        """获取持仓信息（示例）"""
        return {'entry_price': 0, 'lowest_price': 0}  # 返回默认值，实际使用时需要实现持仓管理 

    def get_stock_name(self, stock_code):
        """获取股票名称"""
        try:
            symbol = stock_code.split('.')[0]  # 去掉.SH或.SZ后缀
            stock_info = self.client.stock_info(symbol=symbol)
            return stock_info['name']
        except:
            return stock_code

# 创建全局实例
stock_utils = StockUtils()


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
            # 添加交易所后缀
            df['full_code'] = df['stock_code'].apply(
                lambda x: f"{x}.SH" if x.startswith(('6', '5', '9')) else f"{x}.SZ"
            )
            print(f"成功加载{len(df)}只股票信息")
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