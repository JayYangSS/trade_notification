import adata as ad

class StockUtils:
    def __init__(self):
        """初始化StockUtils类"""
        pass
        
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
        symbol = stock_code.split('.')[0]  # 去掉.SH或.SZ后缀
        # 获取日线数据，默认返回最近100个交易日的数据
        df = self.client.daily(symbol=symbol)
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