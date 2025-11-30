import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import os
import random

# --- 1. 审美升级: 字体 & CSS 注入 ---
# 引入 Montserrat (标题) 和 JetBrains Mono (数字)
EXTERNAL_STYLES = [
    dbc.themes.BOOTSTRAP, # 基础框架
    "https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap"
]

CUSTOM_CSS = """
/* 全局背景：深海极光渐变，不再是死黑 */
body {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    min-height: 100vh;
    color: #e2e8f0;
    font-family: 'Montserrat', sans-serif;
    overflow-x: hidden;
}

/* 玻璃拟态卡片：更通透，带微光 */
.glass-card {
    background: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px; /* 更大的圆角 */
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    transition: all 0.3s ease;
}

.glass-card:hover {
    transform: translateY(-5px); /* 悬浮动效 */
    border-color: rgba(255, 255, 255, 0.2);
    box-shadow: 0 15px 40px 0 rgba(0, 0, 0, 0.3);
}

/* 顶部导航条 */
.nav-header {
    background: rgba(15, 23, 42, 0.8);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 15px 0;
    margin-bottom: 30px;
}

/* 字体优化 */
h1, h2, h3, h4, h5, h6 { font-weight: 800; letter-spacing: -0.5px; }
.mono-font { font-family: 'JetBrains Mono', monospace; }

/* KPI 数值样式 */
.kpi-label { color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
.kpi-value { font-size: 2.5rem; font-weight: 800; background: -webkit-linear-gradient(#fff, #cbd5e1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

/* 高级配色 */
.text-profit { color: #00F5D4; text-shadow: 0 0 10px rgba(0, 245, 212, 0.3); } /* 荧光薄荷绿 */
.text-loss { color: #FF5E5E; text-shadow: 0 0 10px rgba(255, 94, 94, 0.3); }   /* 珊瑚红 */

/* 修复表格样式 */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: rgba(255,255,255,0.05) !important;
    color: #94a3b8 !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    border: none !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
    background-color: transparent !important;
    color: #f1f5f9 !important;
    font-family: 'JetBrains Mono', monospace;
    border: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
}
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>AESTHETIC FINANCE</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 数据引擎 (保留之前的强健逻辑) ---
def get_data_engine():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    
    status_msg = "Checking Data..."
    df = pd.DataFrame()

    # 读取逻辑
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path, engine='openpyxl')
            df.columns = df.columns.str.strip().str.title()
            status_msg = "Excel Loaded"
        except: pass
    
    # 模拟数据 (美化版)
    if df.empty:
        status_msg = "Demo Data"
        df = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 80, 'Price': 140},
            {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 40, 'Price': 190},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 15, 'Price': 420},
            {'Ticker': 'ETH-USD', 'Action': 'Buy', 'Quantity': 5, 'Price': 1800},
        ])

    # 持仓计算
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

    # 价格获取 (带模拟)
    prices, sectors, changes = [], [], []
    is_sim = False
    try:
        data = yf.Tickers(' '.join(res['Ticker'].tolist()))
        for t in res['Ticker']:
            info = data.tickers[t].info
            p = info.get('currentPrice') or info.get('regularMarketPrice')
            if not p: raise Exception("No Price")
            prices.append(p)
            sectors.append(info.get('sector', 'Tech'))
            prev = info.get('previousClose', p)
            changes.append((p - prev)/prev)
    except:
        is_sim = True
        for t in res['Ticker']:
            prices.append((portfolio[t]['cost']/portfolio[t]['qty']) * random.uniform(0.95, 1.35))
            sectors.append(random.choice(['Technology', 'Crypto', 'AI', 'Energy']))
            changes.append(random.uniform(-0.04, 0.06))

    res['Price'] = prices
    res['Sector'] = sectors
    res['Change'] = changes
    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['PnL%'] = res['PnL'] / res['cost']
    
    return res, res['Value'].sum(), res['PnL'].sum(), res['PnL'].sum()/res['cost'].sum(), is_sim, status_msg

# --- 3. 布局设计 ---
def serve_layout():
    df, tot_val, tot_pnl, tot_ret, is_sim, msg = get_data_engine()
    
    # 状态指示
    status_dot = "🟢" if not is_sim else "🟠"
    status_text = "Live Market" if not is_sim else "Simulated"

    # 图表配色方案 (高级柔和色系)
    colors = px.colors.qualitative.Pastel

    return html.Div([
        # 1. 顶部导航
        html.Div([
            dbc.Container([
                dbc.Row([
                    dbc.Col(html.H3(["✨ AESTHETIC", html.Span("FINANCE", style={'fontWeight':300, 'opacity':0.7})], className="text-white m-0"), width=8),
                    dbc.Col(html.Div([
                        html.Span(f"{msg} | {status_dot} {status_text}", className="mono-font", style={'fontSize':'12px', 'opacity':0.6})
                    ], className="text-end pt-2"), width=4)
                ], align="center")
            ], fluid=True)
        ], className="nav-header"),

        dbc.Container([
            # 2. 核心 KPI (悬浮卡片)
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("Total Balance", className="kpi-label"),
                    html.Div(f"${tot_val:,.2f}", className="kpi-value mono-font"),
                ], className="glass-card p-4 h-100"), width=12, md=4, className="mb-4"),
                
                dbc.Col(html.Div([
                    html.Div("Unrealized P&L", className="kpi-label"),
                    html.Div(f"{'+' if tot_pnl>0 else ''}${tot_pnl:,.2f}", className=f"kpi-value mono-font {'text-profit' if tot_pnl>=0 else 'text-loss'}"),
                ], className="glass-card p-4 h-100"), width=12, md=4, className="mb-4"),

                dbc.Col(html.Div([
                    html.Div("Return Rate", className="kpi-label"),
                    html.Div(f"{tot_ret:+.2%}", className=f"kpi-value mono-font {'text-profit' if tot_ret>=0 else 'text-loss'}"),
                ], className="glass-card p-4 h-100"), width=12, md=4, className="mb-4"),
            ]),

            # 3. 图表区
            dbc.Row([
                # 左侧：高级甜甜圈图
                dbc.Col(html.Div([
                    html.H5("Asset Distribution", className="text-white mb-4"),
                    dcc.Graph(
                        figure=px.pie(df, values='Value', names='Ticker', hole=0.7, 
                                    color_discrete_sequence=px.colors.sequential.RdBu_r) # 蓝紫色系
                        .update_layout(
                            template="plotly_dark", 
                            paper_bgcolor='rgba(0,0,0,0)', 
                            plot_bgcolor='rgba(0,0,0,0)',
                            showlegend=False,
                            margin=dict(t=0, b=0, l=0, r=0),
                            height=300,
                            annotations=[dict(text='PORTFOLIO', x=0.5, y=0.5, font_size=14, showarrow=False, font_color='#94a3b8')]
                        ),
                        config={'displayModeBar': False}
                    )
                ], className="glass-card p-4 h-100"), width=12, lg=4, className="mb-4"),

                # 右侧：盈亏条形图 (更直观)
                dbc.Col(html.Div([
                    html.H5("Profit & Loss Analysis", className="text-white mb-4"),
                    dcc.Graph(
                        figure=go.Figure(go.Bar(
                            x=df['Ticker'], 
                            y=df['PnL'],
                            marker_color=['#00F5D4' if x >= 0 else '#FF5E5E' for x in df['PnL']], # 自定义颜色
                            marker_line_width=0,
                            opacity=0.9
                        )).update_layout(
                            template="plotly_dark",
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            margin=dict(t=10, b=10, l=0, r=0),
                            height=300,
                            xaxis=dict(showgrid=False),
                            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                        ),
                        config={'displayModeBar': False}
                    )
                ], className="glass-card p-4 h-100"), width=12, lg=8, className="mb-4"),
            ]),

            # 4. 详细数据表
            dbc.Row([
                dbc.Col(html.Div([
                    html.H5("Positions Detail", className="text-white mb-4"),
                    dash_table.DataTable(
                        data=df.to_dict('records'),
                        columns=[
                            {'name': 'Asset', 'id': 'Ticker'},
                            {'name': 'Sector', 'id': 'Sector'},
                            {'name': 'Holdings', 'id': 'qty'},
                            {'name': 'Price', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                            {'name': 'Value', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                            {'name': 'PnL', 'id': 'PnL', 'type': 'numeric', 'format': {'specifier': '$+,.0f'}},
                            {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                        ],
                        style_as_list_view=True,
                        style_data_conditional=[
                            {'if': {'filter_query': '{PnL} >= 0', 'column_id': 'PnL'}, 'color': '#00F5D4', 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{PnL} < 0', 'column_id': 'PnL'}, 'color': '#FF5E5E', 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#00F5D4'},
                            {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#FF5E5E'},
                        ]
                    )
                ], className="glass-card p-4"), width=12)
            ], className="mb-5")

        ], fluid=True)
    ])

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)