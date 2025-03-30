# Preprocess data to cut down on load time

#%% imports

import os
import pathlib
import sys

# https://github.com/pygraphviz/pygraphviz/issues/186
if sys.platform == 'win32':
    path = pathlib.Path(r'C:\Program Files\Graphviz\bin')
    if path.is_dir() and str(path) not in os.environ['PATH']:
        os.environ['PATH'] += f';{path}'

import pandas as pd
from datetime import datetime
import networkx as nx
import pygraphviz
import plotly.express as px
import plotly.graph_objects as go
import pickle

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
    """
    Create a network from experiences dataframe

    Cite: https://medium.com/@harshkjoya/connecting-the-dots-creating-network-graphs-from-pandas-dataframes-with-networkx-9c4fb60089cf
    """

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
    G = nx.DiGraph()
    G.add_nodes_from(graph['source'])
    G.add_edges_from([(row['source'],row['target']) for i,row in edges.iterrows()])

    nx.set_node_attributes(
        G, 
        dict(zip(range(1,len(graph)+1),graph['label'].tolist())), 
        "labels"
    )
    nx.set_node_attributes(
        G, 
        dict(zip(range(1,len(graph)+1),graph['interests'].tolist())), 
        "interests"
    )

    # Generate a layout (e.g., Kamada-Kawai layout)
    # pos = nx.kamada_kawai_layout(G)
    # pos = nx.nx_agraph.graphviz_layout(G)
    pos = nx.nx_agraph.graphviz_layout(G,prog='twopi')

    # Assign the layout to the 'pos' attribute of each node
    nx.set_node_attributes(G, pos, 'pos')

    return G

def create_text(row):
    """
    Combine feature columns into stylized HTML
    """

    row = row.fillna("")

    out = ""
    out += f'<b>{row["Course/Role"]}</b>'
    out += f'<a href="{row["URL"]}" target="blank_">'
    out += f'{row["Organization"]}</a>'
    out += f'{row["Start"].month}/{row["Start"].year} - '
    out += f'{row["End"].month}/{row["End"].year}'

    out += '<div class="bubbles">'
    for col in ['Type','Interests','Skills','Technologies']:
        bubbles = row[col].split(', ')
        if len([x for x in bubbles if len(x)]):
            for bubble in bubbles:
                if bubble!='N/A':
                    out += f'<span class="bubble">{bubble}</span>'
    out += '</div>'  

    if len(row['Award']):
        out += f"<span>🏆 {row['Award']}</span>"
    out += f"<p>{row['Description']}</p>"

    # print(out)
    return out

def make_gantt_data(df):
    """
    Clean data for Gantt chart
    """
    
    # do not show coursework except associated with award
    df = df.loc[(df['Type']!='student') | (len(df['Award'])>0)].sort_values('Start')

    df = df.loc[df['End']>datetime(2000,1,1)]

    df = df.drop_duplicates('ID')

    df['Text'] = df.apply(create_text, axis=1)
    return df

def make_color_scale(unique_groups):
    """
    Create a dictionary mapping groups to colors in a specified palette

    Cite: Copilot
    """

    # px.colors.qualitative.Safe palette with some adjustments
    color_scale =  [
        'rgb(136, 204, 238)',
        'rgb(204, 102, 119)',
        'rgb(221, 204, 119)',
        'rgb(17, 119, 51)',
        'rgb(51, 34, 136)',
        'rgb(170, 68, 153)',
        'rgb(68, 170, 153)',
        'rgb(136, 180, 14)',
        'rgb(136, 34, 85)',
        'rgb(102, 17, 0)',
        'rgb(165, 165, 255)'
    ]

    # map to groups
    group_colors = {
        group: color_scale[i % len(color_scale)] for i, group in enumerate(unique_groups)
    }

    return group_colors

def make_edge_trace(G):
    """
    Generate plotly-compatible data for edges of network graph

    Cite: https://plotly.com/python/network-graphs/
    """

    edge_x = []
    edge_y = []
    for edge in G.edges():
        xstart, ystart = G.nodes[edge[0]]['pos']
        xend, yend = G.nodes[edge[1]]['pos']
        edge_x.append(xstart)
        edge_x.append(xend)
        edge_x.append(None) # pick up pen
        edge_y.append(ystart)
        edge_y.append(yend)
        edge_y.append(None) # pick up pen

    edge_trace = go.Scatter(
        x=edge_x, 
        y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode="lines+markers",
        # https://community.plotly.com/t/triangle-symbol-placed-at-the-end-of-a-line/81289/4
        marker={
            'symbol':'arrow',
            'angleref':"previous",
            'size':5,
            'standoff': 5,
        }
    )

    return edge_trace

def get_degrees(G):
    return [G.degree(node) for node in G.nodes()]

def make_node_trace(G):
    """
    Generate plotly-compatible data for nodes of network graph

    Cite: https://plotly.com/python/network-graphs/
    """

    # Get unique interests
    unique_groups = list(set(nx.get_node_attributes(G, 'interests').values()))

    # Map each interest to a color
    interest_colors = make_color_scale(unique_groups)

    # Assign colors to nodes based on their interests
    node_colors = [interest_colors[G.nodes[node]['interests']] for node in G.nodes()]
    
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
        text=[G.nodes[node]['labels'] for node in G.nodes()],
        hoverinfo='text',
        marker={
            'size': [x**.8*3+8 for x in get_degrees(G)],
            'line_width': 2,
            'color': node_colors,
            'opacity': 1,
        }
    )

    return node_trace    

#%% store data

gantt = make_gantt_data(df)
gantt.to_excel('resources/gantt.xlsx',index=False)

G = make_graph_data(df)
edge_trace=make_edge_trace(G)
node_trace=make_node_trace(G)
pickle.dump(edge_trace, open('edge_trace.pickle', 'wb'))
pickle.dump(node_trace, open('node_trace.pickle', 'wb'))
