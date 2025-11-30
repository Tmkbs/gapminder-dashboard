import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go

# --- 初始化 APP (使用 DARKLY 主题，打造黑金交易终端风格) ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

# --- 核心逻辑函数：处理数据 ---
def get_portfolio_data():
    # 1. 读取交易记录
    try:
        df_trans = pd.read_csv('data_transactions.csv')
    except:
        # 如果没有文件，返回空数据防止报错
        return pd.DataFrame(), 0, 0, 0, pd.DataFrame()

    # 2. 计算持仓 (加权平均成本逻辑)
    portfolio = {}
    
    for index, row in df_trans.iterrows():
        ticker = row['Ticker']
        action = row['Action'].lower()
        qty = row['Quantity']
        price = row['Price']
        
        if ticker not in portfolio:
            portfolio[ticker] = {'Quantity': 0, 'TotalCost': 0, 'RealizedGain': 0}
        
        if action == 'buy':
            portfolio[ticker]['Quantity'] += qty
            portfolio[ticker]['TotalCost'] += (qty * price)
        elif action == 'sell':
            # 卖出时，计算已实现盈亏 (基于平均成本)
            avg_cost = portfolio[ticker]['TotalCost'] / portfolio[ticker]['Quantity'] if portfolio[ticker]['Quantity'] > 0 else 0
            portfolio[ticker]['Quantity'] -= qty
            portfolio[ticker]['TotalCost'] -= (qty * avg_cost) # 减少对应的成本
            portfolio[ticker]['RealizedGain'] += (price - avg_cost) * qty

    # 3. 转为 DataFrame 并过滤掉已清仓的股票
    df_holdings = pd.DataFrame.from_dict(portfolio, orient='index').reset_index()
    df_holdings.rename(columns={'index': 'Ticker'}, inplace=True)
    df_holdings = df_holdings[df_holdings['Quantity'] > 0].copy()

    if df_holdings.empty:
        return df_holdings, 0, 0, 0, df_trans

    # 4. 自动化：批量从 Yahoo Finance 获取实时数据 (Sector, Market Cap, Beta, Price)
    ticker_list = list(df_holdings['Ticker'])
    try:
        # 批量下载，速度更快
        tickers_data = yf.Tickers(' '.join(ticker_list))
        
        current_prices = []
        sectors = []
        market_caps = []
        betas = []
        day_changes = []

        for ticker in ticker_list:
            try:
                info = tickers_data.tickers[ticker].info
                # 价格容错：如果没开盘，取上一日收盘价
                price = info.get('currentPrice', info.get('previousClose', 0))
                prev_close = info.get('previousClose', price)
                
                current_prices.append(price)
                sectors.append(info.get('sector', 'Other'))
                market_caps.append(info.get('marketCap', 0))
                betas.append(info.get('beta', 0))
                day_changes.append((price - prev_close) / prev_close)
            except:
                # 如果某个股票抓取失败，填默认值
                current_prices.append(0)
                sectors.append('Unknown')
                market_caps.append(0)
                betas.append(0)
                day_changes.append(0)

        df_holdings['Current Price'] = current_prices
        df_holdings['Sector'] = sectors
        df_holdings['Market Cap'] = market_caps
        df_holdings['Beta'] = betas
        df_holdings['1D Change %'] = day_changes

    except Exception as e:
        print(f"API Error: {e}")

    # 5. 计算最终指标
    df_holdings['Market Value'] = df_holdings['Quantity'] * df_holdings['Current Price']
    df_holdings['Avg Cost'] = df_holdings['TotalCost'] / df_holdings['Quantity']
    df_holdings['Unrealized Gain'] = df_holdings['Market Value'] - df_holdings['TotalCost']
    df_holdings['Total Return %'] = (df_holdings['Unrealized Gain'] / df_holdings['TotalCost']) * 100
    
    # 汇总数据
    total_market_value = df_holdings['Market Value'].sum()
    total_invested = df_holdings['TotalCost'].sum()
    total_unrealized_pnl = total_market_value - total_invested
    total_pnl_pct = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0

    return df_holdings, total_market_value, total_unrealized_pnl, total_pnl_pct, df_trans

