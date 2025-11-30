import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import os # <--- 关键：引入系统路径模块

# --- 1. 样式: 强制锁死布局，防止鬼畜 ---
EXTERNAL_STYLES = [
    dbc.themes.DARKLY,
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap"
]

CUSTOM_CSS = """
body {
    background-color: #050505;
    font-family: 'Inter', sans-serif;
    color: #e0e0e0;
    overflow-x: hidden; /* 🚫 核心修复：禁止横向滚动，防止拉升 */
    width: 100vw;
}

/* 玻璃卡片 */
.glass-box {
    background: rgba(20, 25, 35, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    overflow: hidden; /* 🚫 核心修复：内容溢出直接切断 */
}

/* 强制图表容器高度，防止无限拉长 */
.chart-container {
    height: 400px; 
    position: relative;
}

/* 滚动条 */
.ticker-wrap {
    width: 100%;
    background: #000;
    height: 40px;
    line-height: 40px;
    white-space: nowrap;
    border-bottom: 1px solid #333;
    overflow: hidden;
}
.ticker-move { display: inline-block; animation: tick 30s linear infinite; }
.ticker-item { display: inline-block; padding: 0 30px; font-weight: 600; font-size: 14px; }
@keyframes tick { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }

/* 颜色辅助 */
.text-green { color: #00E396; }
.text-red { color: #FF4560; }
"""

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLES)
server = app.server
app.index_string = f'''<!DOCTYPE html><html><head>{{%metas%}}<title>PRO DASHBOARD</title>{{%favicon%}}{{%css%}}<style>{CUSTOM_CSS}</style></head><body>{{%app_entry%}}<footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer></body></html>'''

# --- 2. 核心数据逻辑 (绝对路径修复版) ---
def get_data():
    # 🌟 修复文件读取：获取 app.py 所在的绝对路径
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, 'portfolio.xlsx')
    
    print(f"尝试读取文件路径: {file_path}") # Debug信息

    df = pd.DataFrame()
    
    # 尝试读取 Excel
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        df.columns = df.columns.str.strip().str.title()
    except Exception as e:
        print(f"❌ Excel 读取失败: {e}")
        # 如果读取失败，启用【内置保底数据】，确保网页永远能打开
        df = pd.DataFrame([
            {'Ticker': 'AAPL', 'Action': 'Buy', 'Quantity': 50, 'Price': 150},
            {'Ticker': 'NVDA', 'Action': 'Buy', 'Quantity': 20, 'Price': 400},
            {'Ticker': 'TSLA', 'Action': 'Buy', 'Quantity': 50, 'Price': 180},
            {'Ticker': 'MSFT', 'Action': 'Buy', 'Quantity': 30, 'Price': 250},
        ])

    # 处理持仓逻辑
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
        elif 'sell' in a:
            if portfolio[t]['qty'] > 0:
                avg = portfolio[t]['cost'] / portfolio[t]['qty']
                portfolio[t]['qty'] -= q
                portfolio[t]['cost'] -= (q * avg)
    
    res = pd.DataFrame.from_dict(portfolio, orient='index').reset_index()
    res.rename(columns={'index': 'Ticker'}, inplace=True)
    res = res[res['qty'] > 0].copy()

    if res.empty: return res, 0, 0, 0, True

    # 尝试获取行情 (带模拟回退)
    is_sim = False
    try:
        tickers_str = ' '.join(res['Ticker'].tolist())
        data = yf.Tickers(tickers_str)
        prices, sectors, changes = [], [], []
        
        for t in res['Ticker']:
            info = data.tickers[t].info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            if not price: raise Exception("Price Missing")
            prices.append(price)
            sectors.append(info.get('sector', 'Tech'))
            prev = info.get('previousClose', price)
            changes.append((price - prev)/prev)
            
        res['Price'] = prices
        res['Sector'] = sectors
        res['Change'] = changes
        
    except:
        is_sim = True
        # 模拟数据生成
        import random
        res['Price'] = res.apply(lambda x: (x['cost']/x['qty']) * random.uniform(0.9, 1.4), axis=1)
        res['Sector'] = [random.choice(['Technology', 'Finance', 'Energy', 'Healthcare']) for _ in range(len(res))]
        res['Change'] = [random.uniform(-0.05, 0.05) for _ in range(len(res))]

    res['Value'] = res['qty'] * res['Price']
    res['PnL'] = res['Value'] - res['cost']
    res['PnL%'] = res['PnL'] / res['cost']
    
    total_val = res['Value'].sum()
    total_pnl = res['PnL'].sum()
    total_ret = total_pnl / res['cost'].sum() if res['cost'].sum() else 0
    
    return res, total_val, total_pnl, total_ret, is_sim

