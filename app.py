import dash
from dash import dcc, html, dash_table, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import os
import random
import numpy as np
from datetime import datetime

# --- 1. 视觉系统: 极光 X (Aurora X) ---
EXTERNAL_STYLES = [
    dbc.themes.CYBORG,
    "https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&family=JetBrains+Mono:wght@400;700&display=swap"
]

CUSTOM_CSS = """
/* 全局动态背景 - 深邃宇宙 */
body {
    background: radial-gradient(circle at 50% -20%, #2b1055, #7597de 100%);
    background-color: #050505;
    font-family: 'Rajdhani', sans-serif;
    color: #fff;
    overflow-x: hidden;
    margin: 0;
}

/* 顶部滚动行情条 */
.ticker-wrap {
    width: 100%;
    background: rgba(0,0,0,0.8);
    height: 35px;
    line-height: 35px;
    white-space: nowrap;
    border-bottom: 1px solid rgba(0, 255, 255, 0.2);
    overflow: hidden;
    position: fixed;
    top: 0;
    z-index: 9999;
}
.ticker-move { display: inline-block; animation: ticker 40s linear infinite; }
.ticker-item { display: inline-block; padding: 0 30px; font-family: 'JetBrains Mono'; font-size: 12px; }
@keyframes ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-100%); } }

/* 玻璃卡片 X */
.glass-x {
    background: rgba(18, 18, 28, 0.65);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    border-radius: 12px;
    position: relative;
    overflow: hidden;
}
/* 卡片光晕动画 */
.glass-x::after {
    content: '';
    position: absolute;
    top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.03) 0%, transparent 70%);
    transform: rotate(30deg);
    pointer-events: none;
}

/* 字体系统 */
.font-sci { font-family: 'Orbitron', sans-serif; letter-spacing: 2px; }
.font-data { font-family: 'JetBrains Mono', monospace; }
.text-neon-blue { color: #00f3ff; text-shadow: 0 0 10px rgba(0, 243, 255, 0.5); }
.text-neon-pink { color: #ff0055; text-shadow: 0 0 10px rgba(255, 0, 85, 0.5); }
.text-neon-green { color: #00ff9d; text-shadow: 0 0 10px rgba(0, 255, 157, 0.5); }

/* Tab 样式重写 */
.nav-tabs { border-bottom: 1px solid rgba(255,255,255,0.1); }
.nav-link { color: #888 !important; border: none !important; font-family: 'Orbitron'; letter-spacing: 1px; }
.nav-link.active { 
    background-color: transparent !important; 
    color: #fff !important; 
    border-bottom: 2px solid #00f3ff !important;
    text-shadow: 0 0 15px #00f3ff;
}

/* 修复表格 */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: rgba(0,243,255,0.05) !important;
    color: #00f3ff !important;
    font-family: 'Orbitron';
    text-transform: uppercase;
    border: none !important;
    font-weight: 900 !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
    background-color: transparent !important;
    color: #eee !important;
    font-family: 'JetBrains Mono';
    border: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
}
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>AURORA X</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 数据引擎 (保留强健逻辑) ---
def get_data_engine():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    df = pd.DataFrame()
    
    if os.path.exists(excel_path):
        try: 
            df = pd.read_excel(excel_path, engine='openpyxl')
            df.columns = df.columns.str.strip().str.title()
        except: pass
    
    if df.empty:
        df = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 50, 'Price': 140},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 20, 'Price': 380},
            {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 60, 'Price': 190},
            {'Ticker': 'MSFT', 'Action': 'Buy', 'Quantity': 30, 'Price': 260}
        ])

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

    prices, sectors, betas, caps = [], [], [], []
    is_sim = False
    try:
        data = yf.Tickers(' '.join(res['Ticker'].tolist()))
        for t in res['Ticker']:
            info = data.tickers[t].info
            p = info.get('currentPrice') or info.get('regularMarketPrice')
            if not p: raise Exception
            prices.append(p)
            sectors.append(info.get('sector', 'Unknown'))
            betas.append(info.get('beta', 1.0))
            caps.append(info.get('marketCap', 1e9))
    except:
        is_sim = True
        for t in res['Ticker']:
            prices.append((portfolio[t]['cost']/portfolio[t]['qty']) * random.uniform(0.92, 1.25))
            sectors.append(random.choice(['Tech', 'Finance', 'Energy', 'Auto']))
            betas.append(random.uniform(0.8, 2.5))
            caps.append(random.uniform(1e10, 2e12))

    res['Price'] = prices
    res['Sector'] = sectors
    res['Beta'] = betas
    res['Mkt Cap'] = caps
    
    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['PnL%'] = res['PnL'] / res['cost']
    res['DayChg'] = np.random.uniform(-0.03, 0.03, len(res)) # 模拟日涨跌
    res['DayPnL'] = res['Value'] * res['DayChg']
    
    # 模拟 AI 情感评分 (0-100)
    res['AI_Score'] = [int(x * 100) for x in np.random.uniform(0.3, 0.95, len(res))]
    
    return res, is_sim

# --- 3. 布局设计 ---
def serve_layout():
    df, is_sim = get_data_engine()
    
    # 汇总数据
    kpi = {
        'val': df['Value'].sum(),
        'pnl': df['PnL'].sum(),
        'roi': df['PnL'].sum()/df['cost'].sum() if df['cost'].sum() else 0,
        'day': df['DayPnL'].sum()
    }
    
    # 滚动条内容
    ticker_items = []
    for _, row in df.iterrows():
        c = "text-neon-green" if row['DayChg'] >= 0 else "text-neon-pink"
        s = "▲" if row['DayChg'] >= 0 else "▼"
        ticker_items.append(html.Span([
            f"{row['Ticker']} ", html.Span(f"{s}{row['DayChg']:.2%}", className=c), " /// "
        ], className="ticker-item"))

    # Tab 1: 指挥塔 (Table + Sunburst)
    tab1_content = dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("HOLDINGS MATRIX", className="text-neon-blue font-sci mb-3"),
                dash_table.DataTable(
                    data=df.to_dict('records'),
                    columns=[
                        {'name': 'ASSET', 'id': 'Ticker'},
                        {'name': 'SECTOR', 'id': 'Sector'},
                        {'name': 'PRICE', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                        {'name': 'VALUE', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                        {'name': 'PNL', 'id': 'PnL', 'type': 'numeric', 'format': {'specifier': '+,.0f'}},
                        {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                    ],
                    style_as_list_view=True,
                    sort_action='native',
                    style_data_conditional=[
                        {'if': {'filter_query': '{PnL} >= 0', 'column_id': 'PnL'}, 'color': '#00ff9d', 'fontWeight': 'bold'},
                        {'if': {'filter_query': '{PnL} < 0', 'column_id': 'PnL'}, 'color': '#ff0055', 'fontWeight': 'bold'},
                        {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#00ff9d'},
                        {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#ff0055'},
                    ]
                )
            ], className="glass-x p-4 h-100")
        ], width=12, lg=7),
        
        dbc.Col([
            html.Div([
                html.H5("SECTOR ALLOCATION", className="text-white font-sci mb-3 text-center"),
                dcc.Graph(
                    figure=px.sunburst(df, path=['Sector', 'Ticker'], values='Value', color='PnL%',
                                     color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
                    .update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0)),
                    config={'displayModeBar': False},
                    style={'height': '350px'}
                )
            ], className="glass-x p-4 h-100")
        ], width=12, lg=5)
    ], className="mt-4")

    # Tab 2: 3D 量子实验室 (3D Scatter)
    fig_3d = px.scatter_3d(df, x='Beta', y='PnL%', z='Mkt Cap', color='Sector', size='Value',
                           hover_name='Ticker', opacity=0.9, title="3D RISK / REWARD / SIZE ANALYZER")
    fig_3d.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', scene=dict(
        xaxis_title='BETA (RISK)', yaxis_title='ROI (REWARD)', zaxis_title='MKT CAP'), margin=dict(l=0, r=0, b=0, t=30), height=500)

    tab2_content = dbc.Row([
        dbc.Col(html.Div([dcc.Graph(figure=fig_3d)], className="glass-x p-3 mt-4"), width=12)
    ])

    # Tab 3: AI 情绪 (Gauge Charts)
    # 选取前3大持仓做仪表盘
    top_3 = df.nlargest(3, 'Value')
    gauges = []
    for _, row in top_3.iterrows():
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number", value = row['AI_Score'],
            title = {'text': f"{row['Ticker']} AI SCORE"},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#00f3ff"},
                     'steps': [{'range': [0, 50], 'color': "rgba(255,0,0,0.2)"}, {'range': [50, 100], 'color': "rgba(0,255,0,0.2)"}]}
        ))
        fig_g.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=20,r=20,t=50,b=20))
        gauges.append(dbc.Col(dcc.Graph(figure=fig_g), width=12, md=4))

    tab3_content = dbc.Row(gauges, className="mt-4 glass-x p-4")

    # --- 最终页面 ---
    return html.Div([
        # 1. 顶部行情
        html.Div(html.Div(ticker_items * 5, className="ticker-move"), className="ticker-wrap"),
        
        # 2. 主体容器
        dbc.Container([
            # 标题与时间
            dbc.Row([
                dbc.Col([
                    html.H1(["AURORA", html.Span(" X", style={'color':'#00f3ff'})], className="font-sci mb-0"),
                    html.P(f"SYSTEM TIME: {datetime.now().strftime('%H:%M:%S UTC')} | MODE: {'SIMULATION' if is_sim else 'LIVE'}", 
                           className="font-data text-muted", style={'fontSize':'12px'})
                ], className="text-center mt-5 mb-4")
            ]),

            # 核心 KPI HUD
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("NET ASSETS", className="text-muted font-sci", style={'fontSize':'10px'}),
                    html.Div(f"${kpi['val']:,.0f}", className="font-data", style={'fontSize':'36px', 'color':'#fff'})
                ], className="glass-x p-3 text-center"), width=6, lg=3),
                dbc.Col(html.Div([
                    html.Div("TOTAL ROI", className="text-muted font-sci", style={'fontSize':'10px'}),
                    html.Div(f"{kpi['roi']:+.2%}", className="font-data", style={'fontSize':'36px', 'color': '#00ff9d' if kpi['roi']>0 else '#ff0055'})
                ], className="glass-x p-3 text-center"), width=6, lg=3),
                dbc.Col(html.Div([
                    html.Div("UNREALIZED PNL", className="text-muted font-sci", style={'fontSize':'10px'}),
                    html.Div(f"${kpi['pnl']:+,.0f}", className="font-data", style={'fontSize':'36px', 'color': '#00ff9d' if kpi['pnl']>0 else '#ff0055'})
                ], className="glass-x p-3 text-center"), width=6, lg=3),
                dbc.Col(html.Div([
                    html.Div("DAY CHANGE", className="text-muted font-sci", style={'fontSize':'10px'}),
                    html.Div(f"${kpi['day']:+,.0f}", className="font-data", style={'fontSize':'36px', 'color': '#00ff9d' if kpi['day']>0 else '#ff0055'})
                ], className="glass-x p-3 text-center"), width=6, lg=3),
            ], className="mb-4"),

            # 功能区 Tabs
            dbc.Tabs([
                dbc.Tab(tab1_content, label="COMMAND CENTER", tab_style={'marginLeft':'auto'}),
                dbc.Tab(tab2_content, label="3D QUANTUM LAB"),
                dbc.Tab(tab3_content, label="AI SENTIMENT"),
            ], className="font-sci"),

        ], fluid=True, style={'paddingTop': '40px'}) # 给顶部滚动条留出空间
    ])

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)