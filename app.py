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

# --- 1. 视觉系统: Living Aurora (呼吸极光) ---
EXTERNAL_STYLES = [
    dbc.themes.CYBORG,
    # 引入字体: Orbitron (科幻), Outfit (几何), JetBrains Mono (代码)
    "https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Outfit:wght@300;500;700&family=JetBrains+Mono:wght@400;700&display=swap"
]

CUSTOM_CSS = """
/* 真正的实时渐变背景逻辑 */
@keyframes living-gradient {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

body {
    /* 使用更加丰富、高饱和度的深色渐变组合 */
    background: linear-gradient(
        -45deg, 
        #020024, /* 深空黑 */
        #090979, /* 深蓝 */
        #2a0845, /* 魅紫 */
        #00d2ff  /* 激光蓝 */
    );
    background-size: 400% 400%;
    /* 40秒一个循环，缓慢呼吸 */
    animation: living-gradient 40s ease infinite;
    
    font-family: 'Outfit', sans-serif;
    color: #fff;
    overflow-x: hidden;
    margin: 0;
}

/* 顶部透明磨砂条 */
.ticker-wrap {
    width: 100%;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(10px);
    height: 35px;
    line-height: 35px;
    white-space: nowrap;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    overflow: hidden;
    position: fixed;
    top: 0;
    z-index: 9999;
}
.ticker-move { display: inline-block; animation: ticker 60s linear infinite; }
.ticker-item { display: inline-block; padding: 0 30px; font-family: 'JetBrains Mono'; font-size: 12px; opacity: 0.8; }
@keyframes ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-100%); } }

/* 玻璃卡片升级版 */
.glass-x {
    background: rgba(255, 255, 255, 0.03); /* 极度通透 */
    backdrop-filter: blur(20px);           /* 强力模糊 */
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    border-radius: 16px;
    position: relative;
    overflow: hidden;
    transition: border 0.3s;
}
.glass-x:hover { border-color: rgba(255, 255, 255, 0.2); }

/* 字体系统 */
.font-sci { font-family: 'Orbitron', sans-serif; letter-spacing: 2px; }
.font-num { font-family: 'JetBrains Mono', monospace; }
.text-cyan { color: #00f3ff; text-shadow: 0 0 15px rgba(0, 243, 255, 0.4); }
.text-green { color: #00ff9d; text-shadow: 0 0 10px rgba(0, 255, 157, 0.4); }
.text-pink { color: #ff0055; text-shadow: 0 0 10px rgba(255, 0, 85, 0.4); }

/* Tab 样式美化 */
.nav-tabs { border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px; }
.nav-link { color: rgba(255,255,255,0.5) !important; border: none !important; font-family: 'Orbitron'; letter-spacing: 1px; transition: color 0.3s; }
.nav-link:hover { color: #fff !important; }
.nav-link.active { 
    background-color: transparent !important; 
    color: #fff !important; 
    border-bottom: 2px solid #00f3ff !important;
    text-shadow: 0 0 10px rgba(0, 243, 255, 0.6);
}

/* 表格样式 */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: rgba(255,255,255,0.05) !important;
    color: #00f3ff !important;
    font-family: 'Orbitron';
    font-weight: 700 !important;
    letter-spacing: 1px;
    border: none !important;
    padding: 15px !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
    background-color: transparent !important;
    color: #eee !important;
    font-family: 'JetBrains Mono';
    border: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    padding: 12px !important;
}
.dash-table-container .previous-next-container .page-number { color: #888 !important; }
.dash-table-container .previous-next-container .page-number.active { color: #00f3ff !important; }
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>AURORA LIVING</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 数据引擎 ---
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

    prices, sectors, betas, caps, changes = [], [], [], [], []
    is_sim = False
    
    try:
        # 强制模拟，保证流畅度
        raise Exception("Force Sim")
    except:
        is_sim = True
        for t in res['Ticker']:
            cost = portfolio[t]['cost']/portfolio[t]['qty']
            prices.append(cost * random.uniform(0.85, 1.4))
            sectors.append(random.choice(['Technology', 'Finance', 'Energy', 'Consumer', 'Crypto']))
            betas.append(random.uniform(0.5, 2.5))
            caps.append(random.uniform(1e9, 2e12))
            changes.append(random.uniform(-0.05, 0.05))

    res['Price'] = prices
    res['Sector'] = sectors
    res['Beta'] = betas
    res['Mkt Cap'] = caps
    res['DayChg'] = changes
    
    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['PnL%'] = res['PnL'] / res['cost']
    res['DayPnL'] = res['Value'] * res['DayChg']
    res['AI_Score'] = [int(x * 100) for x in np.random.uniform(0.3, 0.98, len(res))]
    
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
    
    ticker_items = []
    for _, row in df.iterrows():
        c = "text-green" if row['DayChg'] >= 0 else "text-pink"
        s = "▲" if row['DayChg'] >= 0 else "▼"
        ticker_items.append(html.Span([
            f"{row['Ticker']} ", html.Span(f"{s}{row['DayChg']:.2%}", className=c), " /// "
        ], className="ticker-item"))

    # Tab 1: 主控台
    tab1 = dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("HOLDINGS MATRIX", className="text-cyan font-sci mb-3"),
                dash_table.DataTable(
                    data=df.to_dict('records'),
                    columns=[
                        {'name': 'ASSET', 'id': 'Ticker'},
                        {'name': 'SECTOR', 'id': 'Sector'},
                        {'name': 'BETA', 'id': 'Beta', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                        {'name': 'PRICE', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                        {'name': 'VALUE', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                        {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                    ],
                    page_size=8,
                    sort_action="native",
                    filter_action="native",
                    style_as_list_view=True,
                    style_data_conditional=[
                        {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#00ff9d', 'fontWeight': 'bold'},
                        {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#ff0055', 'fontWeight': 'bold'},
                    ]
                )
            ], className="glass-x p-4 h-100")
        ], width=12, lg=7),
        
        dbc.Col([
            html.Div([
                html.H5("ASSET ALLOCATION", className="text-white font-sci mb-3 text-center"),
                dcc.Graph(
                    figure=px.sunburst(df, path=['Sector', 'Ticker'], values='Value', color='PnL%',
                                     color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
                    .update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0)),
                    config={'displayModeBar': False},
                    style={'height': '400px'}
                )
            ], className="glass-x p-4 h-100")
        ], width=12, lg=5)
    ], className="mt-2")

    # Tab 2: 3D 实验室 (字体深度美化)
    # 核心修改：统一使用了 'Outfit' 字体，并调整了颜色，让它看起来不像默认图表
    fig_3d = px.scatter_3d(df, x='Beta', y='PnL%', z='Mkt Cap', color='Sector', size='Value',
                           hover_name='Ticker', opacity=0.9)
    
    fig_3d.update_layout(
        template="plotly_dark", 
        paper_bgcolor='rgba(0,0,0,0)',
        # 场景字体美化
        scene=dict(
            xaxis=dict(title='RISK (BETA)', title_font=dict(family='Orbitron', size=14, color='#00f3ff'), tickfont=dict(family='JetBrains Mono')),
            yaxis=dict(title='RETURN (ROI)', title_font=dict(family='Orbitron', size=14, color='#00ff9d'), tickfont=dict(family='JetBrains Mono')),
            zaxis=dict(title='SIZE (CAP)', title_font=dict(family='Orbitron', size=14, color='#ff0055'), tickfont=dict(family='JetBrains Mono')),
            bgcolor='rgba(0,0,0,0)' # 透明背景
        ),
        font=dict(family="Outfit", size=12), # 全局字体
        margin=dict(l=0, r=0, b=0, t=20), 
        height=500,
        legend=dict(font=dict(family='Outfit', size=12))
    )
    
    tab2 = html.Div([dcc.Graph(figure=fig_3d)], className="glass-x p-3 mt-2")

    # Tab 3: AI 仪表盘
    top_stocks = df.head(3)
    gauges = []
    for _, row in top_stocks.iterrows():
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number", value = row['AI_Score'],
            title = {'text': f"{row['Ticker']} SENTIMENT", 'font': {'family': 'Orbitron', 'size': 16}},
            number = {'font': {'family': 'JetBrains Mono'}},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#00f3ff"},
                     'steps': [{'range': [0, 50], 'color': "rgba(255,0,0,0.1)"}, {'range': [50, 100], 'color': "rgba(0,255,0,0.1)"}]}
        ))
        fig_g.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=220, margin=dict(l=20,r=20,t=40,b=20))
        gauges.append(dbc.Col(dcc.Graph(figure=fig_g), width=12, md=4))
    
    tab3 = dbc.Row(gauges, className="mt-2 glass-x p-4")

    # --- 最终架构 ---
    return html.Div([
        html.Div(html.Div(ticker_items * 5, className="ticker-move"), className="ticker-wrap"),
        
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1(["AURORA", html.Span(" LIVING", style={'color':'#00f3ff', 'fontWeight':'300'})], className="font-sci mb-0"),
                    html.P(f"SYSTEM TIME: {datetime.now().strftime('%H:%M:%S')} | MODE: {'SIMULATION' if is_sim else 'LIVE'}", 
                           className="font-num text-muted", style={'fontSize':'12px'})
                ], className="text-center mt-5 mb-4")
            ]),

            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("NET ASSETS", className="text-muted font-sci", style={'fontSize':'10px'}),
                    html.Div(f"${kpi['val']:,.0f}", className="font-num", style={'fontSize':'32px', 'color':'#fff'})
                ], className="glass-x p-3 text-center"), width=6, lg=3),
                dbc.Col(html.Div([
                    html.Div("TOTAL ROI", className="text-muted font-sci", style={'fontSize':'10px'}),
                    html.Div(f"{kpi['roi']:+.2%}", className="font-num", style={'fontSize':'32px', 'color': '#00ff9d' if kpi['roi']>0 else '#ff0055'})
                ], className="glass-x p-3 text-center"), width=6, lg=3),
                dbc.Col(html.Div([
                    html.Div("UNREALIZED PNL", className="text-muted font-sci", style={'fontSize':'10px'}),
                    html.Div(f"${kpi['pnl']:+,.0f}", className="font-num", style={'fontSize':'32px', 'color': '#00ff9d' if kpi['pnl']>0 else '#ff0055'})
                ], className="glass-x p-3 text-center"), width=6, lg=3),
                dbc.Col(html.Div([
                    html.Div("DAY CHANGE", className="text-muted font-sci", style={'fontSize':'10px'}),
                    html.Div(f"${kpi['day']:+,.0f}", className="font-num", style={'fontSize':'32px', 'color': '#00ff9d' if kpi['day']>0 else '#ff0055'})
                ], className="glass-x p-3 text-center"), width=6, lg=3),
            ], className="mb-2"),

            dbc.Tabs([
                dbc.Tab(tab1, label="COMMAND CENTER"),
                dbc.Tab(tab2, label="3D QUANTUM LAB"),
                dbc.Tab(tab3, label="AI SENTIMENT"),
            ], className="font-sci"),

        ], fluid=True, style={'paddingTop': '40px'})
    ])

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)