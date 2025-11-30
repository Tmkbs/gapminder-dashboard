import pandas as pd
import random
from datetime import datetime, timedelta

# --- 1. 配置你的持仓 (这里演示用，你可以改成自己的) ---
# 格式: '代码': [股数, 成本价]
my_positions = {
    'AAPL': [50, 145.00],
    'NVDA': [20, 350.00],
    'MSFT': [30, 280.00],
    'TSLA': [60, 180.00],
    'AMZN': [40, 130.00],
    'GOOGL': [25, 120.00],
    'BTC-USD': [0.5, 30000.00], # 加密货币
}

# --- 2. 生成交易记录 ---
data = []
# 倒推一个日期
base_date = datetime.now() - timedelta(days=365)

for ticker, (qty, cost) in my_positions.items():
    # 生成一行买入记录
    data.append({
        'Date': base_date.strftime('%Y-%m-%d'),
        'Ticker': ticker,
        'Action': 'Buy',
        'Quantity': qty,
        'Price': cost
    })

# --- 3. 保存为 Excel (.xlsx) ---
df = pd.DataFrame(data)
file_name = 'portfolio.xlsx'

# 这一步能彻底解决乱码问题
try:
    df.to_excel(file_name, index=False, engine='openpyxl')
    print(f"✅ 成功！已生成 Excel 文件: {file_name}")
    print("✨ 这个文件不会有编码问题，PythonAnywhere 能完美读取。")
except Exception as e:
    print(f"❌ 生成失败: {e}")
    print("请确保你已经安装了 openpyxl (pip install openpyxl)")