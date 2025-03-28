import pandas as pd
from datetime import datetime
from shiny.express import input, render, ui
import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive
from shinywidgets import render_plotly
import networkx as nx

#%% read and clean data
df = pd.read_excel('resources/resume.xlsx',sheet_name='Graph',parse_dates=['Start','End'])

df['Start'] = df['Start'].fillna(datetime(2000,1,1))
df['End'] = df['End'].fillna(datetime(2000, 1, 1))
df['Interests'] = df['Interests'].fillna('N/A')

df = df.sort_values('Start')
df['Dummy'] = 1

df['Title'] = df['Course/Role'] + '<br />' + df['Organization'] + '<br />' + df['Interests']
df['Connection'] = [x.split(', ') if isinstance(x,str) else [] for x in df['Connection']]
df = df.explode('Connection')
df = df.sort_values('ID')

# print(df.loc[df['StartYear']==2023])
# print(df.columns)

#%% define functions

def make_graph_data(df):
    graph = df[['Title','ID','Connection','Interests']]
    graph['ID'] = graph['ID'].astype('int64')
    # graph = graph.loc[graph['Interests']!='N/A']
    graph = graph.rename(columns={
        'Title':'label',
        'ID':'source',
        'Connection':'target',
        'Interests': 'interests'
    })
    edges = graph.loc[~graph['target'].isnull(),['source','target']]
    edges['target'] = edges['target'].astype('int64')

    graph = graph.drop_duplicates('source')
    G = nx.Graph()
    G.add_nodes_from(graph['source'])
    G.add_edges_from([(row['source'],row['target']) for i,row in edges.iterrows()])
    nx.set_node_attributes(G, dict(zip(range(1,len(graph)+1),graph['label'].tolist())), "labels")
    nx.set_node_attributes(G, dict(zip(range(1,len(graph)+1),graph['interests'].tolist())), "interests")

    # Generate a layout (e.g., Kamada-Kawai layout)
    pos = nx.kamada_kawai_layout(G)

    # Assign the layout to the 'pos' attribute of each node
    nx.set_node_attributes(G, pos, 'pos')

    return G

def make_gantt_data(df):
    def create_text(row):
        out = ""
        for col in ['Course/Role','URL','Organization','Type','Interests','Skills','Technologies']:
            if isinstance(row[col],str):
                if col == 'URL':
                    out += '<a href="' + row[col] + '" target="blank_">'
                    continue
                if col == 'Organization':
                    out += row[col] + '</a>'
                else:
                    out += row[col]
                out += '<br />'
        return out

    not_student = df.loc[df['Type']!='student'].sort_values('Start')
    not_student = not_student.drop_duplicates('ID')
    not_student = not_student.loc[not_student['End']>datetime(2000,1,1)]
    not_student['Text'] = not_student.apply(create_text, axis=1)
    not_student['Index'] = not_student.groupby('Dummy').cumcount() + 1
    return not_student

#%% UI

ui.include_css(
    'resources/css/index.css'
)

ui.input_selectize(
    "group_by", 
    "Group by", 
    choices=['Type','Interests'], 
    selected='Type'
)

ui.input_selectize(
    "filter_by", 
    "Filter by", 
    choices=['Main','Jobs','All'], 
    selected='Main'
)

#%% server

# "Click info"
# @render.code
# def click_info():
#     return str(click_reactive.get())

# Capture the clicked point in a reactive value
click_reactive = reactive.value() 

def on_point_click(trace, points, state): 
    click_reactive.set(points) 

ui.h2("Resume")

