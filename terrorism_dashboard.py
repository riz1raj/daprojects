import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import os
import requests

# Downloading the dataset from Google Drive
file_id = '1Mqw3CrFphknTddLtGngJ_jRERV_rq0e-'
url = f'https://drive.google.com/uc?export=download&id={file_id}'
with open('gtanalysis.csv', 'wb') as f:
    f.write(requests.get(url).content)

# Loading the dataset
df = pd.read_csv('gtanalysis.csv', encoding='latin1', low_memory=False)

# Preprocessing the data
df = df[['iyear', 'imonth', 'country_txt', 'attacktype1_txt', 'targtype1_txt', 'latitude', 'longitude', 'nkill', 'nwound', 'gname']].copy()
df['nkill'] = pd.to_numeric(df['nkill'], errors='coerce').fillna(0).astype(int)
df['nwound'] = pd.to_numeric(df['nwound'], errors='coerce').fillna(0).astype(int)
df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

# Filtering out rows with invalid imonth (0)
df = df[df['imonth'] != 0]

# Creating date column for valid dates
df['date'] = pd.to_datetime(df['iyear'].astype(str) + '-' + df['imonth'].astype(str), format='%Y-%m', errors='coerce')
df = df.dropna(subset=['country_txt', 'attacktype1_txt', 'targtype1_txt', 'date'])

# Initializing the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # For gunicorn

# Defining the layout
app.layout = dbc.Container([
    html.H1("Global Terrorism Dashboard (Jan-Jun 2021)", className="text-center my-4"),
    
    # Filters
    dbc.Row([
        dbc.Col([
            html.Label("Select Country:"),
            dcc.Dropdown(
                id='country-dropdown',
                options=[{'label': 'All', 'value': 'All'}] + [{'label': c, 'value': c} for c in sorted(df['country_txt'].unique())],
                value='All',
                multi=False
            )
        ], width=6),
        dbc.Col([
            html.Label("Select Attack Type:"),
            dcc.Dropdown(
                id='attack-type-dropdown',
                options=[{'label': 'All', 'value': 'All'}] + [{'label': a, 'value': a} for a in sorted(df['attacktype1_txt'].unique())],
                value='All',
                multi=False
            )
        ], width=6)
    ], className="mb-4"),
    
    # Visualizations
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='attack-type-bar')
        ], width=6),
        dbc.Col([
            dcc.Graph(id='target-type-pie')
        ], width=6)
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='attack-map')
        ], width=12)
    ]),
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='trend-line')
        ], width=12)
    ])
], fluid=True)

# Callback to update charts based on filters
@app.callback(
    [Output('attack-type-bar', 'figure'),
     Output('target-type-pie', 'figure'),
     Output('attack-map', 'figure'),
     Output('trend-line', 'figure')],
    [Input('country-dropdown', 'value'),
     Input('attack-type-dropdown', 'value')]
)
def update_charts(selected_country, selected_attack_type):
    # Filtering the data
    filtered_df = df.copy()
    if selected_country != 'All':
        filtered_df = filtered_df[filtered_df['country_txt'] == selected_country]
    if selected_attack_type != 'All':
        filtered_df = filtered_df[filtered_df['attacktype1_txt'] == selected_attack_type]
    
    # Attack Type Bar Chart
    attack_counts = filtered_df['attacktype1_txt'].value_counts().reset_index()
    attack_counts.columns = ['Attack Type', 'Count']
    bar_fig = px.bar(
        attack_counts,
        x='Attack Type',
        y='Count',
        title='Number of Attacks by Attack Type',
        color='Attack Type',
        text='Count'
    )
    bar_fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Number of Attacks")
    
    # Target Type Pie Chart
    target_counts = filtered_df['targtype1_txt'].value_counts().reset_index()
    target_counts.columns = ['Target Type', 'Count']
    pie_fig = px.pie(
        target_counts,
        names='Target Type',
        values='Count',
        title='Distribution of Target Types'
    )
    pie_fig.update_traces(textinfo='percent+label')
    
    # Attack Map
    map_fig = px.scatter_geo(
        filtered_df,
        lat='latitude',
        lon='longitude',
        size=filtered_df['nkill'] + filtered_df['nwound'] + 1,  # Adding 1 to ensure visibility
        hover_name='country_txt',
        hover_data=['attacktype1_txt', 'targtype1_txt', 'nkill', 'nwound', 'gname'],
        title='Geographical Distribution of Attacks',
        projection='natural earth'
    )
    map_fig.update_layout(geo=dict(showframe=False, showcoastlines=True))
    
    # Trend Line Chart
    trend_data = filtered_df.groupby('date').size().reset_index(name='Count')
    line_fig = px.line(
        trend_data,
        x='date',
        y='Count',
        title='Trend of Attacks Over Time',
        markers=True
    )
    line_fig.update_layout(xaxis_title="Month", yaxis_title="Number of Attacks")
    
    return bar_fig, pie_fig, map_fig, line_fig

# Running the app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run(host='0.0.0.0', port=port)
