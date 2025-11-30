import pandas as pd
import random
from datetime import datetime

# --- 华尔街热门股池 ---
tech = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NFLX', 'AMD', 'INTC', 'CRM', 'ADBE']
finance = ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'V', 'MA']
consumer = ['KO', 'PEP', 'MCD', 'SBUX', 'NKE', 'COST', 'WMT']
crypto = ['BTC-USD', 'ETH-USD', 'SOL-USD']
energy = ['XOM', 'CVX', 'COP']

all_tickers = tech + finance + consumer + crypto + energy

data = []
print(f"正在生成 {len(all_tickers)} 只股票的持仓数据...")

for ticker in all_tickers:
    # 随机生成持仓
    qty = random.randint(10, 500)
    # 随机生成成本价 (大致范围)
    if ticker in ['BTC-USD']: base_price = 40000
    elif ticker in ['ETH-USD']: base_price = 2500
    else: base_price = random.uniform(50, 400)
    
    cost_price = base_price * random.uniform(0.8, 1.2)
    
    data.append({
        'Date': '2025-11-30',
        'Ticker': ticker, # 这里不管大小写，app.py 里会统一修正
        'Action': 'Buy',
        'Quantity': qty,
        'Price': round(cost_price, 2)
    })

df = pd.DataFrame(data)
# 保存为 Excel
df.to_excel('portfolio.xlsx', index=False, engine='openpyxl')
print("✅ portfolio.xlsx 已生成！包含大量持仓数据。")