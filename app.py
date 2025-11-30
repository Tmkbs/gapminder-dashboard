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

# --- 1. 视觉核心: 动态极光 CSS ---
EXTERNAL_STYLES = [
    dbc.themes.BOOTSTRAP,
    "https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&family=DM+Sans:wght@400;500;700&display=swap"
]

CUSTOM_CSS = """
/* 动态背景 */
@keyframes gradient-animation {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

body {
    background: linear-gradient(-45deg, #0f0c29, #302b63, #24243e, #1F4068);
    background-size: 400% 400%;
    animation: gradient-animation 15s ease infinite;
    font-family: 'DM Sans', sans-serif;
    color: #fff;
    height: 100vh;
    overflow: hidden; 
    margin: 0;
}

/* 布局网格 */
.app-grid {
    display: grid;
    grid-template-columns: 280px 1fr;
    grid-template-rows: 80px 1fr;
    height: 100vh;
    gap: 20px;
    padding: 25px;
    box-sizing: border-box;
}

/* 玻璃拟态 (修复版) */
.glass-panel {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(25px);
    -webkit-backdrop-filter: blur(25px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 24px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    overflow: hidden;
    transition: transform 0.3s ease;
}

.sidebar { grid-row: 1 / 3; display: flex; flex-direction: column; padding: 30px; }
.header-area { display: flex; align-items: center; justify-content: space-between; padding: 0 30px; }

/* 字体与装饰 */
h1, h2, h3 { font-family: 'Outfit', sans-serif; font-weight: 700; letter-spacing: -0.5px; }
.label-muted { color: rgba(255,255,255,0.6); font-size: 0.85rem; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; }
.hero-value { font-size: 2.8rem; font-family: 'Outfit', sans-serif; font-weight: 700; background: linear-gradient(to right, #fff, #a5f3fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.divider { height: 1px; background: rgba(255,255,255,0.1); margin: 20px 0; }
.tag { padding: 5px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
.tag-live { background: rgba(0, 255, 159, 0.2); color: #00ff9f; border: 1px solid rgba(0, 255, 159, 0.3); }
.tag-sim { background: rgba(255, 179, 0, 0.2); color: #ffb300; border: 1px solid rgba(255, 179, 0, 0.3); }

/* 表格样式修复 */
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

# --- 2. 数据引擎 ---
def get_data_engine():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    df = pd.DataFrame()
    
    # 尝试读取 Excel
    if os.path.exists(excel_path):
        try: 
            df = pd.read_excel(excel_path, engine='openpyxl')
            df.columns = df.columns.str.strip().str.title()
        except: pass
    
    # 模拟数据 fallback
    if df.empty:
        df = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 60, 'Price': 145},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 20, 'Price': 380},
            {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 50, 'Price': 200},
            {'Ticker': 'MSFT', 'Action': 'Buy', 'Quantity': 30, 'Price': 260}
        ])

    portfolio = {}
    for _, row in df.iterrows():
        t = str(row['Ticker']).upper().strip()
        q = float(row['Quantity'])
        p = float(row['Price'])
        a = str(row['Action']).lower()
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
            cost = portfolio[t]['cost']/portfolio[t]['qty']
            prices.append(cost * random.uniform(0.92, 1.25))
            sectors.append(random.choice(['Tech', 'Finance', 'Auto']))

    res['Price'] = prices
    res['Sector'] = sectors
    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['PnL%'] = res['PnL'] / res['cost']
    
    return res, res['Value'].sum(), res['PnL'].sum(), (res['PnL'].sum()/res['cost'].sum() if res['cost'].sum() else 0), is_sim

# --- 3. 页面布局 ---
def serve_layout():
    df, tot_val, tot_pnl, tot_ret, is_sim = get_data_engine()
    status_cls = "tag tag-live" if not is_sim else "tag tag-sim"
    status_txt = "LIVE" if not is_sim else "SIMULATED"
    colors = ['#4CC9F0', '#4361EE', '#3A0CA3', '#7209B7', '#F72585']

    # 图表1：趋势图
    fig_trend = go.Figure(go.Scatter(
        x=np.linspace(0, 10, 100), y=np.sin(np.linspace(0, 10, 100)) + np.random.normal(0,0.1,100),
        mode='lines', fill='tozeroy', line=dict(color='#4CC9F0', width=2), fillcolor='rgba(76, 201, 240, 0.1)'
    ))
    fig_trend.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                            xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0,r=0,t=0,b=0), height=80)

    # 图表2：环形图
    fig_donut = px.pie(df, values='Value', names='Ticker', hole=0.75, color_discrete_sequence=colors)
    fig_donut.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            showlegend=False, margin=dict(l=0,r=0,t=20,b=20), height=220,
                            annotations=[dict(text='ASSETS', x=0.5, y=0.5, showarrow=False, font_color='rgba(255,255,255,0.5)')])

    return html.Div([
        # 左侧边栏
        html.Div([
            html.H3("AURORA", className="mb-1", style={'color':'#fff'}),
            html.Div("WEALTH OS", className="label-muted mb-5"),
            
            html.Div("TOTAL BALANCE", className="label-muted"),
            html.Div(f"${tot_val:,.2f}", className="hero-value mb-4"),
            
            html.Div([
                html.Div([html.Div("PROFIT / LOSS", className="label-muted"),
                          html.Div(f"{tot_pnl:+,.0f}", style={'fontSize':'1.2rem', 'fontWeight':'700', 'color': '#00ff9f' if tot_pnl>0 else '#ff4757'})], className="mb-3"),
                html.Div([html.Div("RETURN RATE", className="label-muted"),
                          html.Div(f"{tot_ret:+.2%}", style={'fontSize':'1.2rem', 'fontWeight':'700', 'color': '#00ff9f' if tot_ret>0 else '#ff4757'})])
            ]),
            html.Div(className="divider"),
            dcc.Graph(figure=fig_trend, config={'displayModeBar': False}),
            html.Div(className="divider"),
            html.Div([html.Span(status_txt, className=status_cls)], className="mt-auto")
        ], className="glass-panel sidebar"),

        # 顶部
        html.Div([
            html.Div("PORTFOLIO OVERVIEW", className="label-muted"),
            html.Div([html.Span(datetime.now().strftime("%B %d, %Y"), className="label-muted")])
        ], className="header-area glass-panel", style={'gridArea': '1 / 2 / 2 / 3'}),

        # 主内容
        html.Div([
            # 表格 (核心修复: 移除了 + 号格式)
            html.Div([
                html.Div([html.H5("Active Positions", style={'fontWeight':'700'}), html.Div("Live valuation", className="label-muted mb-3")]),
                html.Div([
                    dash_table.DataTable(
                        data=df.to_dict('records'),
                        columns=[
                            {'name': 'Asset', 'id': 'Ticker'},
                            {'name': 'Price', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                            {'name': 'Value', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                            # 下面这一行是修复重点：只保留货币符号，去掉+号
                            {'name': 'Gain/Loss', 'id': 'PnL', 'type': 'numeric', 'format': {'specifier': '$,.0f'}}, 
                            {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '.2%'}},
                        ],
                        style_as_list_view=True,
                        style_data_conditional=[
                            {'if': {'filter_query': '{PnL} >= 0', 'column_id': 'PnL'}, 'color': '#00ff9f', 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{PnL} < 0', 'column_id': 'PnL'}, 'color': '#ff4757', 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#00ff9f'},
                            {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#ff4757'},
                        ]
                    )
                ], style={'overflowY': 'auto', 'height': '100%'})
            ], className="glass-panel p-4", style={'gridArea': '1 / 1 / 2 / 2', 'display':'flex', 'flexDirection':'column'}),

            # 饼图
            html.Div([
                html.H5("Allocation", style={'fontWeight':'700', 'textAlign':'center'}),
                dcc.Graph(figure=fig_donut, config={'displayModeBar': False})
            ], className="glass-panel p-4", style={'gridArea': '1 / 2 / 2 / 3', 'display':'flex', 'flexDirection':'column', 'justifyContent':'center'})
        ], style={'gridArea': '2 / 2 / 3 / 3', 'display': 'grid', 'gridTemplateColumns': '2fr 1fr', 'gap': '20px'})
    ], className="app-grid")

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)