# --- 3. 布局逻辑 ---
def serve_layout():
    df, tot_val, tot_pnl, tot_ret, is_sim = get_data()
    
    # 顶部跑马灯
    ticker_items = []
    if not df.empty:
        for _, row in df.iterrows():
            c = "text-green" if row['Change'] >= 0 else "text-red"
            s = "▲" if row['Change'] >= 0 else "▼"
            ticker_items.append(html.Span([
                f"{row['Ticker']} ", 
                html.Span(f"${row['Price']:.2f} {s} {row['Change']:.2%}", className=c),
                "  ///  "
            ], className="ticker-item"))

    # 状态栏
    status = html.Span("● LIVE DATA", className="text-green ms-2") if not is_sim else html.Span("● OFFLINE MODE", className="text-warning ms-2")

    return html.Div([
        # 跑马灯
        html.Div(html.Div(ticker_items * 3, className="ticker-move"), className="ticker-wrap"),

        dbc.Container([
            # 标题
            dbc.Row([
                dbc.Col(html.H2(["PORTFOLIO VISUALIZER", status], className="text-white mt-4 mb-4", style={'fontWeight':'800'}))
            ]),

            # KPI 卡片
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("NET WORTH", style={'color':'#888', 'fontSize':'12px', 'letterSpacing':'1px'}),
                    html.Div(f"${tot_val:,.2f}", style={'color':'#fff', 'fontSize':'32px', 'fontWeight':'bold'})
                ], className="glass-box p-4 h-100"), width=12, md=4, className="mb-3"),
                
                dbc.Col(html.Div([
                    html.Div("TOTAL PNL", style={'color':'#888', 'fontSize':'12px', 'letterSpacing':'1px'}),
                    html.Div(f"${tot_pnl:+,.2f}", className="text-green" if tot_pnl>=0 else "text-red", style={'fontSize':'32px', 'fontWeight':'bold'})
                ], className="glass-box p-4 h-100"), width=12, md=4, className="mb-3"),

                dbc.Col(html.Div([
                    html.Div("ROI %", style={'color':'#888', 'fontSize':'12px', 'letterSpacing':'1px'}),
                    html.Div(f"{tot_ret:+.2%}", className="text-green" if tot_ret>=0 else "text-red", style={'fontSize':'32px', 'fontWeight':'bold'})
                ], className="glass-box p-4 h-100"), width=12, md=4, className="mb-3"),
            ]),

            # 图表区域 (重点修复 Heatmap)
            dbc.Row([
                # 甜甜圈图
                dbc.Col(html.Div([
                    html.H5("ALLOCATION", className="text-white mb-3"),
                    dcc.Graph(
                        figure=px.pie(df, values='Value', names='Ticker', hole=0.6, color_discrete_sequence=px.colors.sequential.RdBu)
                        .update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0,b=0,l=0,r=0), showlegend=False),
                        config={'displayModeBar': False},
                        style={'height': '300px'} # 强制高度
                    )
                ], className="glass-box p-4 h-100"), width=12, lg=4, className="mb-3"),

                # 树状图 Heatmap (修复拉升问题)
                dbc.Col(html.Div([
                    html.H5("MARKET HEATMAP", className="text-white mb-3"),
                    html.Div([ # 包裹一层 DIV 限制高度
                        dcc.Graph(
                            figure=px.treemap(df, path=[px.Constant("All"), 'Sector', 'Ticker'], values='Value', color='PnL%',
                                            color_continuous_scale='RdYlGn', color_continuous_midpoint=0)
                            .update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0,b=0,l=0,r=0)),
                            config={'displayModeBar': False},
                            style={'height': '100%', 'width': '100%'} # 填满父容器
                        )
                    ], className="chart-container") # 使用 CSS 类锁死高度
                ], className="glass-box p-4 h-100"), width=12, lg=8, className="mb-3"),
            ]),

            # 表格
            dbc.Row([
                dbc.Col(html.Div([
                    dash_table.DataTable(
                        data=df.to_dict('records'),
                        columns=[
                            {'name': 'ASSET', 'id': 'Ticker'},
                            {'name': 'PRICE', 'id': 'Price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                            {'name': 'VALUE', 'id': 'Value', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                            {'name': 'ROI', 'id': 'PnL%', 'type': 'numeric', 'format': {'specifier': '+.2%'}},
                        ],
                        style_as_list_view=True,
                        style_header={'backgroundColor': 'transparent', 'color': '#888', 'borderBottom': '1px solid #333'},
                        style_cell={'backgroundColor': 'transparent', 'color': '#fff', 'padding': '15px', 'border': 'none'},
                        style_data_conditional=[
                            {'if': {'filter_query': '{PnL%} >= 0', 'column_id': 'PnL%'}, 'color': '#00E396'},
                            {'if': {'filter_query': '{PnL%} < 0', 'column_id': 'PnL%'}, 'color': '#FF4560'},
                        ]
                    )
                ], className="glass-box p-4"), width=12)
            ], className="mb-5")

        ], fluid=True)
    ])

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)