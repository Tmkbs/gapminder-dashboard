import dash
from dash import dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import random

# --- 1. 赛博朋克极致样式 (CSS) ---
CUSTOM_CSS = """
body {
    background-color: #050505;
    background-image: 
        linear-gradient(rgba(0, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 255, 255, 0.03) 1px, transparent 1px);
    background-size: 30px 30px;
    font-family: 'Roboto Mono', monospace;
    color: #e0e0e0;
    overflow-x: hidden;
}
/* 霓虹滚动条 */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #00cc96; border-radius: 4px; }

/* 玻璃卡片 */
.cyber-card {
    background: rgba(16, 20, 25, 0.85);
    border: 1px solid rgba(0, 204, 150, 0.2);
    box-shadow: 0 0 15px rgba(0, 204, 150, 0.05);
    backdrop-filter: blur(10px);
    border-radius: 4px;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.cyber-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; width: 100%; height: 2px;
    background: linear-gradient(90deg, transparent, #00cc96, transparent);
    animation: scanline 3s infinite linear;
}
@keyframes scanline { 0% {transform: translateX(-100%);} 100% {transform: translateX(100%);} }

/* 滚动行情条 */
.ticker-wrap {
    width: 100%;
    background-color: #000;
    border-bottom: 1px solid #333;
    overflow: hidden;
    height: 30px;
    line-height: 30px;
    white-space: nowrap;
}
.ticker-move { display: inline-block; animation: ticker 20s infinite linear; }
.ticker-item { display: inline-block; padding: 0 20px; font-size: 14px; }
@keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
.up { color: #00cc96; } .down { color: #ef553b; }

/* 选项卡样式 */
.custom-tabs .nav-link {
    color: #555 !important;
    border: 1px solid transparent !important;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 2px;
}
.custom-tabs .nav-link.active {
    background-color: transparent !important;
    color: #00cc96 !important;
    border-bottom: 2px solid #00cc96 !important;
    text-shadow: 0 0 10px rgba(0, 204, 150, 0.6);
}
"""

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>QUANTUM TRADER</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 量子模拟引擎 (核心容错) ---
def generate_fake_kline(ticker, days=100):
    """生成逼真的 K 线数据 (防止 API 挂掉时页面空白)"""
    dates = pd.date_range(end=datetime.now(), periods=days)
    base_price = random.uniform(100, 1000)
    data = []
    price = base_price
    for d in dates:
        change = np.random.normal(0, base_price * 0.02)
        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + abs(np.random.normal(0, base_price * 0.01))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, base_price * 0.01))
        vol = int(np.random.uniform(100000, 5000000))
        data.append([d, open_p, high_p, low_p, close_p, vol])
        price = close_p
    df = pd.DataFrame(data, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    return df

def get_data_engine():
    # A. 基础持仓数据
    try:
        df_trans = pd.read_csv('data_transactions.csv')
        df_trans.columns = df_trans.columns.str.strip().str.title()
    except:
        # 默认演示数据
        df_trans = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 100, 'Price': 150},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 50, 'Price': 400},
            {'Ticker': 'BTC-USD', 'Action': 'Buy', 'Quantity': 1, 'Price': 30000},
            {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 200, 'Price': 180},
        ])

    # 汇总持仓
    portfolio = {}
    for _, row in df_trans.iterrows():
        t, q, p, a = row['Ticker'].upper(), row['Quantity'], row['Price'], row['Action'].lower()
        if t not in portfolio: portfolio[t] = {'qty': 0, 'cost': 0}
        if 'buy' in a:
            portfolio[t]['qty'] += q
            portfolio[t]['cost'] += (q * p)
        elif 'sell' in a:
            if portfolio[t]['qty'] > 0:
                avg = portfolio[t]['cost'] / portfolio[t]['qty']
                portfolio[t]['qty'] -= q
                portfolio[t]['cost'] -= (q * avg)
    
    df = pd.DataFrame.from_dict(portfolio, orient='index').reset_index()
    if df.empty: return pd.DataFrame(), 0, 0, 0
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    df = df[df['qty'] > 0].copy()

    # B. 尝试获取实时数据 (带自动降级)
    prices, sectors, changes = [], [], []
    use_simulation = False
    
    try:
        # 这里的 timeout 很关键，PA Free Tier 会在这里卡死
        data = yf.Tickers(' '.join(df['Ticker'].tolist()))
        for t in df['Ticker']:
            info = data.tickers[t].info
            if 'regularMarketPrice' not in info and 'currentPrice' not in info: raise Exception("No Data")
            p = info.get('currentPrice', info.get('regularMarketPrice', 0))
            prices.append(p)
            sectors.append(info.get('sector', 'Tech'))
            prev = info.get('previousClose', p)
            changes.append((p - prev)/prev)
    except:
        use_simulation = True # 触发模拟模式
        for t in df['Ticker']:
            # 生成随机波动价格
            sim_price = (portfolio[t]['cost'] / portfolio[t]['qty']) * random.uniform(0.9, 1.3)
            prices.append(sim_price)
            sectors.append(random.choice(['Technology', 'Crypto', 'Automotive', 'AI']))
            changes.append(random.uniform(-0.05, 0.05))

    df['Price'] = prices
    df['Sector'] = sectors
    df['Change'] = changes
    df['Value'] = df['qty'] * df['Price']
    df['PnL'] = df['Value'] - df['cost']
    df['PnL%'] = df['PnL'] / df['cost']

    return df, df['Value'].sum(), df['PnL'].sum(), (df['PnL'].sum()/df['cost'].sum()), use_simulation

