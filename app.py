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

# --- 1. 艺术与架构: 字体 & CSS Grid 系统 ---
EXTERNAL_STYLES = [
    dbc.themes.BOOTSTRAP,
    "https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;500;700&family=Space+Mono:wght@400;700&display=swap"
]

CUSTOM_CSS = """
:root {
    --bg-deep: #050509;
    --glass-surf: rgba(20, 20, 30, 0.6);
    --glass-border: rgba(255, 255, 255, 0.08);
    --neon-cyan: #00f0ff;
    --neon-pink: #ff003c;
    --neon-green: #00ff9f;
    --text-main: #e0e6ed;
    --text-dim: #64748b;
}

body {
    background-color: var(--bg-deep);
    background-image: 
        radial-gradient(circle at 15% 50%, rgba(0, 240, 255, 0.03), transparent 25%),
        radial-gradient(circle at 85% 30%, rgba(255, 0, 60, 0.03), transparent 25%);
    font-family: 'Rajdhani', sans-serif;
    color: var(--text-main);
    overflow-x: hidden; /* 🔒 物理锁死横向滚动 */
    height: 100vh;
    margin: 0;
}

/* 布局框架：CSS Grid (防鬼畜的核心) */
.grid-container {
    display: grid;
    grid-template-columns: 300px 1fr; /* 左侧边栏300px，右侧自适应 */
    grid-template-rows: 80px 1fr;     /* 顶部80px，下方自适应 */
    gap: 20px;
    height: 100vh;
    padding: 20px;
    box-sizing: border-box;
}

/* 玻璃卡片通用样式 */
.monolith-card {
    background: var(--glass-surf);
    backdrop-filter: blur(20px) saturate(120%);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    overflow: hidden;
    position: relative;
    transition: border-color 0.3s;
}
.monolith-card:hover { border-color: rgba(255,255,255,0.15); }

/* 装饰性光条 */
.glow-bar { width: 3px; height: 20px; display: inline-block; margin-right: 10px; border-radius: 2px; }
.glow-cyan { background: var(--neon-cyan); box-shadow: 0 0 10px var(--neon-cyan); }
.glow-pink { background: var(--neon-pink); box-shadow: 0 0 10px var(--neon-pink); }

/* 字体排版 */
.mono-num { font-family: 'Space Mono', monospace; letter-spacing: -1px; }
.label-xs { color: var(--text-dim); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; font-weight: 700; }
.val-xl { font-size: 2.2rem; font-weight: 700; line-height: 1.1; }
.val-lg { font-size: 1.5rem; font-weight: 600; }

/* 表格终极美化 */
.dash-table-container { border: none !important; }
.dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: rgba(0,0,0,0.3) !important;
    color: var(--text-dim) !important;
    font-family: 'Rajdhani', sans-serif !important;
    text-transform: uppercase;
    font-weight: 600;
    border: none !important;
    border-bottom: 1px solid var(--glass-border) !important;
    padding: 15px !important;
}
.dash-spreadsheet-container .dash-spreadsheet-inner td {
    background-color: transparent !important;
    color: var(--text-main) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.9rem;
    border: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.02) !important;
    padding: 12px 15px !important;
}

/* 滚动条美化 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>MONOLITH OS</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 强健数据引擎 ---
def get_data_engine():
    # 路径锁定
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    
    df = pd.DataFrame()
    status = "WAITING"

    # 读取
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path, engine='openpyxl')
            df.columns = df.columns.str.strip().str.title()
            status = "CONNECTED"
        except: pass
    
    # 模拟回退 (Fallback)
    if df.empty:
        status = "SIMULATION"
        df = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 50, 'Price': 140},
            {'Ticker': 'MSFT', 'Action': 'Buy', 'Quantity': 30, 'Price': 250},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 10, 'Price': 450},
            {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 60, 'Price': 200},
            {'Ticker': 'BTC-USD', 'Action': 'Buy', 'Quantity': 0.2, 'Price': 28000}
        ])

    # 逻辑计算
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

    # 价格获取
    prices, sectors = [], []
    try:
        data = yf.Tickers(' '.join(res['Ticker'].tolist()))
        for t in res['Ticker']:
            info = data.tickers[t].info
            p = info.get('currentPrice') or info.get('regularMarketPrice')
            if not p: raise Exception("No Price")
            prices.append(p)
            sectors.append(info.get('sector', 'Unknown'))
    except:
        status = "SIMULATION (OFFLINE)"
        for t in res['Ticker']:
            cost = portfolio[t]['cost']/portfolio[t]['qty']
            # 生成更符合逻辑的模拟波动
            volatility = 0.4 if 'BTC' in t or 'NVDA' in t else 0.15
            prices.append(cost * random.uniform(1 - volatility, 1 + volatility))
            sectors.append('Technology' if t in ['AAPL', 'MSFT'] else 'Crypto' if 'BTC' in t else 'Auto')

    res['Price'] = prices
    res['Sector'] = sectors
    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['PnL%'] = res['PnL'] / res['cost']
    res['Weight'] = res['Value'] / res['Value'].sum()
    
    return res, status

# --- 3. 页面布局 (网格化架构) ---
def serve_layout():
    df, status = get_data_engine()
    
    # 汇总数据
    tot_val = df['Value'].sum()
    tot_pnl = df['PnL'].sum()
    tot_ret = tot_pnl / df['cost'].sum() if df['cost'].sum() else 0
    
    # 颜色
    c_win = "#00ff9f"
    c_loss = "#ff003c"
    
    # 图表 1: 瀑布图 (Waterfall) - 极度专业
    # 展示每个资产对总盈亏的贡献
    df_sorted = df.sort_values('PnL', ascending=False)
    fig_waterfall = go.Figure(go.Waterfall(
        name = "PnL", orientation = "v",
        measure = ["relative"] * len(df),
        x = df_sorted['Ticker'],
        textposition = "outside",
        text = [f"${x/1000:.1f}k" for x in df_sorted['PnL']],
        y = df_sorted['PnL'],
        connector = {"line": {"color": "rgba(255,255,255,0.2)"}},
        decreasing = {"marker": {"color": c_loss}},
        increasing = {"marker": {"color": c_win}},
        totals = {"marker": {"color": "#ffffff"}}
    ))
    fig_waterfall.update_layout(
        title={"text": "PnL ATTRIBUTION ANALYZER", "font": {"color": "#64748b", "size": 12, "family": "Rajdhani"}},
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, tickfont=dict(family='Space Mono')),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(family='Space Mono')),
        margin=dict(t=40, b=20, l=40, r=20), height=280
    )

    # 图表 2: 旭日图 (Sunburst)
    fig_sun = px.sunburst(df, path=['Sector', 'Ticker'], values='Value', color='PnL%',
                          color_continuous_scale='Bluered_r', color_continuous_midpoint=0)
    fig_sun.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0), height=250)

    # --- 网格布局结构 ---
    return html.Div([
        
        # 1. 侧边栏 (Sidebar)
        html.Div([
            html.H2("MONOLITH", style={'fontWeight':900, 'letterSpacing':'4px', 'color':'#fff', 'marginBottom':'40px'}),
            
            # KPI 组
            html.Div([
                html.Div([html.Span(className="glow-bar glow-cyan"), "NET LIQUIDITY"], className="label-xs mb-2"),
                html.Div(f"${tot_val:,.2f}", className="val-xl mono-num text-white mb-4"),
                
                html.Div([html.Span(className="glow-bar glow-pink"), "UNREALIZED PnL"], className="label-xs mb-2"),
                html.Div(f"{tot_pnl:+,.2f}", className="val-lg mono-num mb-4", style={'color': c_win if tot_pnl>0 else c_loss}),
                
                html.Div("RETURN ROI", className="label-xs mb-2"),
                html.Div(f"{tot_ret:+.2%}", className="val-lg mono-num", style={'color': c_win if tot_ret>0 else c_loss}),
            ], className="monolith-card p-4 mb-4"),

            # 状态指示
            html.Div([
                html.Span("SYSTEM STATUS", className="label-xs"),
                html.Div(f"● {status}", className="mt-2 mono-num", style={'color': c_win if 'CONNECTED' in status else '#f59e0b', 'fontSize':'0.8rem'})
            ], className="monolith-card p-3")

        ], style={'gridArea': '1 / 1 / 3 / 2'}), # 占据左侧全高

        # 2. 顶部主图 (Top Chart)
        html.Div([
            dcc.Graph(figure=fig_waterfall, config={'displayModeBar': False})
        ], className="monolith-card p-3", style={'gridArea': '1 / 2 / 2 / 3'}), # 占据右上区域

        # 3. 底部区域 (Split View)
        html.Div([
            # 左下：持仓表 (固定高度，内部滚动，防止鬼畜)
            html.Div([
                html.Div("ACTIVE HOLDINGS", className="label-xs mb-3 px-2"),
                html.Div([
                    dash_table.DataTable(
                        data=df.to_dict('records'),
                        columns=[
                            {'name': 'ASSET', 'id': 'Ticker'},
                            {'name': 'PRICE', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                            {'name': 'VALUE', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                            {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '+.1%'}},
                        ],
                        style_as_list_view=True,
                        style_header={'borderBottom': '2px solid rgba(255,255,255,0.1)'},
                        style_data_conditional=[
                            {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': c_win},
                            {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': c_loss},
                        ]
                    )
                ], style={'overflowY': 'auto', 'height': '100%'}) # 关键：内部滚动
            ], className="monolith-card p-4", style={'width': '65%', 'marginRight':'20px', 'display':'flex', 'flexDirection':'column'}),

            # 右下：扇形图
            html.Div([
                html.Div("SECTOR RISK", className="label-xs mb-2 text-center"),
                dcc.Graph(figure=fig_sun, config={'displayModeBar': False})
            ], className="monolith-card p-3", style={'width': '35%', 'display':'flex', 'flexDirection':'column', 'justifyContent':'center'})

        ], style={'gridArea': '2 / 2 / 3 / 3', 'display': 'flex', 'height': '100%', 'overflow': 'hidden'}) # 弹性盒子

    ], className="grid-container")

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)