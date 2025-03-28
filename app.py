import pickle
import pandas as pd
from datetime import datetime
import networkx as nx
from shiny.express import input, render, ui
import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive
from shinywidgets import render_plotly

from clean import make_color_scale

#%% UI and server

ui.include_css(
    'resources/css/index.css'
)

# Capture the hovered point in a reactive value
hover_reactive = reactive.value() 

def on_hover(trace, points, state): 
    hover_reactive.set(points.__dict__) 

with ui.card():

    ui.h2("Resume")
        
    with ui.layout_column_wrap(gap="2em"):
        
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

    # Create Gantt chart
    # The native function does not work with Shiny for some reason
    @render_plotly  
    def gantt():  
                
        gantt = pd.read_excel('resources/gantt.xlsx',index_col=None)

        if input.filter_by() == 'Jobs':
            gantt = gantt.loc[gantt['Type']!='member']
            gantt = gantt.loc[gantt['Type']!='volunteer']
        elif input.filter_by() == 'Main':
            gantt = gantt.loc[gantt['Main']==True]

        gantt['Index'] = range(len(gantt))  # Create a new index for y-axis]

        traces = []

        #%% hover data layer 
        # click data events only register the top layer :/

        xs = []
        ys = []
        groups = []
        for _, row in gantt.iterrows():
            xs.append(row['Start'])
            xs.append(row['End'])
            xs.append(None) # pick up pen
            ys.append(row['Index'])
            ys.append(row['Index'])
            ys.append(None)
            # Assign color based on Type
            groups.append(row[input.group_by()])
            groups.append(row[input.group_by()])
            groups.append(None)

        traces.append(go.Scatter(
            x=xs,
            y=ys,
            mode='lines',
            hoverinfo='none',
            line={
                'width':12
            },
            opacity=0,
            showlegend=False
        )) 
            
        #%% color-coded can only be created with individual traces 

        # Create a mapping of groups to colors
        unique_groups = gantt[input.group_by()].unique()
        color_scale = px.colors.qualitative.Safe 
        group_colors = {group: color_scale[i % len(color_scale)] for i, group in enumerate(unique_groups)}

        # Iterate over each row in the dataset
        for _, row in gantt.iterrows():
            if row[input.group_by()] != 'student':  # Filter out rows with Type == 'student'
                line_trace = go.Scatter(
                    x=[row['Start'], row['End']],  # X-coordinates for the line
                    y=[row['Index'], row['Index']],  # Y-coordinates for the line
                    mode='lines',
                    line=dict(
                        color=group_colors[row[input.group_by()]],  # Assign color based on Type
                        width=15
                    ),
                    hoverinfo='none',
                    showlegend=False
                )
                # Add the line trace to the list
                traces.append(line_trace)

        # config = {
        #     'displayModeBar': True,  # Show the mode bar
        #     'modeBarButtonsToRemove': ['select2d', 'lasso2d'],  # Remove box select and lasso select
        #     'scrollZoom': True,  # Allow scroll zoom
        # }

        layout = go.Layout(
            xaxis=dict(
                showgrid=True,
                showline=True,
                range=[
                    min(
                        gantt.loc[gantt['Start']>datetime(1970,1,1),'Start']
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
            hovermode='y',
            dragmode='pan',
            height=len(gantt) * 20+100,  # Adjust height based on number of rows
        )

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
            traces.append(trace)

        fig = go.Figure(
            data=traces, 
            layout=layout,
        )

        fig.update_layout(   
            template='plotly_white',
        )

        # plot as input
        # https://shiny.posit.co/py/components/outputs/plot-plotly/
        w = go.FigureWidget(fig.data, fig.layout) 
        w.data[0].on_hover(on_hover) 
        return w
    
    @render.express
    def hover_info():
        gantt = pd.read_excel('resources/gantt.xlsx',index_col=None)

        if input.filter_by() == 'Jobs':
            gantt = gantt.loc[gantt['Type']!='member']
            gantt = gantt.loc[gantt['Type']!='volunteer']
        elif input.filter_by() == 'Main':
            gantt = gantt.loc[gantt['Main']==True]

        gantt['Index'] = range(len(gantt))  # Create a new index for y-axis]

        point = hover_reactive.get()
        text = gantt.loc[gantt['Index']==point['_ys'][0],'Text'].values[0]

        # express does not allow returns but displays each line dynamically 
        ui.HTML(text)

with ui.card():
    ui.h2("Experience")

    # https://plotly.com/python/network-graphs/
    @render_plotly  
    def network_graph():  

        # load graph object from file
        edge_trace = pickle.load(open('edge_trace.pickle', 'rb'))
        node_trace = pickle.load(open('node_trace.pickle', 'rb'))

        axis = dict(
            showgrid=False, 
            zeroline=False, 
            showticklabels=False
        )

        fig = go.Figure(data=[edge_trace, node_trace],
            layout=go.Layout(
                showlegend=False,
                dragmode='pan',
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
                height=750,
                width=750,
            )
        )

        fig.update_layout(   
            template='plotly_white',
        )

        return fig