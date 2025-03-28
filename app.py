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

# "Click info"
# @render.code
# def click_info():
#     return str(click_reactive.get())

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
        
        # Get unique groups (e.g., Interests)
        unique_groups = gantt[input.group_by()].unique()

        group_colors = make_color_scale(unique_groups)

        styles = []
        for i,color in enumerate(group_colors.values()):
            styles.append({
                'target':unique_groups[i],
                'value': {
                    'marker': {
                        'color': color
                    }
                }
            })

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
            
        trace = go.Scatter(
            x=xs,
            y=ys,
            mode='lines',
            # transforms = [{
            #     type: 'groupby',
            #     groups: groups,
            #     styles: styles
            # }],
            hoverinfo='none',
            line={
                'width':12
            },
            showlegend=False
        )        

        # Create the layout
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

        # config = {
        #     'displayModeBar': True,  # Show the mode bar
        #     'modeBarButtonsToRemove': ['select2d', 'lasso2d'],  # Remove box select and lasso select
        #     'scrollZoom': True,  # Allow scroll zoom
        # }

        # Create the figure
        fig = go.Figure(
            data=trace, 
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
        text = gantt.loc[gantt['Index']==point['_ys'][0],'Title'].values[0]

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