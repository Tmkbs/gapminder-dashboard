from flask import Flask
from plotly.data import gapminder
from dash import dcc, html, Dash, callback, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# 1. 初始化 Flask 服务器
server = Flask(__name__)

# 2. 准备 CSS 并将 Dash 附加到 Flask 服务器
css = ["https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css", ]
app = Dash(
    name="Gapminder Dashboard",
    external_stylesheets=css,
    server=server,
    url_base_pathname='/'
)

################### DATASET & 数据清洗 ####################################
gapminder_df = gapminder(datetimes=True, centroids=True, pretty_names=True)
gapminder_df["Year"] = gapminder_df.Year.dt.year

# 异常值处理函数 (我们之前加的，继续保留)
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

# 图表创建函数 (这部分不用变)
def create_table():
    fig = go.Figure(data=[go.Table(header=dict(values=gapminder_df.columns, align='left'), cells=dict(values=gapminder_df.values.T, align='left'))])
    fig.update_layout(paper_bgcolor="#ffffff", margin={"t":0, "l":0, "r":0, "b":0})
    return fig

def create_population_chart(continent="Asia", year=1952):
    filtered_df = gapminder_df_cleaned[(gapminder_df_cleaned.Continent==continent) & (gapminder_df_cleaned.Year==year)]
    filtered_df = filtered_df.sort_values(by="Population", ascending=False).head(15)
    fig = px.bar(filtered_df, x="Country", y="Population", color="Country", title=f"Population for {continent} in {year}", text_auto=True)
    fig.update_layout(paper_bgcolor="#ffffff")
    return fig

def create_gdp_chart(continent="Asia", year=1952):
    filtered_df = gapminder_df_cleaned[(gapminder_df_cleaned.Continent==continent) & (gapminder_df_cleaned.Year==year)]
    filtered_df = filtered_df.sort_values(by="GDP per Capita", ascending=False).head(15)
    fig = px.bar(filtered_df, x="Country", y="GDP per Capita", color="Country", title=f"GDP per Capita for {continent} in {year}", text_auto=True)
    fig.update_layout(paper_bgcolor="#ffffff")
    return fig

def create_life_exp_chart(continent="Asia", year=1952):
    filtered_df = gapminder_df_cleaned[(gapminder_df_cleaned.Continent==continent) & (gapminder_df_cleaned.Year==year)]
    filtered_df = filtered_df.sort_values(by="Life Expectancy", ascending=False).head(15)
    fig = px.bar(filtered_df, x="Country", y="Life Expectancy", color="Country", title=f"Life Expectancy for {continent} in {year}", text_auto=True)
    fig.update_layout(paper_bgcolor="#ffffff")
    return fig

def create_choropleth_map(variable, year):
    filtered_df = gapminder_df_cleaned[gapminder_df_cleaned.Year==year]
    fig = px.choropleth(filtered_df, color=variable, locations="ISO Alpha Country Code", locationmode="ISO-3",
                        color_continuous_scale="RdYlBu", hover_data=["Country", variable], title=f"{variable} Choropleth Map [{year}]")
    fig.update_layout(dragmode=False, paper_bgcolor="#ffffff", margin={"l":0, "r":0})
    return fig

##################### 全局筛选器变量 ####################################
continents = gapminder_df.Continent.unique()
years = gapminder_df.Year.unique()

##################### 全新布局：侧边栏 + 内容区 ###########################
# 创建侧边栏
sidebar = html.Div(
    [
        html.H4("筛选器", className="display-6"),
        html.Hr(),
        html.P("选择参数来更新图表", className="lead"),
        html.H5("条形图筛选"),
        html.Label("大洲 (Continent):"),
        dcc.Dropdown(id="continent-filter", options=continents, value="Asia", clearable=False),
        html.Br(),
        html.Label("年份 (Year):"),
        dcc.Dropdown(id="year-filter", options=years, value=1952, clearable=False),
        html.Hr(),
        html.H5("世界地图筛选"),
        html.Label("变量 (Variable):"),
        dcc.Dropdown(id="var-map-filter", options=["Population", "GDP per Capita", "Life Expectancy"], value="Life Expectancy", clearable=False),
        html.Br(),
        html.Label("年份 (Year):"),
        dcc.Dropdown(id="year-map-filter", options=years, value=1952, clearable=False),
    ],
    className="col-md-3 col-lg-2 p-3 bg-light", # 使用 Bootstrap 列定义宽度
    style={"height": "100vh"}
)

# 创建内容区
content = html.Div(
    [
        html.H1("Gapminder 数据分析仪表盘", className="text-center fw-bold p-3"),
        dcc.Tabs(id="tabs", children=[
            dcc.Tab(label="数据集", children=[dcc.Graph(figure=create_table())]),
            dcc.Tab(label="人口", children=[dcc.Graph(id="population-chart")]),
            dcc.Tab(label="人均GDP", children=[dcc.Graph(id="gdp-chart")]),
            dcc.Tab(label="预期寿命", children=[dcc.Graph(id="life-exp-chart")]),
            dcc.Tab(label="世界地图", children=[dcc.Graph(id="choropleth-map")]),
        ])
    ],
    className="col-md-9 col-lg-10 p-3" # 定义内容区宽度
)

# 组合成最终布局
app.layout = html.Div([
    html.Div([
        sidebar,
        content
    ], className="row g-0") # g-0 移除列之间的间隙
], className="container-fluid", style={"backgroundColor": "#f8f9fa"})


##################### 回调函数 (Callbacks) 更新 ####################################
# 注意：Input 的 ID 已经更新为侧边栏里新的 Dropdown ID
@callback(
    Output("population-chart", "figure"),
    [Input("continent-filter", "value"), Input("year-filter", "value")]
)
def update_population_chart(continent, year):
    return create_population_chart(continent, year)

@callback(
    Output("gdp-chart", "figure"),
    [Input("continent-filter", "value"), Input("year-filter", "value")]
)
def update_gdp_chart(continent, year):
    return create_gdp_chart(continent, year)

@callback(
    Output("life-exp-chart", "figure"),
    [Input("continent-filter", "value"), Input("year-filter", "value")]
)
def update_life_exp_chart(continent, year):
    return create_life_exp_chart(continent, year)

@callback(
    Output("choropleth-map", "figure"),
    [Input("var-map-filter", "value"), Input("year-map-filter", "value")]
)
def update_map(variable, year):
    return create_choropleth_map(variable, year)