import pandas as pd
from datetime import datetime
from shiny.express import input, render, ui
import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive
from shinywidgets import render_plotly
import igraph as ig
import numpy as np

df = pd.read_excel('resources/resume.xlsx',sheet_name='Graph',parse_dates=['Start','End'])

df['Start'] = df['Start'].fillna(datetime(2000,1,1))
df['End'] = df['End'].fillna(datetime(2000, 1, 1))
df['Interests'] = df['Interests'].fillna('N/A')

df = df.sort_values('Start')
df['Dummy'] = 1

df['Title'] = df['Course/Role'] + df['Organization']
df['Connection'] = [x.split(', ') if isinstance(x,str) else [] for x in df['Connection']]
df = df.explode('Connection')
graph = df[['Title','ID','Connection']]
graph['ID'] = graph['ID'].astype('int64')
graph = graph.rename(columns={
    'Title':'label',
    'ID':'from',
    'Connection':'to'
})
edges = graph.loc[~graph['to'].isnull(),['from','to']]
edges['to'] = edges['to'].astype('int64')
G = ig.Graph.DataFrame(
    edges, 
    directed=True,
    # vertices=graph[['from','label']]
)

# print(df['StartMonth'])
# print(df.loc[df['StartYear']==2023])
# print(df.columns)

# df.to_json('resources/resume.json', orient='records')

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
not_student = not_student.loc[not_student['End']>datetime(2000,1,1)]
not_student['Text'] = not_student.apply(create_text, axis=1)
not_student['Index'] = not_student.groupby('Dummy').cumcount() + 1

ui.h1("Karen's Resume")

ui.input_selectize(
    "group_by", 
    "Group by", 
    choices=['Type','Interests'], 
    selected='Type'
)

"Click info"
@render.code
def click_info():
    return str(click_reactive.get())

@render_plotly  
def graph():  
    # labels=list(G.vs['label'])
    # N=len(labels)
    N = len(G.vs)
    E=[e.tuple for e in G.es]# list of edges
    layt=G.layout('kk') #kamada-kawai layout
        
    Xn=[layt[k][0] for k in range(N)]
    Yn=[layt[k][1] for k in range(N)]
    Xe=[]
    Ye=[]
    for e in E:
        Xe+=[layt[e[0]][0],layt[e[1]][0], None]
        Ye+=[layt[e[0]][1],layt[e[1]][1], None]

    trace1=go.Scatter(x=Xe,
        y=Ye,
        mode='lines',
        line= dict(color='rgb(210,210,210)', width=1),
        hoverinfo='none'
    )
    trace2=go.Scatter(x=Xn,
        y=Yn,
        mode='markers',
        name='ntw',
        marker=dict(symbol='circle-dot',
                                    size=5,
                                    color='#6959CD',
                                    line=dict(color='rgb(50,50,50)', width=0.5)
                                    ),
        # text=labels,
        # hoverinfo='text'
    )

    axis=dict(
        showline=False, # hide axis line, grid, ticklabels and  title
        zeroline=False,
        showgrid=False,
        showticklabels=False,
        title=''
    )

    width=800
    height=800
    # layout=go.Layout(title= "Coauthorship network of scientists working on network theory and experiment"+\
    #             "<br> Data source: <a href='https://networkdata.ics.uci.edu/data.php?id=11'> [1]</a>",
    #     font= dict(size=12),
    #     showlegend=False,
    #     autosize=False,
    #     width=width,
    #     height=height,
    #     xaxis=layout.XAxis(axis),
    #     yaxis=layout.YAxis(axis),
    #     margin=layout.Margin(
    #         l=40,
    #         r=40,
    #         b=85,
    #         t=100,
    #     ),
    #     hovermode='closest',
    #     annotations=[
    #         dict(
    #         showarrow=False,
    #             text='This igraph.Graph has the Kamada-Kawai layout',
    #             xref='paper',
    #             yref='paper',
    #             x=0,
    #             y=-0.1,
    #             xanchor='left',
    #             yanchor='bottom',
    #             font=dict(
    #             size=14
    #             )
    #             )
    #         ]
    #     )

    data=[trace1, trace2]
    fig=go.Figure(
        data=data, 
        # layout=layout
    )
    return fig

# Create Gantt chart
# The native function does not work with Shiny for some reason
@render_plotly  
def plot():  

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
                    width=12
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
            range=['2014-01-01', '2026-01-01'],  # Adjust the range as needed
            type='date',
            dtick='M12',
            ticklabelstep=1
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
        ),
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='white'
        ),
        height=600,        
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

# Capture the clicked point in a reactive value
click_reactive = reactive.value() 

def on_point_click(trace, points, state): 
    click_reactive.set(points) 
