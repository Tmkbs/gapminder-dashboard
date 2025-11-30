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

# --- 1. 视觉核心: 动态极光 CSS ---
EXTERNAL_STYLES = [
    dbc.themes.BOOTSTRAP,
    "https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&family=DM+Sans:wght@400;500;700&display=swap"
]

CUSTOM_CSS = """
/* 动态背景：流动的极光 */
@keyframes gradient-animation {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

body {
    /* 高级渐变背景，不再是死黑 */
    background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
    background: linear-gradient(-45deg, #0f0c29, #302b63, #24243e); /* 深邃星空紫 */
    background: linear-gradient(-45deg, #1A1A2E, #16213E, #4B3F72, #1F4068);
    background-size: 400% 400%;
    animation: gradient-animation 15s ease infinite;
    
    font-family: 'DM Sans', sans-serif;
    color: #fff;
    height: 100vh;
    overflow: hidden; /* 锁死滚动 */
    margin: 0;
}

/* 布局网格 */
.app-grid {
    display: grid;
    grid-template-columns: 280px 1fr; /* 左侧栏固定，右侧自适应 */
    grid-template-rows: 80px 1fr;
    height: 100vh;
    gap: 20px;
    padding: 25px;
    box-sizing: border-box;
}

/* 玻璃拟态核心类 (White Glass) */
.glass-panel {
    background: rgba(255, 255, 255, 0.05); /* 极度通透的白 */
    backdrop-filter: blur(25px);
    -webkit-backdrop-filter: blur(25px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 24px; /* 超大圆角 */
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    overflow: hidden;
    transition: transform 0.3s ease;
}

/* 侧边栏特化 */
.sidebar {
    grid-row: 1 / 3;
    display: flex;
    flex-direction: column;
    padding: 30px;
}

/* 顶部 Header */
.header-area {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 30px;
}

/* 字体排版 */
h1, h2, h3 { font-family: 'Outfit', sans-serif; font-weight: 700; letter-spacing: -0.5px; }
.label-muted { color: rgba(255,255,255,0.6); font-size: 0.85rem; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; }
.hero-value { font-size: 2.8rem; font-family: 'Outfit', sans-serif; font-weight: 700; background: linear-gradient(to right, #fff, #a5f3fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

/* 装饰性元素 */
.divider { height: 1px; background: rgba(255,255,255,0.1); margin: 20px 0; }
.tag { padding: 5px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
.tag-live { background: rgba(0, 255, 159, 0.2); color: #00ff9f; border: 1px solid rgba(0, 255, 159, 0.3); }
.tag-sim { background: rgba(255, 179, 0, 0.2); color: #ffb300; border: 1px solid rgba(255, 179, 0, 0.3); }

/* 表格重构 */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: transparent !important;
    color: rgba(255,255,255,0.5) !important;
    font-weight: 600 !important;
    border-bottom: 1px solid rgba(255,255,255,0.1) !important;
    font-family: 'Outfit';
    text-align: left !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
    background-color: transparent !important;
    color: #fff !important;
    border-bottom: 1px solid rgba(255,255,255,0.03) !important;
    padding: 15px 10px !important;
    font-family: 'DM Sans';
    font-size: 0.95rem;
}
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>AURORA WEALTH</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 数据引擎 (保持不变，因为逻辑是完美的) ---
def get_data_engine():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    df = pd.DataFrame()
    
    if os.path.exists(excel_path):
        try: df = pd.read_excel(excel_path, engine='openpyxl')
        except: pass
    
    if df.empty:
        df = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 60, 'Price': 145},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 20, 'Price': 380},
            {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 50, 'Price': 200},
            {'Ticker': 'MSFT', 'Action': 'Buy', 'Quantity': 30, 'Price': 260},
            {'Ticker': 'AMZN', 'Action': 'Buy', 'Quantity': 40, 'Price': 130}
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

    prices, sectors = [], []
    is_sim = False
    try:
        data = yf.Tickers(' '.join(res['Ticker'].tolist()))
        for t in res['Ticker']:
            info = data.tickers[t].info
            p = info.get('currentPrice') or info.get('regularMarketPrice')
            if not p: raise Exception
            prices.append(p)
            sectors.append(info.get('sector', 'Unknown'))
    except:
        is_sim = True
        for t in res['Ticker']:
            prices.append((portfolio[t]['cost']/portfolio[t]['qty']) * random.uniform(0.92, 1.25))
            sectors.append(random.choice(['Technology', 'Consumer', 'Finance', 'Energy']))

    res['Price'] = prices
    res['Sector'] = sectors
    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['PnL%'] = res['PnL'] / res['cost']
    
    return res, res['Value'].sum(), res['PnL'].sum(), res['PnL'].sum()/res['cost'].sum(), is_sim

# --- 3. 页面布局 (极光架构) ---
def serve_layout():
    df, tot_val, tot_pnl, tot_ret, is_sim = get_data_engine()
    status_cls = "tag tag-live" if not is_sim else "tag tag-sim"
    status_txt = "LIVE CONNECTION" if not is_sim else "SIMULATION MODE"

    # 图表配色：使用高级的紫色/青色渐变
    colors = ['#4CC9F0', '#4361EE', '#3A0CA3', '#7209B7', '#F72585']

    # 图表1：波浪面积图 (模拟趋势)
    # 这里生成一个假的趋势图，增加视觉丰富度
    x_trend = np.linspace(0, 10, 100)
    y_trend = np.sin(x_trend) + np.random.normal(0, 0.1, 100) + (x_trend/2)
    fig_trend = go.Figure(go.Scatter(
        x=x_trend, y=y_trend, mode='lines', fill='tozeroy',
        line=dict(color='#4CC9F0', width=3),
        fillcolor='rgba(76, 201, 240, 0.1)'
    ))
    fig_trend.update_layout(
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0, r=0, t=0, b=0), height=100
    )

    # 图表2：环形图
    fig_donut = px.pie(df, values='Value', names='Ticker', hole=0.75, color_discrete_sequence=colors)
    fig_donut.update_layout(
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False, margin=dict(l=0, r=0, t=20, b=20), height=220,
        annotations=[dict(text='ASSETS', x=0.5, y=0.5, font_size=12, showarrow=False, font_color='rgba(255,255,255,0.5)')]
    )

    return html.Div([
        
        # 左侧边栏：核心数据
        html.Div([
            html.H3("AURORA", className="mb-1", style={'color':'#fff'}),
            html.Div("WEALTH OS v2.0", className="label-muted mb-5"),
            
            html.Div("TOTAL BALANCE", className="label-muted"),
            html.Div(f"${tot_val:,.2f}", className="hero-value mb-4"),
            
            html.Div([
                html.Div([
                    html.Div("PROFIT / LOSS", className="label-muted"),
                    html.Div(f"{tot_pnl:+,.0f}", style={'fontSize':'1.2rem', 'fontWeight':'700', 'color': '#00ff9f' if tot_pnl>0 else '#ff4757'})
                ], className="mb-3"),
                
                html.Div([
                    html.Div("RETURN RATE", className="label-muted"),
                    html.Div(f"{tot_ret:+.2%}", style={'fontSize':'1.2rem', 'fontWeight':'700', 'color': '#00ff9f' if tot_ret>0 else '#ff4757'})
                ])
            ]),
            
            html.Div(className="divider"),
            
            html.Div("MARKET TREND", className="label-muted mb-2"),
            dcc.Graph(figure=fig_trend, config={'displayModeBar': False}),
            
            html.Div(className="divider"),
            html.Div([
                html.Span(status_txt, className=status_cls)
            ], className="mt-auto") # 推到底部

        ], className="glass-panel sidebar"),

        # 顶部栏
        html.Div([
            html.Div("PORTFOLIO OVERVIEW", className="label-muted", style={'fontSize':'1rem'}),
            html.Div([
                # 这里可以放一些顶部的小按钮或时间，暂时留空
                html.Span(datetime.now().strftime("%B %d, %Y"), className="label-muted")
            ])
        ], className="header-area glass-panel", style={'gridArea': '1 / 2 / 2 / 3', 'display': 'flex', 'alignItems': 'center'}),

        # 主内容区：下方网格
        html.Div([
            
            # 中间：持仓表格 (占据主要空间)
            html.Div([
                html.Div([
                    html.H5("Active Positions", style={'fontWeight':'700'}),
                    html.Div("Real-time valuation of assets", className="label-muted mb-4")
                ]),
                html.Div([
                    dash_table.DataTable(
                        data=df.to_dict('records'),
                        columns=[
                            {'name': 'Asset', 'id': 'Ticker'},
                            {'name': 'Sector', 'id': 'Sector'},
                            {'name': 'Price', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                            {'name': 'Holding Value', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                            {'name': 'Gain/Loss', 'id': 'PnL', 'type': 'numeric', 'format': {'specifier': '$+,.0f'}},
                            {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                        ],
                        style_as_list_view=True,
                        style_data_conditional=[
                            {'if': {'filter_query': '{PnL} >= 0', 'column_id': 'PnL'}, 'color': '#00ff9f', 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{PnL} < 0', 'column_id': 'PnL'}, 'color': '#ff4757', 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#00ff9f'},
                            {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#ff4757'},
                        ]
                    )
                ], style={'overflowY': 'auto', 'height': '400px'})
            ], className="glass-panel p-4", style={'gridArea': '1 / 1 / 2 / 2', 'display': 'flex', 'flexDirection': 'column'}),

            # 右侧：分布图
            html.Div([
                html.H5("Allocation", style={'fontWeight':'700', 'marginBottom':'20px', 'textAlign':'center'}),
                dcc.Graph(figure=fig_donut, config={'displayModeBar': False})
            ], className="glass-panel p-4", style={'gridArea': '1 / 2 / 2 / 3', 'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'})

        ], style={'gridArea': '2 / 2 / 3 / 3', 'display': 'grid', 'gridTemplateColumns': '2fr 1fr', 'gap': '20px'})

    ], className="app-grid")

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)