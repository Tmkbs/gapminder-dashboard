import pandas as pd
import yfinance as yf
import random
from datetime import datetime, timedelta

# --- 配置：你想生成的演示组合 ---
# 这是一个非常典型的科技股投资组合
TARGET_STOCKS = {
    'AAPL': {'shares': 50, 'buy_month_ago': 12},  # 1年前买的苹果
    'NVDA': {'shares': 20, 'buy_month_ago': 8},   # 8个月前买的英伟达
    'MSFT': {'shares': 30, 'buy_month_ago': 6},   # 6个月前买的微软
    'TSLA': {'shares': 40, 'buy_month_ago': 3},   # 3个月前买的特斯拉
    'GOOGL': {'shares': 25, 'buy_month_ago': 10}, # 10个月前买的谷歌
    'AMD':   {'shares': 50, 'buy_month_ago': 5},   # 5个月前买的AMD
    'AMZN':  {'shares': 30, 'buy_month_ago': 11}   # 11个月前买的亚马逊
}

print("正在连接华尔街服务器，抓取历史真实数据...")

transactions = []

# --- 核心逻辑：穿越时间获取真实历史价格 ---
for ticker, config in TARGET_STOCKS.items():
    try:
        # 1. 计算大概的购买日期
        days_ago = config['buy_month_ago'] * 30
        start_date = (datetime.now() - timedelta(days=days_ago + 5)).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        # 2. 从 Yahoo Finance 获取那段时间的历史数据
        stock = yf.Ticker(ticker)
        # 获取那几天的历史记录
        history = stock.history(start=start_date, end=end_date)
        
        if not history.empty:
            # 取第一条数据的收盘价作为成本价
            real_price = round(history.iloc[0]['Close'], 2)
            real_date = history.index[0].strftime('%Y-%m-%d')
            
            # 3. 生成交易记录
            print(f"✅ 模拟交易: 在 {real_date} 以 ${real_price} 买入了 {ticker}...")
            
            transactions.append({
                'Date': real_date,
                'Ticker': ticker,
                'Action': 'Buy',
                'Quantity': config['shares'],
                'Price': real_price
            })
        else:
            print(f"⚠️ 警告: 无法获取 {ticker} 在 {start_date} 的数据，跳过。")
            
    except Exception as e:
        print(f"❌ 错误: 处理 {ticker} 时出错 - {e}")

# --- 添加一笔“卖出”操作演示逻辑 (让数据更好看) ---
# 假设我们最近卖了一点 Apple 获利
try:
    ticker = 'AAPL'
    days_ago = 5 # 5天前
    start_date = (datetime.now() - timedelta(days=days_ago + 5)).strftime('%Y-%m-%d')
    end_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    history = yf.Ticker(ticker).history(start=start_date, end=end_date)
    
    if not history.empty:
        real_price = round(history.iloc[0]['Close'], 2)
        real_date = history.index[0].strftime('%Y-%m-%d')
        print(f"💰 模拟止盈: 在 {real_date} 以 ${real_price} 卖出了部分 {ticker}...")
        
        transactions.append({
            'Date': real_date,
            'Ticker': ticker,
            'Action': 'Sell',
            'Quantity': 5, # 卖出5股
            'Price': real_price
        })
except:
    pass

# --- 保存文件 ---
df = pd.DataFrame(transactions)
# 确保列顺序正确
df = df[['Date', 'Ticker', 'Action', 'Quantity', 'Price']]
df.to_csv('data_transactions.csv', index=False)

print("\n" + "="*50)
print("🎉 成功！真实历史模拟数据已生成至 data_transactions.csv")
print("🚀 现在你可以直接运行 app.py 了！")
print("="*50)