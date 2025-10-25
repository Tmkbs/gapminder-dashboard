import dash
<<<<<<< HEAD
from dash import Dash, dcc, html, callback, Input, Output
=======
<<<<<<< HEAD
from dash import Dash, dcc, html, callback, Input, Output
=======
from dash import Dash dcc, html, callback, Input, Output
>>>>>>> eca0b510117fd46dc37d3adaf0dc8ceeb8e49246
>>>>>>> 8d041d0349d8184399abe4ab43a6774fef692900
import plotly.express as px
import pandas as pd
from plotly.data import gapminder

# 1. 引入 dash-bootstrap-components 库和图标
import dash_bootstrap_components as dbc

# ------------------------------ APP 初始化 ---------------------------------
# 使用 Flask 服务器
from flask import Flask
server = Flask(__name__)

# 2. 指定使用 LUX 主题和 Font Awesome 图标
app = Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Gapminder Ultimate Dashboard"
)

# ------------------------------ 数据加载与清洗 ------------------------------
gapminder_df = gapminder(datetimes=True, centroids=True, pretty_names=True)
gapminder_df["Year"] = gapminder_df.Year.dt.year

def remove_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

gapminder_df_cleaned = gapminder_df.copy()
for col in ["Population", "GDP per Capita", "Life Expectancy"]:
    gapminder_df_cleaned = remove_outliers(gapminder_df_cleaned, col)

continents = gapminder_df_cleaned.Continent.unique()
years = gapminder_df_cleaned.Year.unique()

# ------------------------------ 图表创建函数 (注入主题模板) ------------------
# 3. 为所有图表注入 'lux' 主题模板，使其风格统一
chart_template = "lux"

def create_population_chart(continent, year):
    df = gapminder_df_cleaned[(gapminder_df_cleaned.Continent == continent) & (gapminder_df_cleaned.Year == year)]
    df = df.sort_values(by="Population", ascending=False).head(15)
    fig = px.bar(df, x="Country", y="Population", color="Country", template=chart_template,
                 title=f"Top 15 Population in {continent} ({year})")
    fig.update_layout(showlegend=False, title_x=0.5)
    return fig

def create_gdp_chart(continent, year):
    df = gapminder_df_cleaned[(gapminder_df_cleaned.Continent == continent) & (gapminder_df_cleaned.Year == year)]
    df = df.sort_values(by="GDP per Capita", ascending=False).head(15)
    fig = px.bar(df, x="Country", y="GDP per Capita", color="Country", template=chart_template,
                 title=f"Top 15 GDP Per Capita in {continent} ({year})")
    fig.update_layout(showlegend=False, title_x=0.5)
    return fig

def create_life_exp_chart(continent, year):
    df = gapminder_df_cleaned[(gapminder_df_cleaned.Continent == continent) & (gapminder_df_cleaned.Year == year)]
    df = df.sort_values(by="Life Expectancy", ascending=False).head(15)
    fig = px.bar(df, x="Country", y="Life Expectancy", color="Country", template=chart_template,
                 title=f"Top 15 Life Expectancy in {continent} ({year})")
    fig.update_layout(showlegend=False, title_x=0.5)
    return fig

def create_choropleth_map(variable, year):
    df = gapminder_df_cleaned[gapminder_df_cleaned.Year == year]
    fig = px.choropleth(df, color=variable, locations="ISO Alpha Country Code", locationmode="ISO-3",
                        template=chart_template, hover_data=["Country", variable],
                        title=f"Global {variable} Map ({year})")
    fig.update_layout(title_x=0.5, geo=dict(bgcolor='rgba(0,0,0,0)'))
    return fig

# ------------------------------ 定义布局组件 --------------------------------
# 4. 使用 DBC 组件构建一个更精致、响应式的布局
header = html.Header(
    dbc.Container([
        html.H1("Gapminder 全球数据透视", className="text-white my-2"),
        html.P("探索世界各国的人口、财富与健康", className="text-light")
    ], fluid=True, className="py-3"),
    className="bg-primary shadow-sm"
)

sidebar = dbc.Col([
    html.Div([
        html.I(className="fas fa-compass-drafting fa-2x text-primary"),
        html.H4("控制面板", className="ms-2 d-inline-block align-middle")
    ], className="d-flex align-items-center mb-4"),

    dbc.Row([
        dbc.Label("大洲 (Continent)"),
        dcc.Dropdown(id="continent-filter", options=continents, value="Asia", clearable=False),
    ], className="mb-3"),

    dbc.Row([
        dbc.Label("年份 (Year)"),
        dcc.Slider(
            id='year-slider', min=years.min(), max=years.max(), step=None,
            marks={str(year): str(year) for year in years if year % 10 == 2 or year == 2007},
            value=1952,
        ),
    ], className="mb-4"),

    html.Hr(),
    html.H5("世界地图变量", className="mt-4"),

    dbc.Row([
        dbc.Label("指标 (Metric)"),
        dbc.RadioItems(
            id='map-var-filter',
            options=[
                {"label": " 人口", "value": "Population"},
                {"label": " 人均 GDP", "value": "GDP per Capita"},
                {"label": " 预期寿命", "value": "Life Expectancy"},
            ],
            value="Life Expectancy",
            inline=False,
            labelClassName="me-2",
            inputClassName="me-1",
        )
    ]),
], width=12, lg=2, className="p-4 bg-light border-end")

content = dbc.Col([
    dbc.Tabs([
        dbc.Tab(label=html.Span([html.I(className="fas fa-chart-bar me-2"), "关键指标"]), children=[
            dbc.Row([
                dbc.Col(dcc.Graph(id="population-chart"), width=12, lg=4),
                dbc.Col(dcc.Graph(id="gdp-chart"), width=12, lg=4),
                dbc.Col(dcc.Graph(id="life-exp-chart"), width=12, lg=4),
            ], className="g-4 p-4")
        ]),
        dbc.Tab(label=html.Span([html.I(className="fas fa-globe-americas me-2"), "世界地图"]), children=[
            dbc.Row(dbc.Col(dcc.Graph(id="choropleth-map", style={'height': '70vh'}), width=12), className="p-4")
        ]),
    ])
], width=12, lg=10)

app.layout = html.Div([
    header,
    dbc.Container([
        dbc.Row([
            sidebar,
            content
        ])
    ], fluid=True)
])

# ------------------------------ 回调函数 -----------------------------------
@callback(
    Output("population-chart", "figure"),
    Output("gdp-chart", "figure"),
    Output("life-exp-chart", "figure"),
    Input("continent-filter", "value"),
    Input("year-slider", "value")
)
def update_bar_charts(continent, year):
    return (
        create_population_chart(continent, year),
        create_gdp_chart(continent, year),
        create_life_exp_chart(continent, year)
    )

@callback(
    Output("choropleth-map", "figure"),
    Input("map-var-filter", "value"),
    Input("year-slider", "value") # 地图也受年份滑块控制
)
def update_map(variable, year):
    return create_choropleth_map(variable, year)

# ------------------------------ 运行 (本地测试时使用) ----------------------
# if __name__ == "__main__":
#     app.run_server(debug=True)