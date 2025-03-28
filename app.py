import pandas as pd
from datetime import datetime
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

# Capture the clicked point in a reactive value
click_reactive = reactive.value() 

def on_point_click(trace, points, state): 
    click_reactive.set(points) 

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
            dragmode='pan',
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