# Create Gantt chart
# The native function does not work with Shiny for some reason
@render_plotly  
def gantt():  

    not_student = make_gantt_data(df)

    if input.filter_by() == 'Jobs':
        not_student = not_student.loc[not_student['Type']!='member']
        not_student = not_student.loc[not_student['Type']!='volunteer']
    elif input.filter_by() == 'Main':
        not_student = not_student.loc[not_student['Main']==True]

    not_student['Index'] = range(len(not_student))  # Create a new index for y-axis]

    traces = []  # List to hold all traces

    # Get unique groups (e.g., Interests)
    unique_groups = not_student[input.group_by()].unique()

    # Create a mapping of groups to colors
    color_scale = px.colors.qualitative.Safe 
    group_colors = {group: color_scale[i % len(color_scale)] for i, group in enumerate(unique_groups)}

    # Iterate over each row in the dataset
    for _, row in not_student.iterrows():
        if row[input.group_by()] != 'student':  # Filter out rows with Type == 'student'
            line_trace = go.Scatter(
                x=[row['Start'], row['End']],  # X-coordinates for the line
                y=[row['Index'], row['Index']],  # Y-coordinates for the line
                mode='lines',
                line=dict(
                    color=group_colors[row[input.group_by()]],  # Assign color based on Type
                    width=15
                ),
                text=[row['Text'],row['Text']],  # Hover text
                hoverinfo='text',
                hovertemplate='%{text}<extra></extra>',
                showlegend=False
            )
            # Add the line trace to the list
            traces.append(line_trace)

    # Create the layout
    layout = go.Layout(
        xaxis=dict(
            showgrid=True,
            showline=True,
            range=[
                min(
                    not_student.loc[not_student['Start']>datetime(1970,1,1),'Start']
                ), 
                '2026-01-01'
            ],  # Adjust the range as needed
            type='date',
            dtick='M12',
            ticklabelstep=1
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
        ),
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white'
        ),
        height=len(not_student) * 20+100,  # Adjust height based on number of rows
    )

    colorbar_traces = []
    # https://community.plotly.com/t/adding-custom-legend-in-plotly/65610/3
    for k,v in group_colors.items():
        trace = go.Scatter(
            x=[None],  # Dummy x-coordinate
            y=[None],  # Dummy y-coordinate
            mode='markers',
            name=k,
            marker=dict(
                size=7, 
                symbol='circle',
                color=v,  # Colors for each group
            ),
            hoverinfo='none'
        )
        colorbar_traces.append(trace)

    # config = {
    #     'displayModeBar': True,  # Show the mode bar
    #     'modeBarButtonsToRemove': ['select2d', 'lasso2d'],  # Remove box select and lasso select
    #     'scrollZoom': True,  # Allow scroll zoom
    # }

    # Create the figure
    fig = go.Figure(
        data=traces + colorbar_traces, 
        layout=layout,
    )

    fig.update_layout(   
        template='plotly_white',
    )

    # plot as input
    # https://shiny.posit.co/py/components/outputs/plot-plotly/
    w = go.FigureWidget(fig.data, fig.layout) 
    w.data[0].on_click(on_point_click) 
    return w

ui.h2("Experience")

# https://plotly.com/python/network-graphs/
@render_plotly  
def network_graph():  

    G = make_graph_data(df)
        
    # Get unique interests
    unique_groups = list(set(nx.get_node_attributes(G, 'interests').values()))

    # Map each interest to a color
    color_scale = px.colors.qualitative.Safe  # Use a predefined color scale
    interest_colors = {interest: color_scale[i % len(color_scale)] for i, interest in enumerate(unique_groups)}

    # Assign colors to nodes based on their interests
    node_colors = [interest_colors[G.nodes[node]['interests']] for node in G.nodes()]

    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, 
        y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = G.nodes[node]['pos']
        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(
        x=node_x, 
        y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            size=20,
            line_width=2,
            color=node_colors,
        )
    )

    node_adjacencies = []
    node_text = []
    for node, adjacencies in enumerate(G.adjacency()):
        node_adjacencies.append(len(adjacencies[1])*2 + 8)
    for node in G.nodes():    
        node_text.append(G.nodes[node]['labels'])

    node_trace.marker.size = node_adjacencies
    node_trace.text = node_text

    axis = dict(
        showgrid=False, 
        zeroline=False, 
        showticklabels=False
    )

    fig = go.Figure(data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode='closest',
            annotations=[ 
                dict(
                    showarrow=True,
                    xref="paper", 
                    yref="paper",
                    x=0.005, y=-0.002 
                ) 
            ],
            xaxis=axis,
            yaxis=axis,
            height=800,
            width=800,
        )
    )

    fig.update_layout(   
        template='plotly_white',
    )

    return fig