# --- 3. 页面布局 ---
def serve_layout():
    df, tot_val, tot_pnl, tot_ret, is_sim = get_data_engine()
    
    # 顶部滚动条内容
    ticker_html = []
    for _, row in df.iterrows():
        color = "up" if row['Change'] >= 0 else "down"
        arrow = "▲" if row['Change'] >= 0 else "▼"
        ticker_html.append(html.Span(f"{row['Ticker']} ${row['Price']:.2f} {arrow} {row['Change']:.2%}   ///   ", className=f"ticker-item {color}"))
    
    # 状态指示灯
    status_text = "🟢 LIVE DATA CONNECTION" if not is_sim else "🟠 QUANTUM SIMULATION MODE (OFFLINE)"
    status_color = "#00cc96" if not is_sim else "#ffa500"

    return html.Div([
        # 1. 顶部行情条
        html.Div(html.Div(ticker_html * 5, className="ticker-move"), className="ticker-wrap"),

        dbc.Container([
            # 2. 标题区
            dbc.Row([
                dbc.Col([
                    html.H1("QUANTUM // ASSETS", className="mt-4 mb-0", style={'fontWeight': 900, 'letterSpacing': '4px'}),
                    html.P(status_text, style={'color': status_color, 'fontSize': '12px', 'marginTop': '5px', 'opacity': 0.8})
                ], width=12)
            ]),

            # 3. 核心 KPI (玻璃卡片)
            dbc.Row([
                dbc.Col(html.Div([
                    html.H6("TOTAL EQUITY", style={'color': '#888'}),
                    html.H2(f"${tot_val:,.2f}", style={'color': '#fff', 'textShadow': '0 0 15px rgba(255,255,255,0.5)'}),
                ], className="cyber-card p-4"), width=12, lg=4),
                dbc.Col(html.Div([
                    html.H6("UNREALIZED P&L", style={'color': '#888'}),
                    html.H2(f"${tot_pnl:+,.2f}", style={'color': '#00cc96' if tot_pnl>0 else '#ef553b'}),
                ], className="cyber-card p-4"), width=12, lg=4),
                dbc.Col(html.Div([
                    html.H6("PERFORMANCE", style={'color': '#888'}),
                    html.H2(f"{tot_ret:+.2%}", style={'color': '#00cc96' if tot_ret>0 else '#ef553b'}),
                ], className="cyber-card p-4"), width=12, lg=4),
            ], className="mb-2"),

            # 4. 复杂功能 Tabs
            dbc.Tabs([
                # TAB 1: 概览
                dbc.Tab(label="DASHBOARD OVERVIEW", tab_id="tab-1", children=[
                    dbc.Row([
                        dbc.Col(html.Div([
                            html.H5("PORTFOLIO COMPOSITION", className="text-white mb-3"),
                            dcc.Graph(
                                figure=px.sunburst(df, path=['Sector', 'Ticker'], values='Value', color='PnL%', 
                                                 color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
                                .update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0), height=350)
                            )
                        ], className="cyber-card p-3 h-100"), width=12, md=5),
                        
                        dbc.Col(html.Div([
                            html.H5("ASSET PERFORMANCE", className="text-white mb-3"),
                            dcc.Graph(
                                figure=px.bar(df, x='Ticker', y='PnL', color='PnL', color_continuous_scale=['#ef553b', '#00cc96'])
                                .update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False, height=350)
                            )
                        ], className="cyber-card p-3 h-100"), width=12, md=7),
                    ], className="mt-3")
                ]),

                # TAB 2: 技术分析 (K线图)
                dbc.Tab(label="TECHNICAL ANALYSIS", tab_id="tab-2", children=[
                    dbc.Row([
                        dbc.Col(html.Div([
                            html.Div([
                                html.Label("SELECT ASSET:", className="me-2 text-info"),
                                dcc.Dropdown(
                                    id='ticker-select',
                                    options=[{'label': t, 'value': t} for t in df['Ticker']],
                                    value=df['Ticker'].iloc[0] if not df.empty else None,
                                    style={'width': '200px', 'color': '#000'}
                                )
                            ], className="d-flex align-items-center mb-3"),
                            dcc.Graph(id='kline-chart')
                        ], className="cyber-card p-4 mt-3"), width=12)
                    ])
                ])
            ], className="custom-tabs", active_tab="tab-1"),

        ], fluid=True, className="pb-5")
    ])

app.layout = serve_layout

# --- 4. 回调函数：处理 K 线图 ---
@app.callback(
    Output('kline-chart', 'figure'),
    [Input('ticker-select', 'value')]
)
def update_kline(ticker):
    if not ticker: return go.Figure()
    
    # 尝试获取真实历史数据，如果失败则生成模拟数据
    try:
        # 如果是模拟模式，直接跳过 API
        df_k = yf.Ticker(ticker).history(period="6mo")
        if df_k.empty: raise Exception("Empty")
        title_text = f"{ticker} // LIVE MARKET DATA"
    except:
        df_k = generate_fake_kline(ticker, 180) # 生成 180 天模拟数据
        title_text = f"{ticker} // SIMULATED QUANTUM DATA"

    # 画专业的 K 线图
    fig = go.Figure(data=[go.Candlestick(x=df_k.index if 'Date' not in df_k else df_k['Date'],
                open=df_k['Open'], high=df_k['High'], low=df_k['Low'], close=df_k['Close'],
                increasing_line_color='#00cc96', decreasing_line_color='#ef553b')])

    fig.update_layout(
        title=title_text,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_rangeslider_visible=False,
        height=500,
        font={'family': 'Roboto Mono'}
    )
    return fig

if __name__ == '__main__':
    app.run(debug=True)