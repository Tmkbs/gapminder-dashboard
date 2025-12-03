import dash
from dash import dcc, html, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import os
import random
import numpy as np
from datetime import datetime, timedelta
import feedparser # ✅ 核心：免费无限新闻源
import time

# =============================================================================
# 0. 全局配置 & NLP 引擎
# =============================================================================
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    analyzer = SentimentIntensityAnalyzer()
    HAS_NLP = True
except:
    HAS_NLP = False
    print("⚠️ 未安装 vaderSentiment，AI 评分将使用模拟值。")

# =============================================================================
# 1. 视觉系统 (Aurora Anti-Glitch CSS)
# =============================================================================
EXTERNAL_STYLES = [
    dbc.themes.BOOTSTRAP,
    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Oswald:wght@400;500;700&family=Fira+Code:wght@400;600&display=swap"
]

CUSTOM_CSS = """
* { box-sizing: border-box; }
body {
    background: #050505;
    background: radial-gradient(circle at 50% 0%, #1a1a2e 0%, #000000 80%);
    font-family: 'Inter', sans-serif;
    color: #e2e8f0;
    margin: 0; padding: 0;
    height: 100vh; width: 100%;
    overflow: hidden; /* 🔒 锁死主滚动条 */
}

/* 布局容器 */
.app-container { display: flex; flex-direction: column; height: 100vh; }
.top-section { flex: 0 0 auto; z-index: 10; }
.content-section { flex: 1 1 auto; overflow-y: auto; padding: 20px; padding-bottom: 80px; }

/* 玻璃卡片 */
.glass-panel {
    background: rgba(20, 25, 35, 0.7);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    height: 100%; display: flex; flex-direction: column; overflow: hidden;
}

/* 字体与颜色 */
.font-head { font-family: 'Oswald', sans-serif; letter-spacing: 1px; text-transform: uppercase; }
.font-num { font-family: 'Fira Code', monospace; letter-spacing: -0.5px; }
.text-cyan { color: #00f3ff; text-shadow: 0 0 10px rgba(0, 243, 255, 0.3); }
.val-up { color: #4ade80; } .val-down { color: #fb7185; }

/* 跑马灯 */
.ticker-bar { height: 32px; background: rgba(0,0,0,0.9); border-bottom: 1px solid rgba(0,243,255,0.2); display: flex; align-items: center; white-space: nowrap; overflow: hidden; }
.ticker-content { display: inline-block; animation: scroll 60s linear infinite; }
.ticker-item { font-family: 'Fira Code'; font-size: 11px; margin: 0 15px; color: #888; }
@keyframes scroll { 0% {transform: translateX(0);} 100% {transform: translateX(-100%);} }

/* Tab & Table */
.nav-tabs { border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px; }
.nav-link { color: #64748b !important; border: none !important; font-family: 'Oswald'; font-size: 1rem; }
.nav-link.active { background: transparent !important; color: #fff !important; border-bottom: 2px solid #00f3ff !important; }
.dash-table-container { width: 100%; overflow-x: auto; }
.news-item { border-bottom: 1px solid rgba(255,255,255,0.05); padding: 10px; font-size: 0.85rem; }
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>AURORA ULTIMATE</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# =============================================================================
# 2. 引擎 A: 资产组合 (Portfolio Engine) - 自动生成Excel
# =============================================================================
def get_portfolio_data():
    random.seed(42)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'portfolio.xlsx')
    
    # 自动生成 Excel 逻辑
    if not os.path.exists(excel_path):
        try:
            pd.DataFrame([
                {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 50, 'Price': 400},
                {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 100, 'Price': 150},
                {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 60, 'Price': 200},
                {'Ticker': 'MSFT', 'Action': 'Buy', 'Quantity': 40, 'Price': 280}
            ]).to_excel(excel_path, index=False, engine='openpyxl')
        except: pass

    df = pd.DataFrame()
    try: 
        df = pd.read_excel(excel_path, engine='openpyxl')
        df.columns = df.columns.str.strip().str.title()
    except: 
        return pd.DataFrame(), False # 读取失败

    # 计算持仓
    portfolio = {}
    for _, row in df.iterrows():
        t = str(row['Ticker']).upper().strip()
        q, p, a = float(row['Quantity']), float(row['Price']), str(row['Action']).lower()
        if t not in portfolio: portfolio[t] = {'qty': 0, 'cost': 0}
        if 'buy' in a: portfolio[t]['qty'] += q; portfolio[t]['cost'] += (q * p)
        elif 'sell' in a and portfolio[t]['qty'] > 0:
            avg = portfolio[t]['cost'] / portfolio[t]['qty']
            portfolio[t]['qty'] -= q; portfolio[t]['cost'] -= (q * avg)
    
    res = pd.DataFrame.from_dict(portfolio, orient='index').reset_index()
    res.rename(columns={'index': 'Ticker'}, inplace=True)
    res = res[res['qty'] > 0].copy()

    # 抓取行情 (Yfinance)
    prices, sectors, betas, caps, changes = [], [], [], [], []
    is_sim = False
    try:
        tickers_str = ' '.join(res['Ticker'].tolist())
        data = yf.Tickers(tickers_str)
        for t in res['Ticker']:
            info = data.tickers[t].info
            p = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            if not p: p = portfolio[t]['cost'] / portfolio[t]['qty'] # 兜底
            
            prices.append(p)
            sectors.append(info.get('sector', 'Other'))
            betas.append(info.get('beta', 1.0))
            caps.append(info.get('marketCap', 0))
            prev = info.get('previousClose', p) or p
            changes.append((p - prev)/prev if prev else 0)
    except:
        is_sim = True
        # 模拟数据
        for t in res['Ticker']:
            prices.append(portfolio[t]['cost']/portfolio[t]['qty'])
            sectors.append('Tech'); betas.append(1.0); caps.append(0); changes.append(0)

    res['Price'] = prices; res['Sector'] = sectors; res['Beta'] = betas; res['Mkt Cap'] = caps; res['DayChg'] = changes
    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['PnL%'] = res['PnL'] / res['cost']
    res['DayPnL'] = res['Value'] * res['DayChg']
    
    return res.sort_values('Value', ascending=False), is_sim

# =============================================================================
# 3. 引擎 B: 真实 RSS AI 扫描器 (Real AI Engine)
# =============================================================================
def get_rss_analysis(ticker):
    if not ticker: return None
    ticker = ticker.upper().strip()
    
    data = {'price': 0, 'change': 0, 'pct': 0, 'name': ticker, 'score': 50, 'news': [], 'status': 'LIVE'}
    
    # 1. 获取价格 (Yfinance)
    try:
        stk = yf.Ticker(ticker)
        info = stk.info
        p = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        prev = info.get('previousClose') or p
        
        if p:
            data['price'] = p
            data['change'] = p - prev
            data['pct'] = (p - prev) / prev
            data['name'] = info.get('shortName', ticker)
    except:
        data['status'] = 'PRICE_ERR'

    # 2. 获取新闻 (RSS Feedparser) - 免费且实时
    try:
        rss_url = f'https://finance.yahoo.com/rss/headline?s={ticker}'
        feed = feedparser.parse(rss_url)
        
        total_score = 0
        count = 0
        
        for entry in feed.entries[:10]: # 分析前10条
            title = entry.title
            link = entry.link
            
            # NLP 计算
            score = 0
            tag = "NEU"
            if HAS_NLP:
                vs = analyzer.polarity_scores(title)
                score = vs['compound'] # -1 到 1
            
            # 标签判定
            if score >= 0.05: tag = "POS"
            elif score <= -0.05: tag = "NEG"
            
            total_score += score
            count += 1
            
            # 格式化时间
            pub_time = "RECENT"
            if hasattr(entry, 'published_parsed'):
                pub_time = time.strftime('%m-%d %H:%M', entry.published_parsed)

            data['news'].append({'title': title, 'url': link, 'tag': tag, 'time': pub_time})
        
        # 3. 计算最终得分 (修正算法，防止全100)
        # 将 -1~1 映射到 0~100。
        if count > 0:
            avg_score = total_score / count # 平均分 -1 到 1
            # 线性映射: (-1 -> 0), (0 -> 50), (1 -> 100)
            final_score = int((avg_score + 1) * 50)
            data['score'] = final_score
        else:
            data['score'] = 50 # 无新闻中性

    except Exception as e:
        data['news'].append({'title': f"News Fetch Error: {e}", 'url': '#', 'tag': 'ERR', 'time': 'NOW'})

    return data

# =============================================================================
# 4. 布局
# =============================================================================
def serve_layout():
    df, is_sim = get_portfolio_data()
    
    # KPI 计算
    if df.empty:
        kpi = {'val': 0, 'pnl': 0, 'roi': 0, 'day': 0}
        ticker_html = []
    else:
        kpi = {
            'val': df['Value'].sum(),
            'pnl': df['PnL'].sum(),
            'roi': df['PnL'].sum()/df['cost'].sum() if df['cost'].sum() else 0,
            'day': df['DayPnL'].sum()
        }
        ticker_html = [html.Span([f"{r['Ticker']} ", html.Span(f"{r['DayChg']:.1%}", className="val-up" if r['DayChg']>=0 else "val-down"), " | "], className="ticker-item") for _, r in df.iterrows()]

    # Tab 1: Portfolio Panel
    tab1 = dbc.Row([
        dbc.Col([
            html.Div([
                html.H5("ACTIVE HOLDINGS", className="font-head text-white mb-3"),
                dash_table.DataTable(
                    data=df.to_dict('records'),
                    columns=[
                        {'name': 'ASSET', 'id': 'Ticker'},
                        {'name': 'SECTOR', 'id': 'Sector'},
                        {'name': 'PRICE', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                        {'name': 'VALUE', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                        {'name': 'PNL', 'id': 'PnL', 'type': 'numeric', 'format': {'specifier': '+,.0f'}},
                        {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '+.1%'}},
                    ],
                    page_size=8, sort_action="native", style_as_list_view=True,
                    style_header={'backgroundColor': 'rgba(0,0,0,0.2)', 'color': '#888', 'borderBottom': '1px solid #333'},
                    style_cell={'backgroundColor': 'rgba(0,0,0,0)', 'color': '#fff', 'borderBottom': '1px solid #222', 'fontFamily': 'Fira Code'},
                    style_data_conditional=[
                        {'if': {'filter_query': '{PnL} >= 0', 'column_id': 'PnL'}, 'color': '#4ade80', 'fontWeight': 'bold'},
                        {'if': {'filter_query': '{PnL} < 0', 'column_id': 'PnL'}, 'color': '#fb7185', 'fontWeight': 'bold'},
                        {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#4ade80'},
                        {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#fb7185'},
                    ]
                )
            ], className="glass-panel p-4 h-100")
        ], width=12, lg=7),
        dbc.Col([
            html.Div([
                html.H5("PNL ATTRIBUTION", className="font-head text-white mb-3 text-center"),
                dcc.Graph(figure=go.Figure(go.Waterfall(
                    x=df['Ticker'], y=df['PnL'], decreasing={"marker": {"color": "#fb7185"}}, increasing={"marker": {"color": "#4ade80"}}, connector={"line": {"color": "rgba(255,255,255,0.2)"}}
                )).update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0,b=0,l=0,r=0), xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')),
                config={'displayModeBar': False}, style={'height': '350px'})
            ], className="glass-panel p-4 h-100")
        ], width=12, lg=5)
    ], className="g-4")

    # Tab 2: 3D Lab
    fig_3d = px.scatter_3d(df, x='Beta', y='PnL%', z='Mkt Cap', color='Sector', size='Value', hover_name='Ticker', opacity=0.9)
    fig_3d.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,b=0,t=0), height=500, scene=dict(bgcolor='rgba(0,0,0,0)'))
    tab2 = html.Div([dcc.Graph(figure=fig_3d)], className="glass-panel p-2")

    # Tab 3: RSS AI Scanner (Integrator)
    tab3 = html.Div([
        dbc.Row([dbc.Col([
            dbc.InputGroup([
                dbc.Input(id="ai-input", placeholder="ENTER TICKER (e.g. NVDA, 0700.HK)...", style={'background':'rgba(255,255,255,0.1)', 'color':'white', 'border':'none'}),
                dbc.Button("AI SCAN", id="ai-btn", color="primary")
            ], style={'maxWidth':'400px', 'margin':'0 auto'})
        ], className="mb-4")]),
        html.Div(id="ai-output")
    ])

    # Main Layout
    return html.Div([
        html.Div(html.Div(ticker_html*5, className="ticker-content"), className="ticker-bar"),
        html.Div([
            dbc.Container([
                dbc.Row([dbc.Col([
                    html.H1(["AURORA", html.Span(" TERMINAL", style={'color':'#00f3ff'})], className="text-center font-head mt-4 mb-2"),
                    html.P(f"PORTFOLIO: {'LIVE' if not is_sim else 'OFFLINE'} | NLP ENGINE: {'ACTIVE' if HAS_NLP else 'SIMULATION'}", className="text-center font-num text-muted", style={'fontSize':'12px'})
                ])]),
                
                dbc.Row([
                    dbc.Col(html.Div([html.Div("EQUITY", className="font-head text-muted"), html.Div(f"${kpi['val']:,.0f}", className="font-num h2")], className="glass-panel p-3 text-center"), width=6, lg=3),
                    dbc.Col(html.Div([html.Div("RETURN", className="font-head text-muted"), html.Div(f"{kpi['roi']:+.2%}", className=f"font-num h2 {'val-up' if kpi['roi']>0 else 'val-down'}")], className="glass-panel p-3 text-center"), width=6, lg=3),
                    dbc.Col(html.Div([html.Div("PNL", className="font-head text-muted"), html.Div(f"${kpi['pnl']:+,.0f}", className=f"font-num h2 {'val-up' if kpi['pnl']>0 else 'val-down'}")], className="glass-panel p-3 text-center"), width=6, lg=3),
                    dbc.Col(html.Div([html.Div("DAY", className="font-head text-muted"), html.Div(f"${kpi['day']:+,.0f}", className=f"font-num h2 {'val-up' if kpi['day']>0 else 'val-down'}")], className="glass-panel p-3 text-center"), width=6, lg=3),
                ], className="mb-4 g-3"),

                dbc.Tabs([
                    dbc.Tab(tab1, label="PORTFOLIO"),
                    dbc.Tab(tab2, label="3D LAB"),
                    dbc.Tab(tab3, label="AI SCANNER"),
                ], className="font-head mb-3")
            ], fluid=True)
        ], className="content-section")
    ], className="app-container")

# AI Callback
@app.callback(Output("ai-output", "children"), [Input("ai-btn", "n_clicks")], [State("ai-input", "value")])
def update_ai_panel(n, ticker):
    if not ticker: return html.Div("WAITING FOR INPUT...", className="text-center text-muted font-num")
    
    d = get_rss_analysis(ticker)
    
    # 仪表盘颜色
    gauge_col = "#00ff9d" if d['score']>60 else "#ff0050" if d['score']<40 else "#00f3ff"
    
    # 新闻列表
    news_html = []
    for n in d['news']:
        tag_c = "#4ade80" if n['tag']=="POS" else "#fb7185" if n['tag']=="NEG" else "#94a3b8"
        news_html.append(html.Div([
            html.Span(n['tag'], style={'color':tag_c, 'fontWeight':'bold', 'fontSize':'10px', 'border':f'1px solid {tag_c}', 'padding':'2px 4px', 'borderRadius':'4px', 'marginRight':'10px'}),
            html.A(n['title'], href=n['url'], target="_blank", style={'color':'#e2e8f0', 'textDecoration':'none', 'fontSize':'13px'}),
            html.Div(n['time'], style={'float':'right', 'color':'#666', 'fontSize':'10px'})
        ], className="news-item"))
    
    return dbc.Row([
        dbc.Col(html.Div([
            html.H2(d['name'], className="font-head"), 
            html.Div(f"${d['price']}", className="display-4 font-num fw-bold"),
            html.Div(f"{d['change']:.2f} ({d['pct']:.2f}%)", className=f"font-num {'val-up' if d['change']>=0 else 'val-down'}", style={'fontSize':'1.5rem'})
        ], className="glass-panel p-4 text-center h-100"), width=12, lg=6),
        
        dbc.Col(html.Div([
            dbc.Row([
                dbc.Col(dcc.Graph(figure=go.Figure(go.Indicator(mode="gauge+number", value=d['score'], gauge={'axis':{'range':[0,100]}, 'bar':{'color':gauge_col}, 'bgcolor':"rgba(0,0,0,0)"})).update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color':'#fff'}, height=150, margin=dict(l=20,r=20,t=20,b=20)), config={'displayModeBar':False}), width=4),
                dbc.Col(html.Div(news_html, style={'height':'150px', 'overflowY':'auto'}), width=8)
            ])
        ], className="glass-panel p-4 h-100"), width=12, lg=6)
    ], className="g-4")

# 赋值 Layout
app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)