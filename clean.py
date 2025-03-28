# Preprocess data to cut down on load time

import pandas as pd
from datetime import datetime
import networkx as nx
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
                out += f'<span class="bubble">{bubble}</span>'
    out += '</div>'  

    if len(row['Award']):
        out += f"<span>🏆 {row['Award']}</span>"
    out += f"<p>{row['Description']}</p>"

    print(out)
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
    df['Index'] = df.groupby('Dummy').cumcount() + 1
    return df

def make_color_scale(unique_groups):
    """
    Create a dictionary mapping groups to colors in a specified palette

    Cite: Copilot
    """

    # Create a mapping of groups to colors
    color_scale = px.colors.qualitative.Safe 
    group_colors = {group: color_scale[i % len(color_scale)] for i, group in enumerate(unique_groups)}

    return group_colors

def make_graph_traces(G):
    """
    Generate plotly-compatible data for network graph

    Cite: https://plotly.com/python/network-graphs/
    """

    # Get unique interests
    unique_groups = list(set(nx.get_node_attributes(G, 'interests').values()))

    # Map each interest to a color
    interest_colors = make_color_scale(unique_groups)

    # Assign colors to nodes based on their interests
    node_colors = [interest_colors[G.nodes[node]['interests']] for node in G.nodes()]

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

    return edge_trace,node_trace
    

#%% store data

gantt = make_gantt_data(df)
gantt.to_excel('resources/gantt.xlsx',index=False)

G = make_graph_data(df)
edge_trace,node_trace=make_graph_traces(G)
pickle.dump(edge_trace, open('edge_trace.pickle', 'wb'))
pickle.dump(node_trace, open('node_trace.pickle', 'wb'))