# --- 布局设计 ---
def serve_layout():
    df, tot_val, tot_pnl, tot_pct, df_log = get_portfolio_data()
    
    # 颜色逻辑：盈利绿色，亏损红色
    color_pnl = "#00FF00" if tot_pnl >= 0 else "#FF0000"

    # 图表 1: 扇形图 (Sector Allocation)
    fig_sector = px.pie(df, values='Market Value', names='Sector', 
                        title='Portfolio Allocation by Sector', hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_sector.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')

    # 图表 2: 树状图 (Market Cap Size & Allocation) - 类似视频里的矩形图
    fig_treemap = px.treemap(df, path=['Sector', 'Ticker'], values='Market Value',
                             color='Total Return %', 
                             color_continuous_scale='RdYlGn',
                             color_continuous_midpoint=0,
                             title='Holdings Heatmap (Size=Value, Color=Profit)')
    fig_treemap.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')

    # 格式化表格数据以便展示
    df_display = df[['Ticker', 'Quantity', 'Avg Cost', 'Current Price', 'Market Value', 'Total Return %', '1D Change %', 'Beta', 'Sector']].copy()
    for col in ['Avg Cost', 'Current Price', 'Market Value']:
        df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
    for col in ['Total Return %', '1D Change %']:
        df_display[col] = df_display[col].apply(lambda x: f"{x:.2%}")
    df_display['Beta'] = df_display['Beta'].apply(lambda x: f"{x:.2f}")

    return dbc.Container([
        # 顶部标题
        dbc.Row([
            dbc.Col(html.H2("🚀 Live Stock Portfolio Dashboard", className="text-center text-white mb-4"), width=12)
        ], className="mt-4"),

        # 核心指标卡片
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Total Portfolio Value", className="card-title text-muted"),
                    html.H2(f"${tot_val:,.2f}", className="card-text text-white")
                ])
            ], color="secondary", outline=True), width=4),
            
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Unrealized Gain/Loss", className="card-title text-muted"),
                    html.H2(f"${tot_pnl:,.2f}", className="card-text", style={'color': color_pnl})
                ])
            ], color="secondary", outline=True), width=4),

            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H5("Total Return (%)", className="card-title text-muted"),
                    html.H2(f"{tot_pct:.2f}%", className="card-text", style={'color': color_pnl})
                ])
            ], color="secondary", outline=True), width=4),
        ], className="mb-4"),

        # 图表区域
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_sector), width=6),
            dbc.Col(dcc.Graph(figure=fig_treemap), width=6),
        ]),

        # 详细持仓表格
        dbc.Row([
            dbc.Col([
                html.H4("Holdings Detail", className="text-white mt-4"),
                dash_table.DataTable(
                    data=df_display.to_dict('records'),
                    columns=[{'name': i, 'id': i} for i in df_display.columns],
                    style_header={'backgroundColor': '#303030', 'color': 'white', 'fontWeight': 'bold'},
                    style_cell={'backgroundColor': '#202020', 'color': 'white', 'border': '1px solid #444'},
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{Total Return %} contains "-"', 'column_id': 'Total Return %'},
                            'color': '#FF4136' # 亏损显示红色
                        },
                        {
                            'if': {'filter_query': '{Total Return %} contains "-"', 'column_id': 'Total Return %'},
                            'color': '#FF4136' 
                        },
                         {
                            'if': {'column_id': 'Total Return %'},
                            'color': '#2ECC40' # 盈利默认绿色 (会被上面的红色规则覆盖)
                        }
                    ]
                )
            ], width=12)
        ], className="mb-5")

    ], fluid=True)

app.layout = serve_layout

if __name__ == '__main__':
    app.run(debug=True)