import dash
from dash import Dash, dcc, html, callback, Input, Output
import plotly.express as px
import pandas as pd
from plotly.data import gapminder
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from flask import Flask

# ------------------------------ APP INITIALIZATION ---------------------------------
server = Flask(__name__)
app = Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME],
    title="Gapminder Dashboard"
)

# ------------------------------ DATA LOADING (NO OUTLIER REMOVAL) --------------------
# 关键改动：我们只使用原始数据，不再做任何可能导致数据丢失的清洗
gapminder_df = gapminder(datetimes=True, centroids=True, pretty_names=True)
gapminder_df["Year"] = gapminder_df.Year.dt.year

continents = gapminder_df.Continent.unique()
years = gapminder_df.Year.unique()

# ------------------------------ CHART CREATION FUNCTIONS --------------------------------
chart_template = "lux"

def create_table():
    fig = go.Figure(data=[go.Table(
        header=dict(values=list(gapminder_df.columns), fill_color='royalblue', align='left', font=dict(color='white', size=12)),
        cells=dict(values=[gapminder_df[col] for col in gapminder_df.columns], fill_color='lavender', align='left')
    )])
    fig.update_layout(margin=dict(l=5, r=5, t=5, b=5))
    return fig

# --- 所有图表函数现在都使用原始的 gapminder_df，保证有数据 ---
def create_population_chart(continent, year):
    df = gapminder_df[(gapminder_df.Continent == continent) & (gapminder_df.Year == year)]
    df = df.sort_values(by="Population", ascending=False).head(15)
    fig = px.bar(df, x="Country", y="Population", color="Country", template=chart_template, title=f"Top 15 Population in {continent} ({year})")
    fig.update_layout(showlegend=False, title_x=0.5)
    return fig

def create_gdp_chart(continent, year):
    df = gapminder_df[(gapminder_df.Continent == continent) & (gapminder_df.Year == year)]
    df = df.sort_values(by="GDP per Capita", ascending=False).head(15)
    fig = px.bar(df, x="Country", y="GDP per Capita", color="Country", template=chart_template, title=f"Top 15 GDP Per Capita in {continent} ({year})")
    fig.update_layout(showlegend=False, title_x=0.5)
    return fig

def create_life_exp_chart(continent, year):
    df = gapminder_df[(gapminder_df.Continent == continent) & (gapminder_df.Year == year)]
    df = df.sort_values(by="Life Expectancy", ascending=False).head(15)
    fig = px.bar(df, x="Country", y="Life Expectancy", color="Country", template=chart_template, title=f"Top 15 Life Expectancy in {continent} ({year})")
    fig.update_layout(showlegend=False, title_x=0.5)
    return fig

def create_choropleth_map(variable, year):
    df = gapminder_df[gapminder_df.Year == year]
    fig = px.choropleth(df, color=variable, locations="ISO Alpha Country Code", locationmode="ISO-3", template=chart_template, hover_data=["Country", variable], title=f"Global {variable} Map ({year})")
    fig.update_layout(title_x=0.5, geo=dict(bgcolor='rgba(0,0,0,0)'))
    return fig

# ------------------------------ LAYOUT DEFINITION --------------------------------
header = html.Header(dbc.Container([html.H1("Gapminder Global Data Insights", className="text-white my-2"), html.P("Explore the population, wealth, and health of nations", className="text-light")], fluid=True, className="py-3"), className="bg-primary shadow-sm")
sidebar = dbc.Col([html.Div([html.I(className="fas fa-compass-drafting fa-2x text-primary"), html.H4("Control Panel", className="ms-2 d-inline-block align-middle")], className="d-flex align-items-center mb-4"), dbc.Row([dbc.Label("Continent"), dcc.Dropdown(id="continent-filter", options=continents, value="Asia", clearable=False)], className="mb-3"), dbc.Row([dbc.Label("Year"), dcc.Slider(id='year-slider', min=years.min(), max=years.max(), step=None, marks={str(y): str(y) for y in years}, value=1952)], className="mb-4"), html.Hr(), html.H5("World Map Variable", className="mt-4"), dbc.Row([dbc.Label("Metric"), dbc.RadioItems(id='map-var-filter', options=[{"label": " Population", "value": "Population"}, {"label": " GDP per Capita", "value": "GDP per Capita"}, {"label": " Life Expectancy", "value": "Life Expectancy"}], value="Life Expectancy", inline=False, labelClassName="me-2", inputClassName="me-1")]), ], width=12, lg=2, className="p-4 bg-light border-end")
# --- 关键改动：Tabs 的 label 使用简单字符串，避免 Bug ---
content = dbc.Col([dbc.Tabs([dbc.Tab(label="Dataset", children=[dcc.Graph(figure=create_table(), style={'height': '80vh'})]), dbc.Tab(label="Key Metrics", children=[dbc.Row([dbc.Col(dcc.Graph(id="population-chart"), width=12, lg=4), dbc.Col(dcc.Graph(id="gdp-chart"), width=12, lg=4), dbc.Col(dcc.Graph(id="life-exp-chart"), width=12, lg=4)], className="g-4 p-4")]), dbc.Tab(label="World Map", children=[dbc.Row(dbc.Col(dcc.Graph(id="choropleth-map", style={'height': '70vh'}), width=12), className="p-4")])])], width=12, lg=10)
app.layout = html.Div([header, dbc.Container([dbc.Row([sidebar, content])], fluid=True)])

# ------------------------------ CALLBACK FUNCTIONS (WITH BUG FIX) -----------------------------------
@callback([Output("population-chart", "figure"), Output("gdp-chart", "figure"), Output("life-exp-chart", "figure")], [Input("continent-filter", "value"), Input("year-slider", "value")])
def update_bar_charts(continent, year):
    # 必需的修复：将滑块传来的年份（可能是字符串）转为整数
    year_int = int(year)
    return create_population_chart(continent, year_int), create_gdp_chart(continent, year_int), create_life_exp_chart(continent, year_int)

@callback(Output("choropleth-map", "figure"), [Input("map-var-filter", "value"), Input("year-slider", "value")])
def update_map(variable, year):
    # 必需的修复：将滑块传来的年份（可能是字符串）转为整数
    year_int = int(year)
    return create_choropleth_map(variable, year_int)