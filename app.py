from flask import Flask
from plotly.data import gapminder
from dash import dcc, html, Dash, callback, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd # 导入 pandas 用于数据处理

# ****************** 1. 初始化 Flask 服务器 ******************
server = Flask(__name__)

css = ["https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css", ]

# ****************** 2. 将 Dash 附加到 Flask 服务器 ******************
app = Dash(name="Gapminder Dashboard",
           external_stylesheets=css,
           server=server,  # 关键一步：将 Dash 依附于 Flask server
           url_base_pathname='/') # 定义 Dash 应用的基础路径

################### DATASET & OUTLIER HANDLING ####################################
gapminder_df = gapminder(datetimes=True, centroids=True, pretty_names=True)
gapminder_df["Year"] = gapminder_df.Year.dt.year

# ****************** (新增) 异常值处理函数 ******************
def remove_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

# 在创建图表前，对关键数据进行异常值处理
# 注意：这里我们对整个数据集进行处理，也可以在每个图表函数内部按需处理
gapminder_df_cleaned = gapminder_df.copy()
for col in ["Population", "GDP per Capita", "Life Expectancy"]:
    gapminder_df_cleaned = remove_outliers(gapminder_df_cleaned, col)

#################### CHARTS (使用清洗后的数据) #####################################
# 注意：所有图表函数都要使用 gapminder_df_cleaned
def create_table():
    # 表格可以继续使用原始数据以展示完整性
    fig = go.Figure(data=[go.Table(
        header=dict(values=gapminder_df.columns, align='left'),
        cells=dict(values=gapminder_df.values.T, align='left'))
    ]
    )
    fig.update_layout(paper_bgcolor="#e5ecf6", margin={"t":0, "l":0, "r":0, "b":0}, height=700)
    return fig

def create_population_chart(continent="Asia", year=1952, ):
    filtered_df = gapminder_df_cleaned[(gapminder_df_cleaned.Continent==continent) & (gapminder_df_cleaned.Year==year)]
    filtered_df = filtered_df.sort_values(by="Population", ascending=False).head(15)

    fig = px.bar(filtered_df, x="Country", y="Population", color="Country",
                   title="Country {} for {} Continent in {}".format("Population", continent, year),
                   text_auto=True)
    fig.update_layout(paper_bgcolor="#e5ecf6", height=600)
    return fig

# create_gdp_chart, create_life_exp_chart, create_choropleth_map 函数类似，请确保它们也使用 gapminder_df_cleaned

def create_gdp_chart(continent="Asia", year=1952):
    filtered_df = gapminder_df_cleaned[(gapminder_df_cleaned.Continent==continent) & (gapminder_df_cleaned.Year==year)]
    filtered_df = filtered_df.sort_values(by="GDP per Capita", ascending=False).head(15)

    fig = px.bar(filtered_df, x="Country", y="GDP per Capita", color="Country",
                   title="Country {} for {} Continent in {}".format("GDP per Capita", continent, year),
                   text_auto=True)
    fig.update_layout(paper_bgcolor="#e5ecf6", height=600)
    return fig

def create_life_exp_chart(continent="Asia", year=1952):
    filtered_df = gapminder_df_cleaned[(gapminder_df_cleaned.Continent==continent) & (gapminder_df_cleaned.Year==year)]
    filtered_df = filtered_df.sort_values(by="Life Expectancy", ascending=False).head(15)

    fig = px.bar(filtered_df, x="Country", y="Life Expectancy", color="Country",
                   title="Country {} for {} Continent in {}".format("Life Expectancy", continent, year),
                   text_auto=True)
    fig.update_layout(paper_bgcolor="#e5ecf6", height=600)
    return fig

def create_choropleth_map(variable, year):
    filtered_df = gapminder_df_cleaned[gapminder_df_cleaned.Year==year]

    fig = px.choropleth(filtered_df, color=variable,
                        locations="ISO Alpha Country Code", locationmode="ISO-3",
                        color_continuous_scale="RdYlBu", hover_data=["Country", variable],
                        title="{} Choropleth Map [{}]".format(variable, year)
                     )

    fig.update_layout(dragmode=False, paper_bgcolor="#e5ecf6", height=600, margin={"l":0, "r":0})
    return fig

##################### WIDGETS ####################################
continents = gapminder_df.Continent.unique()
years = gapminder_df.Year.unique()

# 我们将在新的布局中重新组织这些组件

##################### APP LAYOUT (优化后) ####################################
# ****************** 4. 优化布局，将选项栏放左边 ******************
sidebar = html.Div(
    [
        html.H4("Filters", className="text-center p-2"),
        html.Hr(),
        html.H5("Bar Chart Filters"),
        html.Label("Continent:"),
        dcc.Dropdown(id="cont_filter", options=continents, value="Asia", clearable=False),
        html.Br(),
        html.Label("Year:"),
        dcc.Dropdown(id="year_filter", options=years, value=1952, clearable=False),
        html.Hr(),
        html.H5("Choropleth Map Filters"),
        html.Label("Variable:"),
        dcc.Dropdown(id="var_map", options=["Population", "GDP per Capita", "Life Expectancy"],
                     value="Life Expectancy", clearable=False),
        html.Br(),
        html.Label("Year:"),
        dcc.Dropdown(id="year_map", options=years, value=1952, clearable=False),
    ],
    className="col-2 bg-light p-3",
    style={"height": "100vh"}
)

content = html.Div(
    [
        dcc.Tabs([
            dcc.Tab([html.Br(), dcc.Graph(id="dataset", figure=create_table())], label="Dataset"),
            dcc.Tab([html.Br(), dcc.Graph(id="population")], label="Population"),
            dcc.Tab([html.Br(), dcc.Graph(id="gdp")], label="GDP Per Capita"),
            dcc.Tab([html.Br(), dcc.Graph(id="life_expectancy")], label="Life Expectancy"),
            dcc.Tab([html.Br(), dcc.Graph(id="choropleth_map")], label="Choropleth Map"),
        ])
    ],
    className="col-10 p-3"
)

app.layout = html.Div([
    html.H1("Gapminder Dataset Analysis", className="text-center fw-bold m-2"),
    html.Div([
        sidebar,
        content
    ], className="row g-0") # 使用 Bootstrap 的 row 和 col
], style={"background-color": "#e5ecf6", "min-height": "100vh"})


##################### CALLBACKS (优化后) ####################################
@callback(
    Output("population", "figure"),
    [Input("cont_filter", "value"), Input("year_filter", "value")]
)
def update_population_chart(continent, year):
    return create_population_chart(continent, year)

@callback(
    Output("gdp", "figure"),
    [Input("cont_filter", "value"), Input("year_filter", "value")]
)
def update_gdp_chart(continent, year):
    return create_gdp_chart(continent, year)

@callback(
    Output("life_expectancy", "figure"),
    [Input("cont_filter", "value"), Input("year_filter", "value")]
)
def update_life_exp_chart(continent, year):
    return create_life_exp_chart(continent, year)

@callback(
    Output("choropleth_map", "figure"),
    [Input("var_map", "value"), Input("year_map", "value")]
)
def update_map(var_map, year):
    return create_choropleth_map(var_map, year)

# ****************** 3. 移除本地服务器运行代码 ******************
# if __name__ == "__main__":
#     app.run(debug=True)
# 这行代码在部署时不再需要，因为 PythonAnywhere 会通过 WSGI 文件来启动 server