import dash
from dash import dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import random

# --- 1. 样式升级: 现代金融风格 (Modern Fintech) ---
# 引入 Inter 字体，修复页面抖动
EXTERNAL_STYLES = [
    dbc.themes.DARKLY,
    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap"
]

CUSTOM_CSS = """
body {
    background-color: #0b0e11; /* 深邃黑蓝 */
    font-family: 'Inter', sans-serif; /* 顶级UI字体 */
    color: #e0e0e0;
    overflow-x: hidden; /* 🚫 修复鬼畜：禁止横向滚动 */
}

/* 玻璃卡片优化 */
.glass-panel {
    background: rgba(30, 34, 45, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    transition: transform 0.2s;
}
.glass-panel:hover {
    border-color: rgba(255, 255, 255, 0.2);
}

/* 顶部行情条 (修复版) */
.ticker-container {
    width: 100%;
    background: #000;
    border-bottom: 1px solid #333;
    overflow: hidden;
    white-space: nowrap;
    height: 36px;
    display: flex;
    align-items: center;
}
.ticker-content {
    display: inline-block;
    animation: scroll-left 40s linear infinite; /* 放慢速度 */
    padding-left: 100%; /* 从屏幕外开始 */
}
.ticker-item {
    display: inline-block;
    padding: 0 24px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
@keyframes scroll-left {
    0% { transform: translateX(0); }
    100% { transform: translateX(-100%); }
}

/* KPI 文字优化 */
.kpi-label { color: #8b9bb4; font-size: 0.85rem; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
.kpi-value { color: #fff; font-size: 2.2rem; font-weight: 800; letter-spacing: -1px; }

/* 涨跌颜色 */
.text-up { color: #4cd964; } /* 苹果绿 */
.text-down { color: #ff3b30; } /* 警示红 */
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>Fintech Dashboard</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 核心逻辑 (读取 Excel + 模拟引擎) ---
def get_data_engine():
    # A. 读取 Excel (抗造核心)
    try:
        # 使用 openpyxl 引擎读取 xlsx
        df_trans = pd.read_excel('portfolio.xlsx', engine='openpyxl')
        # 再次清洗列名，防止 Excel 里的空格
        df_trans.columns = df_trans.columns.str.strip().str.title()
    except Exception as e:
        print(f"Excel读取失败，启用备用数据: {e}")
        # 如果文件不存在，生成内存数据
        df_trans = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 100, 'Price': 150},
            {'Ticker': 'MSFT', 'Action': 'Buy', 'Quantity': 50, 'Price': 280},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 30, 'Price': 400},
        ])

    # B. 汇总持仓
    portfolio = {}
    for _, row in df_trans.iterrows():
        t = str(row['Ticker']).upper().strip()
        q = float(row['Quantity'])
        p = float(row['Price'])
        a = str(row['Action']).lower()
        
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
    if df.empty: return pd.DataFrame(), 0, 0, 0, True
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    df = df[df['qty'] > 0].copy()

    # C. 获取数据 (优先 API，失败则模拟)
    prices, sectors, changes = [], [], []
    use_simulation = False
    
    try:
        # 尝试连接 Yahoo
        data = yf.Tickers(' '.join(df['Ticker'].tolist()))
        for t in df['Ticker']:
            info = data.tickers[t].info
            p = info.get('currentPrice') or info.get('regularMarketPrice')
            if not p: raise Exception("Price Missing")
            prices.append(p)
            sectors.append(info.get('sector', 'Technology'))
            prev = info.get('previousClose', p)
            changes.append((p - prev)/prev)
    except:
        use_simulation = True
        # 模拟数据生成器
        for t in df['Ticker']:
            cost_price = portfolio[t]['cost'] / portfolio[t]['qty']
            # 随机生成 -10% 到 +30% 的波动
            sim_price = cost_price * random.uniform(0.9, 1.3)
            prices.append(sim_price)
            sectors.append(random.choice(['Technology', 'Financial', 'Healthcare', 'Energy']))
            changes.append(random.uniform(-0.03, 0.03))

    df['Price'] = prices
    df['Sector'] = sectors
    df['Change'] = changes
    df['Value'] = df['qty'] * df['Price']
    df['PnL'] = df['Value'] - df['cost']
    df['PnL%'] = df['PnL'] / df['cost']

    return df, df['Value'].sum(), df['PnL'].sum(), (df['PnL'].sum()/df['cost'].sum() if df['cost'].sum() else 0), use_simulation

# --- 3. 页面组件 ---
def serve_layout():
    df, tot_val, tot_pnl, tot_ret, is_sim = get_data_engine()
    
    # 构建滚动条内容
    ticker_items = []
    for _, row in df.iterrows():
        color_class = "text-up" if row['Change'] >= 0 else "text-down"
        arrow = "▲" if row['Change'] >= 0 else "▼"
        ticker_items.append(html.Span([
            html.Span(f"{row['Ticker']} ", style={'color':'#fff'}),
            html.Span(f"${row['Price']:.2f} "),
            html.Span(f"{arrow} {row['Change']:.2%}", className=color_class),
            html.Span("  ///  ", style={'color':'#333', 'margin': '0 15px'})
        ], className="ticker-item"))
    
    # 状态栏
    status_badge = dbc.Badge("LIVE MARKET", color="success", className="ms-2") if not is_sim else dbc.Badge("SIMULATION MODE", color="warning", className="ms-2")

    return html.Div([
        # 1. 顶部滚动条
        html.Div(html.Div(ticker_items * 3, className="ticker-content"), className="ticker-container"),

        dbc.Container([
            # 2. 头部
            dbc.Row([
                dbc.Col([
                    html.H2(["PORTFOLIO OS", status_badge], className="mt-4 mb-4 text-white", style={'fontWeight': '800'}),
                ], width=12)
            ]),

            # 3. 核心指标 (KPI)
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("Net Asset Value", className="kpi-label"),
                    html.Div(f"${tot_val:,.2f}", className="kpi-value"),
                ], className="glass-panel p-4 h-100"), width=12, md=4, className="mb-3"),
                
                dbc.Col(html.Div([
                    html.Div("Total Profit / Loss", className="kpi-label"),
                    html.Div(f"${tot_pnl:+,.2f}", className=f"kpi-value {'text-up' if tot_pnl>=0 else 'text-down'}"),
                ], className="glass-panel p-4 h-100"), width=12, md=4, className="mb-3"),

                dbc.Col(html.Div([
                    html.Div("Return on Investment", className="kpi-label"),
                    html.Div(f"{tot_ret:+.2%}", className=f"kpi-value {'text-up' if tot_ret>=0 else 'text-down'}"),
                ], className="glass-panel p-4 h-100"), width=12, md=4, className="mb-3"),
            ]),

            # 4. 图表区
            dbc.Row([
                # 左侧：甜甜圈图
                dbc.Col(html.Div([
                    html.H5("Allocation", className="text-white mb-3", style={'fontWeight':'600'}),
                    dcc.Graph(
                        figure=px.pie(df, values='Value', names='Ticker', hole=0.7, 
                                    color_discrete_sequence=px.colors.sequential.RdBu)
                        .update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', 
                                     plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
                                     margin=dict(t=0, b=0, l=0, r=0), height=300)
                        .add_annotation(text=f"${tot_val/1000:.0f}K", font=dict(size=24, color='white', family='Inter'), showarrow=False),
                        config={'displayModeBar': False}
                    )
                ], className="glass-panel p-4 h-100"), width=12, lg=4, className="mb-3"),

                # 右侧：树状热力图
                dbc.Col(html.Div([
                    html.H5("Market Heatmap", className="text-white mb-3", style={'fontWeight':'600'}),
                    dcc.Graph(
                        figure=px.treemap(df, path=[px.Constant("Portfolio"), 'Sector', 'Ticker'], values='Value',
                                        color='PnL%', color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
                        .update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', 
                                     margin=dict(t=0, b=0, l=0, r=0), height=300),
                        config={'displayModeBar': False}
                    )
                ], className="glass-panel p-4 h-100"), width=12, lg=8, className="mb-3"),
            ]),

            # 5. 持仓列表
            dbc.Row([
                dbc.Col(html.Div([
                    html.H5("Active Positions", className="text-white mb-3", style={'fontWeight':'600'}),
                    dash_table.DataTable(
                        data=df.to_dict('records'),
                        columns=[
                            {'name': 'ASSET', 'id': 'Ticker'},
                            {'name': 'PRICE', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                            {'name': 'HOLDING', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                            {'name': 'PNL', 'id': 'PnL', 'type': 'numeric', 'format': {'specifier': '$+,.2f'}},
                            {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                        ],
                        style_as_list_view=True,
                        style_header={'backgroundColor': 'rgba(255,255,255,0.05)', 'color': '#8b9bb4', 'fontWeight': 'bold', 'borderBottom': '1px solid #333'},
                        style_cell={'backgroundColor': 'transparent', 'color': '#e0e0e0', 'fontFamily': 'Inter', 'padding': '12px', 'borderBottom': '1px solid #222'},
                        style_data_conditional=[
                            {'if': {'filter_query': '{PnL} >= 0', 'column_id': 'PnL'}, 'color': '#4cd964', 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{PnL} < 0', 'column_id': 'PnL'}, 'color': '#ff3b30', 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#4cd964'},
                            {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#ff3b30'},
                        ]
                    )
                ], className="glass-panel p-4"), width=12)
            ], className="mb-5")

        ], fluid=True)
    ])

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)