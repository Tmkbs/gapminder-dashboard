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

# --- 1. 视觉系统: Cyber-Renaissance (赛博文艺复兴) ---
EXTERNAL_STYLES = [
    dbc.themes.BOOTSTRAP,
    # 引入 Cinzel (帝王科幻), Rajdhani (硬核科技), JetBrains Mono (代码)
    "https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Rajdhani:wght@500;700&family=JetBrains+Mono:wght@400;700&display=swap"
]

CUSTOM_CSS = """
/* 动态背景：深空流体 */
@keyframes void-flow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

body {
    /* 黑金与深邃宇宙的结合 */
    background: linear-gradient(-45deg, #000000, #0f172a, #1e1b4b, #000000);
    background-size: 400% 400%;
    animation: void-flow 30s ease infinite;
    font-family: 'Rajdhani', sans-serif; /* 默认科技字体 */
    color: #e2e8f0;
    overflow-x: hidden;
    margin: 0;
}

/* 顶部全息条 */
.ticker-bar {
    position: fixed; top: 0; width: 100%; height: 32px;
    background: rgba(10, 10, 16, 0.9); 
    border-bottom: 1px solid rgba(212, 175, 55, 0.3); /* 暗金色边框 */
    z-index: 999; display: flex; align-items: center; white-space: nowrap; overflow: hidden;
    backdrop-filter: blur(5px);
}
.ticker-content { display: inline-block; animation: scroll 50s linear infinite; }
.ticker-item { font-family: 'JetBrains Mono'; font-size: 11px; margin: 0 20px; color: #94a3b8; letter-spacing: 0px; }
@keyframes scroll { 0% {transform: translateX(0);} 100% {transform: translateX(-100%);} }

/* 玻璃卡片 (带防溢出保护) */
.glass-panel {
    background: rgba(15, 20, 30, 0.75);
    backdrop-filter: blur(15px);
    -webkit-backdrop-filter: blur(15px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    border-radius: 6px; /* 更锐利的圆角，符合科幻感 */
    transition: all 0.3s ease;
    overflow: hidden; /* 🔒 核心修复：防止内容溢出 */
}
.glass-panel:hover { 
    border-color: rgba(0, 243, 255, 0.3); /* 悬浮变青色光晕 */
    box-shadow: 0 0 20px rgba(0, 243, 255, 0.1); 
}

/* --- 字体分级系统 (关键) --- */
/* 1. 典雅担当: Cinzel (像星际帝国的徽章) */
.font-royal { font-family: 'Cinzel', serif; letter-spacing: 2px; font-weight: 700; }

/* 2. 先进担当: Rajdhani (像HUD显示器) */
.font-tech { font-family: 'Rajdhani', sans-serif; text-transform: uppercase; letter-spacing: 1px; }

/* 3. 数据担当: JetBrains Mono (绝对理性) */
.font-data { font-family: 'JetBrains Mono', monospace; letter-spacing: -0.5px; }

/* --- 修复溢出的响应式字体 --- */
.kpi-val {
    /* 🔒 核心修复：使用 clamp 动态调整字号，最小1.5rem，最大2.5rem */
    font-size: clamp(1.5rem, 2.5vw, 2.8rem); 
    font-weight: 700;
    white-space: nowrap;       /* 不换行 */
    overflow: hidden;          /* 超出隐藏 */
    text-overflow: ellipsis;   /* 显示省略号 */
    line-height: 1.1;
}

/* 颜色系统 */
.gold-glow { color: #deb887; text-shadow: 0 0 10px rgba(222, 184, 135, 0.3); }
.cyan-glow { color: #00f3ff; text-shadow: 0 0 10px rgba(0, 243, 255, 0.3); }
.red-glow { color: #ff0055; text-shadow: 0 0 10px rgba(255, 0, 85, 0.3); }

/* Tab 样式 */
.nav-tabs { border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px; }
.nav-link { color: #64748b !important; border: none !important; font-family: 'Cinzel'; font-size: 1rem; transition: color 0.3s; }
.nav-link:hover { color: #fff !important; }
.nav-link.active { 
    background: transparent !important; 
    color: #fff !important; 
    border-bottom: 2px solid #00f3ff !important; /* 青色下划线，撞色设计 */
    text-shadow: 0 0 10px rgba(0, 243, 255, 0.5);
}

/* 表格样式 (紧凑型) */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background: rgba(0,0,0,0.3) !important; color: #94a3b8 !important;
    font-family: 'Rajdhani'; font-weight: 700; border: none !important; padding: 12px !important;
    font-size: 0.9rem;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
    background: transparent !important; color: #fff !important;
    font-family: 'JetBrains Mono'; font-size: 0.85rem; border-bottom: 1px solid rgba(255,255,255,0.05) !important;
    padding: 8px 12px !important;
}
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>APEX HORIZON</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 数据引擎 ---
def get_data_engine():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    df = pd.DataFrame()
    
    # 读取
    if os.path.exists(excel_path):
        try: 
            df = pd.read_excel(excel_path, engine='openpyxl')
            df.columns = df.columns.str.strip().str.title()
        except: pass
    
    # 模拟 fallback
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

    # 高级模拟
    prices, sectors, betas, caps, changes = [], [], [], [], []
    is_sim = True
    
    sector_map = {
        'AAPL': 'Tech', 'MSFT': 'Tech', 'NVDA': 'Semi',
        'TSLA': 'Auto', 'JPM': 'Fin', 'ETH-USD': 'Crypto'
    }
    
    for t in res['Ticker']:
        cost = portfolio[t]['cost']/portfolio[t]['qty']
        prices.append(cost * random.uniform(0.85, 1.45))
        sectors.append(sector_map.get(t, random.choice(['Energy', 'Health', 'Retail'])))
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

# --- 3. 布局设计 ---
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
        c = "text-info" if row['DayChg'] >= 0 else "text-danger" # 使用Bootstrap颜色更柔和
        s = "▲" if row['DayChg'] >= 0 else "▼"
        ticker_items.append(html.Span([
            f"{row['Ticker']} ", html.Span(f"{s}{row['DayChg']:.2%}", className=c), "  /  "
        ], className="ticker-item"))

    # Tab 1: 指挥中心
    tab1 = dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("HOLDINGS LEDGER", className="font-tech text-white mb-3", style={'opacity':0.7}),
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
                    page_size=10, # 分页
                    sort_action="native",
                    filter_action="native",
                    style_as_list_view=True,
                    style_data_conditional=[
                        {'if': {'filter_query': '{PnL} >= 0', 'column_id': 'PnL'}, 'color': '#00f3ff'},
                        {'if': {'filter_query': '{PnL} < 0', 'column_id': 'PnL'}, 'color': '#ff0055'},
                        {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#00f3ff'},
                        {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#ff0055'},
                    ]
                )
            ], className="glass-panel p-4 h-100")
        ], width=12, lg=7),
        
        dbc.Col([
            html.Div([
                html.H5("SECTOR ALLOCATION", className="font-tech text-white mb-3 text-center", style={'opacity':0.7}),
                dcc.Graph(
                    figure=px.sunburst(df, path=['Sector', 'Ticker'], values='Value', color='PnL%',
                                     color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
                    .update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0)),
                    config={'displayModeBar': False}, style={'height': '400px'}
                )
            ], className="glass-panel p-4 h-100")
        ], width=12, lg=5)
    ], className="mt-2")

    # Tab 2: 3D 量子实验室 (字体美化版)
    # 使用 Cinzel 做标题，Rajdhani 做轴标，完美结合典雅与科幻
    fig_3d = px.scatter_3d(df, x='Beta', y='PnL%', z='Mkt Cap', color='Sector', size='Value',
                           hover_name='Ticker', opacity=0.9)
    fig_3d.update_layout(
        template="plotly_dark", 
        paper_bgcolor='rgba(0,0,0,0)',
        scene=dict(
            xaxis=dict(title='RISK (BETA)', title_font=dict(family='Cinzel', size=12, color='#94a3b8'), tickfont=dict(family='Rajdhani')),
            yaxis=dict(title='RETURN (ROI)', title_font=dict(family='Cinzel', size=12, color='#94a3b8'), tickfont=dict(family='Rajdhani')),
            zaxis=dict(title='CAP (SIZE)', title_font=dict(family='Cinzel', size=12, color='#94a3b8'), tickfont=dict(family='Rajdhani')),
            bgcolor='rgba(0,0,0,0)'
        ),
        font=dict(family="Rajdhani", size=12),
        margin=dict(l=0, r=0, b=0, t=20), height=500
    )
    tab2 = html.Div([dcc.Graph(figure=fig_3d)], className="glass-panel p-3 mt-2")

    # Tab 3: AI
    top_stocks = df.head(3)
    gauges = []
    for _, row in top_stocks.iterrows():
        fig_g = go.Figure(go.Indicator(
            mode = "gauge+number", value = row['AI_Score'],
            title = {'text': f"{row['Ticker']} SENTIMENT", 'font': {'family': 'Cinzel', 'size': 16}},
            number = {'font': {'family': 'JetBrains Mono', 'size': 35}},
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#00f3ff"},
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
                    html.H1(["APEX", html.Span(" HORIZON", style={'color':'#00f3ff', 'fontWeight':'400'})], className="text-center font-royal mb-1", style={'fontSize':'3rem'}),
                    html.P(f"SYSTEM TIME: {datetime.now().strftime('%H:%M:%S UTC')}  //  PROTOCOL: {'QUANTUM SIM' if is_sim else 'LIVE LINK'}", 
                           className="text-center font-data", style={'color':'#64748b', 'fontSize':'11px', 'letterSpacing':'1px'})
                ], className="mt-5 mb-4")
            ]),

            # 3. 核心 KPI (修复字号溢出)
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("NET ASSET VALUE", className="font-tech", style={'color':'#94a3b8', 'fontSize':'0.7rem'}),
                    # 🔒 使用 clamp() 动态字号
                    html.Div(f"${kpi['val']:,.0f}", className="kpi-val font-data gold-glow")
                ], className="glass-panel p-3 text-center h-100"), width=6, lg=3),
                
                dbc.Col(html.Div([
                    html.Div("TOTAL RETURN", className="font-tech", style={'color':'#94a3b8', 'fontSize':'0.7rem'}),
                    html.Div(f"{kpi['roi']:+.2%}", className="kpi-val font-data cyan-glow")
                ], className="glass-panel p-3 text-center h-100"), width=6, lg=3),
                
                dbc.Col(html.Div([
                    html.Div("UNREALIZED PNL", className="font-tech", style={'color':'#94a3b8', 'fontSize':'0.7rem'}),
                    html.Div(f"${kpi['pnl']:+,.0f}", className="kpi-val font-data", style={'color': '#00ff9d' if kpi['pnl']>0 else '#ff0055'})
                ], className="glass-panel p-3 text-center h-100"), width=6, lg=3),
                
                dbc.Col(html.Div([
                    html.Div("24H CHANGE", className="font-tech", style={'color':'#94a3b8', 'fontSize':'0.7rem'}),
                    html.Div(f"${kpi['day']:+,.0f}", className="kpi-val font-data", style={'color': '#00ff9d' if kpi['day']>0 else '#ff0055'})
                ], className="glass-panel p-3 text-center h-100"), width=6, lg=3),
            ], className="mb-2 g-3"),

            # 4. Tabs
            dbc.Tabs([
                dbc.Tab(tab1, label="OVERVIEW"),
                dbc.Tab(tab2, label="QUANTUM LAB"),
                dbc.Tab(tab3, label="SENTIMENT AI"),
            ], className="font-royal", style={'marginTop':'20px'}),

        ], fluid=True, style={'paddingTop': '50px', 'paddingBottom': '50px'})
    ])

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)