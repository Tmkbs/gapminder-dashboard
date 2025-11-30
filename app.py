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

# --- 1. 视觉语言: Infinity Grid (无尽网格) ---
EXTERNAL_STYLES = [
    dbc.themes.SLATE,
    "https://fonts.googleapis.com/css2?family=Syncopate:wght@400;700&family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap"
]

CUSTOM_CSS = """
:root {
    --bg-dark: #09090b;
    --card-bg: rgba(24, 24, 27, 0.6);
    --border-color: rgba(255, 255, 255, 0.08);
    --accent: #3b82f6; /* 专业蓝 */
    --profit: #10b981; /* 翡翠绿 */
    --loss: #ef4444;   /* 警示红 */
}

body {
    background-color: var(--bg-dark);
    background-image: 
        linear-gradient(var(--border-color) 1px, transparent 1px),
        linear-gradient(90deg, var(--border-color) 1px, transparent 1px);
    background-size: 40px 40px; /* 精细网格背景 */
    font-family: 'Inter', sans-serif;
    color: #e4e4e7;
    overflow-x: hidden;
    margin: 0;
}

/* 顶部固定栏 (修复遮挡问题) */
.top-bar {
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 70px;
    background: rgba(9, 9, 11, 0.85);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-color);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 40px;
}

/* 主内容容器 (留出顶部空间) */
.main-content {
    margin-top: 90px; 
    padding: 0 40px 40px 40px;
}

/* 专业级卡片 */
.pro-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 4px; /* 硬朗的直角圆角 */
    padding: 24px;
    height: 100%;
    transition: border-color 0.2s;
}
.pro-card:hover { border-color: rgba(255, 255, 255, 0.2); }

/* 排版微调 */
.font-brand { font-family: 'Syncopate', sans-serif; letter-spacing: -1px; font-weight: 700; text-transform: uppercase; }
.font-mono { font-family: 'JetBrains Mono', monospace; }
.label-sm { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #71717a; font-weight: 600; margin-bottom: 8px; }
.val-xl { font-size: 32px; font-weight: 700; letter-spacing: -0.5px; color: white; }

/* 表格深度定制 (支持分页) */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: #18181b !important;
    color: #a1a1aa !important;
    font-family: 'Inter';
    font-weight: 600 !important;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
    border: none !important;
    border-bottom: 1px solid var(--border-color) !important;
    padding: 16px !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
    background-color: transparent !important;
    color: #e4e4e7 !important;
    font-family: 'JetBrains Mono';
    font-size: 13px;
    border: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.03) !important;
    padding: 12px 16px !important;
}
/* 分页按钮美化 */
.dash-table-container .previous-next-container .page-number { color: #71717a !important; }
.dash-table-container .previous-next-container .page-number.active { color: white !important; font-weight: bold; }
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>INFINITY PRO</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 强健数据处理 ---
def get_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    
    df = pd.DataFrame()
    status = "INIT"

    # 读取 Excel
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path, engine='openpyxl')
            # 🧹 强力清洗数据：去除空格，Title Case 转换
            df.columns = df.columns.str.strip().str.title()
            status = "LIVE"
        except: pass
    
    if df.empty:
        status = "DEMO"
        # 生成一些假数据防止空页面
        df = pd.DataFrame([{'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 100, 'Price': 150}])

    # 计算逻辑
    portfolio = {}
    for _, row in df.iterrows():
        # 🧹 数据清洗：Ticker 转全大写
        t = str(row['Ticker']).strip().upper() 
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

    # 获取行情 (批量)
    try:
        data = yf.Tickers(' '.join(res['Ticker'].tolist()))
        prices, sectors, changes, mkt_caps = [], [], [], []
        
        for t in res['Ticker']:
            info = data.tickers[t].info
            p = info.get('currentPrice') or info.get('regularMarketPrice')
            if not p: raise Exception
            
            prices.append(p)
            # 🧹 数据清洗：Sector 转 Title Case
            s_raw = info.get('sector', 'Unknown')
            sectors.append(s_raw.title().replace('Technology', 'Tech')) # 缩短长单词
            
            prev = info.get('previousClose', p)
            changes.append((p - prev)/prev)
            mkt_caps.append(info.get('marketCap', 0))
            
    except:
        # 模拟数据
        status = "SIMULATION"
        prices = [portfolio[t]['cost']/portfolio[t]['qty'] * random.uniform(0.9, 1.3) for t in res['Ticker']]
        sectors = [random.choice(['Technology', 'Finance', 'Energy', 'Consumer']) for _ in range(len(res))]
        changes = [random.uniform(-0.05, 0.05) for _ in range(len(res))]
        mkt_caps = [random.uniform(1e9, 2e12) for _ in range(len(res))]

    res['Price'] = prices
    res['Sector'] = sectors
    res['Change'] = changes
    res['Market Cap'] = mkt_caps
    
    # 核心指标
    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['ROI'] = res['PnL'] / res['cost']
    
    # 排序：按持仓金额倒序
    res = res.sort_values('Value', ascending=False)
    
    return res, status

# --- 3. 布局 ---
def serve_layout():
    df, status = get_data()
    
    tot_val = df['Value'].sum()
    tot_pnl = df['PnL'].sum()
    
    # 颜色
    c_p = "#10b981"
    c_l = "#ef4444"

    # 图表：板块分布 (Treemap)
    fig_tree = px.treemap(df, path=[px.Constant("All Assets"), 'Sector', 'Ticker'], values='Value',
                          color='ROI', color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
    fig_tree.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0,b=0,l=0,r=0))

    return html.Div([
        # 1. 顶部固定导航栏
        html.Div([
            html.Div([
                html.Span("INFINITY", className="font-brand", style={'color':'white', 'fontSize':'20px'}),
                html.Span(" // GRID", className="font-brand", style={'color':'#52525b', 'fontSize':'20px'})
            ]),
            html.Div([
                html.Span(f"STATUS: {status}", className="font-mono", style={'color': c_p if 'LIVE' in status else '#f59e0b', 'fontSize':'12px'})
            ])
        ], className="top-bar"),

        # 2. 主内容区
        html.Div([
            
            # KPI 行
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("TOTAL EQUITY", className="label-sm"),
                    html.Div(f"${tot_val:,.2f}", className="val-xl font-mono"),
                ], className="pro-card"), width=12, md=4),
                
                dbc.Col(html.Div([
                    html.Div("TOTAL PNL", className="label-sm"),
                    html.Div(f"${tot_pnl:+,.2f}", className="val-xl font-mono", style={'color': c_p if tot_pnl>0 else c_l}),
                ], className="pro-card"), width=12, md=4),
                
                dbc.Col(html.Div([
                    html.Div("TOP SECTOR", className="label-sm"),
                    html.Div(df.iloc[0]['Sector'] if not df.empty else "-", className="val-xl", style={'color':'#a1a1aa'}),
                ], className="pro-card"), width=12, md=4),
            ], className="mb-4"),

            # 复杂图表行
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("PORTFOLIO HEATMAP", className="label-sm mb-3"),
                    dcc.Graph(figure=fig_tree, style={'height': '350px'}, config={'displayModeBar': False})
                ], className="pro-card"), width=12)
            ], className="mb-4"),

            # 数据表格行 (核心升级：分页与过滤)
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("HOLDINGS LEDGER", className="label-sm mb-3"),
                    dash_table.DataTable(
                        id='datatable-interactivity',
                        data=df.to_dict('records'),
                        columns=[
                            {'name': 'TICKER', 'id': 'Ticker'},
                            {'name': 'SECTOR', 'id': 'Sector'},
                            {'name': 'PRICE', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                            {'name': 'CHANGE', 'id': 'Change', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                            {'name': 'HOLDING', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                            {'name': 'PNL', 'id': 'PnL', 'type': 'numeric', 'format': {'specifier': '+,.0f'}}, # 无$符号，纯数字
                            {'name': 'ROI', 'id': 'ROI', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                        ],
                        # 核心功能：分页、排序、过滤
                        page_size=10,  # 每页显示10行，防止页面过长
                        sort_action="native", # 开启排序
                        filter_action="native", # 开启搜索框！你可以输入 'Tech' 只看科技股
                        style_as_list_view=True,
                        style_data_conditional=[
                            {'if': {'filter_query': '{PnL} >= 0', 'column_id': 'PnL'}, 'color': c_p, 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{PnL} < 0', 'column_id': 'PnL'}, 'color': c_l, 'fontWeight': 'bold'},
                            {'if': {'filter_query': '{ROI} >= 0', 'column_id': 'ROI'}, 'color': c_p},
                            {'if': {'filter_query': '{ROI} < 0', 'column_id': 'ROI'}, 'color': c_l},
                            {'if': {'filter_query': '{Change} >= 0', 'column_id': 'Change'}, 'color': c_p},
                            {'if': {'filter_query': '{Change} < 0', 'column_id': 'Change'}, 'color': c_l},
                        ]
                    )
                ], className="pro-card"), width=12)
            ])

        ], className="main-content")
    ])

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)