import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import os
import random
import numpy as np
from datetime import datetime

# --- 1. 极光 UI 系统 (Aurora Glass UI) ---
EXTERNAL_STYLES = [
    dbc.themes.BOOTSTRAP,
    "https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400&display=swap"
]

CUSTOM_CSS = """
/* 动态极光背景 */
@keyframes aurora {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
body {
    background: linear-gradient(-45deg, #0f172a, #1e1b4b, #312e81, #0f172a);
    background-size: 400% 400%;
    animation: aurora 20s ease infinite;
    font-family: 'DM Sans', sans-serif;
    color: #f8fafc;
    height: 100vh;
    overflow: hidden;
    margin: 0;
}

/* 布局框架 */
.main-grid {
    display: grid;
    grid-template-columns: 260px 1fr;
    grid-template-rows: 70px 1fr;
    gap: 20px;
    height: 100vh;
    padding: 20px;
    box-sizing: border-box;
}

/* 玻璃卡片 */
.glass {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
    overflow: hidden;
}

/* 文字与排版 */
h1, h2, h3, h4 { font-family: 'Outfit', sans-serif; letter-spacing: -0.5px; margin: 0; }
.mono { font-family: 'JetBrains Mono', monospace; }
.label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.5px; color: #94a3b8; font-weight: 600; }
.val-lg { font-size: 2rem; font-weight: 700; color: white; }
.val-md { font-size: 1.2rem; font-weight: 600; }

/* 颜色系统 (视频同款红绿) */
.green { color: #4ade80; text-shadow: 0 0 10px rgba(74, 222, 128, 0.2); }
.red { color: #fb7185; text-shadow: 0 0 10px rgba(251, 113, 133, 0.2); }

/* 表格深度定制 */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: rgba(255,255,255,0.05) !important;
    color: #94a3b8 !important;
    font-family: 'Outfit';
    font-weight: 600 !important;
    border-bottom: 1px solid rgba(255,255,255,0.1) !important;
    text-align: left !important;
    padding: 12px !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
    background-color: transparent !important;
    color: #e2e8f0 !important;
    font-family: 'DM Sans';
    border-bottom: 1px solid rgba(255,255,255,0.02) !important;
    padding: 12px !important;
    font-size: 0.9rem;
}
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>AURORA PRO</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 专业数据引擎 (复刻视频里的所有字段) ---
def get_data_engine():
    # 路径处理
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    
    df = pd.DataFrame()
    
    # A. 读取 Excel
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path, engine='openpyxl')
            df.columns = df.columns.str.strip().str.title()
        except: pass
    
    # B. 默认演示数据 (如果 Excel 挂了)
    if df.empty:
        df = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 100, 'Price': 130},
            {'Ticker': 'MSFT', 'Action': 'Buy', 'Quantity': 50, 'Price': 250},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 20, 'Price': 400},
            {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 100, 'Price': 180},
            {'Ticker': 'AMZN', 'Action': 'Buy', 'Quantity': 50, 'Price': 140},
            {'Ticker': 'GOOGL', 'Action': 'Buy', 'Quantity': 40, 'Price': 120},
        ])

    # C. 计算持仓 (加权平均)
    portfolio = {}
    for _, row in df.iterrows():
        t = str(row['Ticker']).upper().strip()
        q, p, a = float(row['Quantity']), float(row['Price']), str(row['Action']).lower()
        if t not in portfolio: portfolio[t] = {'qty': 0, 'cost': 0}
        if 'buy' in a:
            portfolio[t]['qty'] += q
            portfolio[t]['cost'] += (q * p)
        elif 'sell' in a and portfolio[t]['qty'] > 0:
            avg = portfolio[t]['cost'] / portfolio[t]['qty']
            portfolio[t]['qty'] -= q
            portfolio[t]['cost'] -= (q * avg)
    
    res = pd.DataFrame.from_dict(portfolio, orient='index').reset_index()
    res.rename(columns={'index': 'Ticker'}, inplace=True)
    res = res[res['qty'] > 0].copy()

    # D. 获取高级数据 (API / 模拟)
    is_sim = False
    try:
        # 尝试连接 Yahoo
        data = yf.Tickers(' '.join(res['Ticker'].tolist()))
        prices, sectors, market_caps, betas, day_changes = [], [], [], [], []
        
        for t in res['Ticker']:
            info = data.tickers[t].info
            p = info.get('currentPrice') or info.get('regularMarketPrice')
            if not p: raise Exception
            
            prices.append(p)
            sectors.append(info.get('sector', 'Unknown'))
            market_caps.append(info.get('marketCap', 0))
            betas.append(info.get('beta', 1.0))
            
            prev = info.get('previousClose', p)
            day_changes.append((p - prev)/prev)
            
    except:
        # 模拟模式：生成非常真实的数据
        is_sim = True
        prices, sectors, market_caps, betas, day_changes = [], [], [], [], []
        
        sector_map = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'NVDA': 'Semiconductors',
            'TSLA': 'Auto', 'AMZN': 'Consumer', 'GOOGL': 'Communication'
        }
        
        for t in res['Ticker']:
            # 价格模拟
            cost = portfolio[t]['cost'] / portfolio[t]['qty']
            prices.append(cost * random.uniform(0.9, 1.4))
            # 板块模拟
            sectors.append(sector_map.get(t, random.choice(['Finance', 'Healthcare', 'Energy'])))
            # 市值模拟 (Billions)
            market_caps.append(random.uniform(50e9, 2000e9))
            # Beta 模拟
            betas.append(random.uniform(0.8, 2.5))
            # 日涨跌模拟
            day_changes.append(random.uniform(-0.04, 0.04))

    # E. 组装最终数据表
    res['Price'] = prices
    res['Change%'] = day_changes
    res['Sector'] = sectors
    res['Beta'] = betas
    res['Mkt Cap'] = [f"${x/1e9:.1f}B" for x in market_caps] # 格式化为 Billions
    
    res['Value'] = res['qty'] * res['Price']
    res['Cost'] = res['cost']
    res['Total PnL'] = res['Value'] - res['Cost']
    res['ROI'] = res['Total PnL'] / res['Cost']
    
    # 模拟“今日盈亏” (Value * Day Change)
    res['Day PnL'] = res['Value'] * res['Change%']

    # 汇总
    kpi = {
        'total_val': res['Value'].sum(),
        'total_pnl': res['Total PnL'].sum(),
        'total_roi': res['Total PnL'].sum() / res['Cost'].sum(),
        'day_pnl': res['Day PnL'].sum(),
        'status': "SIMULATION" if is_sim else "LIVE DATA"
    }
    
    return res, kpi

# --- 3. 布局逻辑 ---
def serve_layout():
    df, kpi = get_data_engine()
    
    # 图表：板块热力图 (Treemap)
    fig_tree = px.treemap(df, path=[px.Constant("Portfolio"), 'Sector', 'Ticker'], values='Value',
                          color='ROI', color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
    fig_tree.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0,b=0,l=0,r=0))

    # 图表：Beta vs ROI 散点图 (专业分析)
    fig_risk = px.scatter(df, x='Beta', y='ROI', size='Value', color='Sector',
                          hover_name='Ticker', title="Risk (Beta) vs Return")
    fig_risk.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(255,255,255,0.05)',
                           margin=dict(t=40,b=20,l=20,r=20), height=250)

    return html.Div([
        # 侧边栏
        html.Div([
            html.H3("AURORA", className="text-white mb-1"),
            html.Div("PRO TERMINAL", className="label mb-5"),
            
            # KPI 1: 总资产
            html.Div("NET LIQUIDITY", className="label"),
            html.Div(f"${kpi['total_val']:,.0f}", className="val-lg mb-4 mono"),
            
            # KPI 2: 总盈亏
            html.Div([
                html.Div("TOTAL P/L", className="label"),
                html.Div(f"{kpi['total_pnl']:+,.0f}", className=f"val-md mono {'green' if kpi['total_pnl']>0 else 'red'}"),
                html.Div(f"{kpi['total_roi']:+.2%}", className=f"mono {'green' if kpi['total_roi']>0 else 'red'}", style={'fontSize':'0.9rem'})
            ], className="mb-4"),
            
            # KPI 3: 今日盈亏 (视频核心功能)
            html.Div([
                html.Div("DAY'S P/L", className="label"),
                html.Div(f"{kpi['day_pnl']:+,.0f}", className=f"val-md mono {'green' if kpi['day_pnl']>0 else 'red'}"),
            ], className="mb-4"),
            
            html.Hr(style={'borderColor':'rgba(255,255,255,0.1)'}),
            
            # 状态
            html.Div([
                html.Span("●", className="green" if "LIVE" in kpi['status'] else "red", style={'marginRight':'10px'}),
                html.Span(kpi['status'], className="label")
            ])
            
        ], className="glass", style={'gridArea': '1 / 1 / 3 / 2', 'padding':'30px', 'display':'flex', 'flexDirection':'column'}),

        # 顶部：风险分析图
        html.Div([
            dcc.Graph(figure=fig_risk, config={'displayModeBar': False}, style={'height':'100%'})
        ], className="glass", style={'gridArea': '1 / 2 / 2 / 3', 'padding':'15px'}),

        # 主内容：超级表格
        html.Div([
            html.Div([
                html.H4("Active Holdings", className="text-white"),
                html.Div("Real-time Sector & Risk Analysis", style={'color':'#64748b', 'fontSize':'0.9rem'})
            ], className="mb-3 px-2"),
            
            dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[
                    {'name': 'Ticker', 'id': 'Ticker'},
                    {'name': 'Sector', 'id': 'Sector'},
                    {'name': 'Beta', 'id': 'Beta', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                    {'name': 'Mkt Cap', 'id': 'Mkt Cap'},
                    {'name': 'Price', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                    {'name': '1D %', 'id': 'Change%', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                    {'name': 'Value', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                    {'name': 'Total P/L', 'id': 'Total PnL', 'type': 'numeric', 'format': {'specifier': '+,.0f'}}, # 这里去掉了$
                    {'name': 'ROI', 'id': 'ROI', 'type': 'numeric', 'format': {'specifier': '+.1%'}},
                ],
                style_as_list_view=True,
                style_data_conditional=[
                    # 涨跌颜色逻辑
                    {'if': {'filter_query': '{Total PnL} >= 0', 'column_id': 'Total PnL'}, 'color': '#4ade80', 'fontWeight': 'bold'},
                    {'if': {'filter_query': '{Total PnL} < 0', 'column_id': 'Total PnL'}, 'color': '#fb7185', 'fontWeight': 'bold'},
                    {'if': {'filter_query': '{Change%} >= 0', 'column_id': 'Change%'}, 'color': '#4ade80'},
                    {'if': {'filter_query': '{Change%} < 0', 'column_id': 'Change%'}, 'color': '#fb7185'},
                    {'if': {'filter_query': '{ROI} >= 0', 'column_id': 'ROI'}, 'color': '#4ade80'},
                    {'if': {'filter_query': '{ROI} < 0', 'column_id': 'ROI'}, 'color': '#fb7185'},
                ],
                sort_action="native", # 允许点击表头排序
            )
        ], className="glass", style={'gridArea': '2 / 2 / 3 / 3', 'padding':'20px', 'overflowY':'auto'}),

    ], className="main-grid")

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)