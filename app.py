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

# --- 1. 字体与视觉系统: 金融精英版 (Elite Finance) ---
EXTERNAL_STYLES = [
    dbc.themes.BOOTSTRAP,
    # 核心升级：引入 Playfair(老钱风), Oswald(力量感), IBM Plex Mono(专业数据), Inter(UI)
    "https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,700&family=Oswald:wght@400;600&family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@300;500&display=swap"
]

CUSTOM_CSS = """
/* 动态背景：更深邃、更冷静的极光 */
@keyframes elite-flow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

body {
    /* 深蓝、炭黑、皇家紫 */
    background: linear-gradient(-45deg, #050505, #0f172a, #1e1b4b, #020617);
    background-size: 400% 400%;
    animation: elite-flow 30s ease infinite;
    font-family: 'Inter', sans-serif;
    color: #e2e8f0;
    overflow-x: hidden;
    margin: 0;
}

/* 顶部行情条 */
.ticker-bar {
    position: fixed; top: 0; width: 100%; height: 36px;
    background: rgba(0,0,0,0.85); 
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    z-index: 999; display: flex; align-items: center; white-space: nowrap; overflow: hidden;
}
.ticker-content { display: inline-block; animation: scroll 50s linear infinite; }
.ticker-item { font-family: 'IBM Plex Mono'; font-weight: 600; font-size: 13px; margin: 0 25px; color: #cbd5e1; letter-spacing: -0.5px; }
@keyframes scroll { 0% {transform: translateX(0);} 100% {transform: translateX(-100%);} }

/* 玻璃卡片：更锋利的边缘，更薄的质感 */
.glass-panel {
    background: rgba(20, 25, 35, 0.7);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 4px; /* 直角微圆，更硬朗 */
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    transition: border 0.3s ease;
}
.glass-panel:hover { border-color: rgba(255, 255, 255, 0.25); }

/* --- 字体分层设计 (核心) --- */
.font-brand { 
    font-family: 'Playfair Display', serif; 
    font-weight: 700; 
    font-style: italic; 
    letter-spacing: 1px; 
}
.font-head { 
    font-family: 'Oswald', sans-serif; 
    font-weight: 500; 
    text-transform: uppercase; 
    letter-spacing: 1.5px; 
}
.font-num { 
    font-family: 'IBM Plex Mono', monospace; 
    letter-spacing: -0.5px; 
    font-weight: 500;
}

/* 颜色系统 */
.text-gold { color: #d4af37; text-shadow: 0 0 15px rgba(212, 175, 55, 0.3); } /* 奢华金 */
.text-up { color: #4ade80; } /* 沉稳绿 */
.text-down { color: #fb7185; } /* 柔和红 */

/* Tab 样式 */
.nav-tabs { border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 25px; }
.nav-link { color: #64748b !important; border: none !important; font-family: 'Oswald'; font-size: 1.1rem; letter-spacing: 1px; transition: color 0.3s; }
.nav-link:hover { color: #fff !important; }
.nav-link.active { 
    background: transparent !important; 
    color: #fff !important; 
    border-bottom: 2px solid #d4af37 !important; /* 金色下划线 */
}

/* 表格终极优化 */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background: rgba(255,255,255,0.03) !important; 
    color: #94a3b8 !important;
    font-family: 'Oswald'; 
    font-weight: 600 !important; 
    letter-spacing: 1px;
    border: none !important; 
    padding: 16px !important;
    font-size: 0.9rem;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
    background: transparent !important; 
    color: #e2e8f0 !important;
    font-family: 'IBM Plex Mono'; 
    font-size: 0.9rem; 
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    padding: 12px !important;
}
/* 分页栏 */
.page-number { color: #64748b !important; font-family: 'IBM Plex Mono'; } 
.page-number.active { color: #d4af37 !important; font-weight: bold; }
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>APEX ELITE</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 数据引擎 (Data Engine) ---
def get_data_engine():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    df = pd.DataFrame()
    
    # 读取 Excel
    if os.path.exists(excel_path):
        try: 
            df = pd.read_excel(excel_path, engine='openpyxl')
            df.columns = df.columns.str.strip().str.title()
        except: pass
    
    # 模拟数据 (保障展示效果)
    if df.empty:
        df = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 100, 'Price': 140},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 50, 'Price': 300},
            {'Ticker': 'MSFT', 'Action': 'Buy', 'Quantity': 60, 'Price': 250},
            {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 100, 'Price': 180},
            {'Ticker': 'JPM', 'Action': 'Buy', 'Quantity': 150, 'Price': 140},
            {'Ticker': 'ETH-USD', 'Action': 'Buy', 'Quantity': 10, 'Price': 1800}
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

    # 高级模拟填充
    prices, sectors, betas, caps, changes = [], [], [], [], []
    is_sim = True # 默认开启模拟，保证 PythonAnywhere 免费版不报错
    
    sector_map = {
        'AAPL': 'Technology', 'MSFT': 'Technology', 'NVDA': 'Semiconductors',
        'TSLA': 'Automotive', 'JPM': 'Financial', 'ETH-USD': 'Crypto'
    }
    
    for t in res['Ticker']:
        cost = portfolio[t]['cost']/portfolio[t]['qty']
        prices.append(cost * random.uniform(0.85, 1.45))
        sectors.append(sector_map.get(t, random.choice(['Energy', 'Healthcare', 'Consumer'])))
        betas.append(random.uniform(0.6, 2.2))
        caps.append(random.uniform(10e9, 3000e9))
        changes.append(random.uniform(-0.04, 0.04))

    res['Price'] = prices
    res['Sector'] = sectors
    res['Beta'] = betas
    res['Mkt Cap'] = caps
    res['DayChg'] = changes
    
    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['PnL%'] = res['PnL'] / res['cost']
    res['DayPnL'] = res['Value'] * res['DayChg']
    res['AI_Score'] = [int(x * 100) for x in np.random.uniform(0.35, 0.99, len(res))]
    
    res = res.sort_values('Value', ascending=False)
    return res, is_sim

# --- 3. 页面布局 ---
def serve_layout():
    df, is_sim = get_data_engine()
    
    kpi = {
        'val': df['Value'].sum(),
        'pnl': df['PnL'].sum(),
        'roi': df['PnL'].sum()/df['cost'].sum() if df['cost'].sum() else 0,
        'day': df['DayPnL'].sum()
    }
    
    # 跑马灯
    ticker_items = []
    for _, row in df.iterrows():
        c = "text-up" if row['DayChg'] >= 0 else "text-down"
        s = "▲" if row['DayChg'] >= 0 else "▼"
        ticker_items.append(html.Span([
            f"{row['Ticker']} ", html.Span(f"{s}{row['DayChg']:.2%}", className=c), "  /  "
        ], className="ticker-item"))

    # Tab 1: 主控台 (表格 + 矩形树图)
    tab1 = dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("HOLDINGS LEDGER", className="font-head text-gold mb-3"),
                dash_table.DataTable(
                    data=df.to_dict('records'),
                    columns=[
                        {'name': 'ASSET', 'id': 'Ticker'},
                        {'name': 'SECTOR', 'id': 'Sector'},
                        {'name': 'BETA', 'id': 'Beta', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                        {'name': 'PRICE', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                        {'name': 'VALUE', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                        {'name': 'PNL', 'id': 'PnL', 'type': 'numeric', 'format': {'specifier': '+,.0f'}},
                        {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                    ],
                    page_size=8,
                    sort_action="native",
                    filter_action="native",
                    style_as_list_view=True,
                    style_data_conditional=[
                        {'if': {'filter_query': '{PnL} >= 0', 'column_id': 'PnL'}, 'color': '#4ade80', 'fontWeight': '600'},
                        {'if': {'filter_query': '{PnL} < 0', 'column_id': 'PnL'}, 'color': '#fb7185', 'fontWeight': '600'},
                        {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#4ade80'},
                        {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#fb7185'},
                    ]
                )
            ], className="glass-panel p-4 h-100")
        ], width=12, lg=7),
        
        dbc.Col([
            html.Div([
                html.H5("SECTOR EXPOSURE", className="font-head text-white mb-3 text-center"),
                dcc.Graph(
                    figure=px.treemap(df, path=['Sector', 'Ticker'], values='Value', color='PnL%',
                                    color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
                    .update_layout(
                        template="plotly_dark", 
                        paper_bgcolor='rgba(0,0,0,0)', 
                        margin=dict(t=0, b=0, l=0, r=0),
                        font=dict(family='Inter', size=12)
                    ),
                    config={'displayModeBar': False}, style={'height': '400px'}
                )
            ], className="glass-panel p-4 h-100")
        ], width=12, lg=5)
    ], className="mt-2")

    # Tab 2: 3D 实验室 (字体深度美化)
    # 使用 Oswald 做标题，IBM Plex Mono 做刻度，极具专业感
    fig_3d = px.scatter_3d(df, x='Beta', y='PnL%', z='Mkt Cap', color='Sector', size='Value',
                           hover_name='Ticker', opacity=0.9)
    fig_3d.update_layout(
        template="plotly_dark", 
        paper_bgcolor='rgba(0,0,0,0)',
        scene=dict(
            xaxis=dict(title='BETA (RISK)', title_font=dict(family='Oswald', size=14, color='#94a3b8'), tickfont=dict(family='IBM Plex Mono')),
            yaxis=dict(title='ROI (RETURN)', title_font=dict(family='Oswald', size=14, color='#94a3b8'), tickfont=dict(family='IBM Plex Mono')),
            zaxis=dict(title='CAP (SIZE)', title_font=dict(family='Oswald', size=14, color='#94a3b8'), tickfont=dict(family='IBM Plex Mono')),
            bgcolor='rgba(0,0,0,0)'
        ),
        font=dict(family="Inter", size=12),
        margin=dict(l=0, r=0, b=0, t=20), height=500
    )
    tab2 = html.Div([dcc.Graph(figure=fig_3d)], className="glass-panel p-3 mt-2")

    # Tab 3: AI 仪表盘
    top_stocks = df.head(3)
    gauges = []
    for _, row in top_stocks.iterrows():
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number", value = row['AI_Score'],
            title = {'text': f"{row['Ticker']} SENTIMENT", 'font': {'family': 'Oswald', 'size': 18}},
            number = {'font': {'family': 'IBM Plex Mono', 'size': 40}},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#d4af37"}, # 金色指针
                     'steps': [{'range': [0, 100], 'color': "rgba(255,255,255,0.05)"}]}
        ))
        fig_g.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=220, margin=dict(l=20,r=20,t=40,b=20))
        gauges.append(dbc.Col(dcc.Graph(figure=fig_g), width=12, md=4))
    
    tab3 = dbc.Row(gauges, className="mt-2 glass-panel p-4")

    # --- 最终页面 ---
    return html.Div([
        # 1. 顶部行情
        html.Div(html.Div(ticker_items * 5, className="ticker-content"), className="ticker-bar"),
        
        dbc.Container([
            # 2. 标题区
            dbc.Row([
                dbc.Col([
                    html.H1(["APEX", html.Span(" PRIVATE", style={'color':'#d4af37', 'fontWeight':'400', 'fontStyle':'italic'})], className="text-center font-brand mb-2"),
                    html.P(f"SYSTEM TIME: {datetime.now().strftime('%H:%M:%S UTC')}  //  DATA STREAM: {'SIMULATED' if is_sim else 'LIVE'}", 
                           className="text-center font-num", style={'color':'#64748b', 'fontSize':'11px', 'letterSpacing':'1px'})
                ], className="mt-5 mb-4")
            ]),

            # 3. 核心 KPI (抬头显示 HUD)
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("Net Asset Value", className="font-head mb-1", style={'color':'#94a3b8', 'fontSize':'0.7rem'}),
                    html.Div(f"${kpi['val']:,.0f}", className="font-num", style={'fontSize':'2.5rem', 'color':'#fff', 'fontWeight':'600'})
                ], className="glass-panel p-3 text-center h-100"), width=6, lg=3),
                dbc.Col(html.Div([
                    html.Div("Total Return", className="font-head mb-1", style={'color':'#94a3b8', 'fontSize':'0.7rem'}),
                    html.Div(f"{kpi['roi']:+.2%}", className="font-num", style={'fontSize':'2.5rem', 'color': '#4ade80' if kpi['roi']>0 else '#fb7185'})
                ], className="glass-panel p-3 text-center h-100"), width=6, lg=3),
                dbc.Col(html.Div([
                    html.Div("Unrealized PnL", className="font-head mb-1", style={'color':'#94a3b8', 'fontSize':'0.7rem'}),
                    html.Div(f"${kpi['pnl']:+,.0f}", className="font-num", style={'fontSize':'2.5rem', 'color': '#4ade80' if kpi['pnl']>0 else '#fb7185'})
                ], className="glass-panel p-3 text-center h-100"), width=6, lg=3),
                dbc.Col(html.Div([
                    html.Div("Day Change", className="font-head mb-1", style={'color':'#94a3b8', 'fontSize':'0.7rem'}),
                    html.Div(f"${kpi['day']:+,.0f}", className="font-num", style={'fontSize':'2.5rem', 'color': '#4ade80' if kpi['day']>0 else '#fb7185'})
                ], className="glass-panel p-3 text-center h-100"), width=6, lg=3),
            ], className="mb-2"),

            # 4. Tabs
            dbc.Tabs([
                dbc.Tab(tab1, label="OVERVIEW"),
                dbc.Tab(tab2, label="QUANTUM LAB"),
                dbc.Tab(tab3, label="AI SENTIMENT"),
            ], className="font-head"),

        ], fluid=True, style={'paddingTop': '50px', 'paddingBottom': '50px'})
    ])

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)