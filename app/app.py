# Instructions:
# 1. Install the VSCode Shiny extension and use the dropdown by the Play button to launch the app locally for debugging.
# 2. Comment out each card to deploy each app. This is because Shiny expects the app to be in app.py and all required dependencies must be in the same directory.
# 3. Deploy using `rsconnect deploy shiny app --name notkarenyi --title resume`

#%% imports

import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
# future: use dash instead of shiny
from shiny.express import input, render, ui
import plotly.graph_objects as go
from shiny import reactive
from shinywidgets import render_plotly
import pickle

from utils import make_color_scale, config

# import os
# print(os.getcwd())
# if not os.getcwd().endswith('app'):
#     os.chdir('app')

#%% server

@reactive.calc
def filter_data():
    gantt = pd.read_excel('gantt.xlsx',index_col=None)
    gantt['End'] = [datetime.today() if x==datetime(2100,1,1) else x for x in gantt['End']]
    gantt['Text'] = gantt['Text'].apply(lambda x: x.replace('1/2100','Present'))

    if input.filter_by() == 'Jobs':
        gantt = gantt.loc[gantt['Type']!='member']
        gantt = gantt.loc[gantt['Type']!='volunteer']
    elif input.filter_by() == 'Main':
        gantt = gantt.loc[gantt['Main']==True]
    elif input.filter_by() == 'Awards':
        gantt['Award'] = gantt['Award'].fillna('')
        gantt = gantt.loc[gantt['Award']!='']

    if not input.filter_by() == 'Awards':
        gantt = gantt.loc[gantt['Type']!='student']

    gantt['Index'] = range(len(gantt))  # Create a new index for y-axis]

    return gantt

# Capture the hovered point in a reactive value
hover_reactive = reactive.value("Click or hover over data to view details. Double-click to reset pan or zoom.") 

def on_hover(_, points, __): 
    hover_reactive.set(points.__dict__)

def create_layout(gantt_data):
    
    return go.Layout(
        xaxis=dict(
            showgrid=True,
            showline=True,
            range=[
                min(
                    gantt_data.loc[gantt_data['Start']>datetime(1970,1,1),'Start']
                ), 
                datetime.today() + relativedelta(years=1)
            ],
            type='date',
            dtick='M12',
            ticklabelstep=1,
            minallowed=min(
                gantt_data.loc[gantt_data['Start']>datetime(1970,1,1),'Start']
            ),
            maxallowed=datetime.today() + relativedelta(years=5)
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            range=[-.5,len(gantt_data)+.5],
            minallowed=-1,
            maxallowed=len(gantt_data)+1
        ),
        hovermode='y',
        dragmode='pan',
        height=min(len(gantt_data)*25+100,750),  # Adjust height based on number of rows
    )

def create_traces(xs, ys, groups, group_colors):
    # group the gantt-compatible dataframe
    gantt_df = pd.DataFrame({
        'x':xs,
        'y':ys,
        'group':groups
    })

    traces = []
    # click data events only register the top layer :/
    traces.append(go.Scatter(
        x=xs,
        y=ys,
        mode='lines',
        hoverinfo='none',
        line={
            'width':15
        },
        opacity=0,
        showlegend=False
    )) 

    # Iterate over each group in the dataset
    for group in gantt_df.groupby('group'):
        traces.append(go.Scatter(
            name=group[0],
            x=group[1]['x'].tolist(),
            y=group[1]['y'].tolist(),
            mode='lines',
            hoverinfo='none',
            line=dict(
                color=group_colors[group[1]['group'].unique()[0]],  # Assign color based on Type
                width=15
            ),
        ))

    return traces

def make_groups(gantt_data):
    xs = []
    ys = []
    groups = []
    # insight: can copy the syntax for graphing edges because this is also a discontinuous line chart
    for _, row in gantt_data.iterrows():
        xs.append(row['Start'])
        xs.append(row['End'])
        xs.append(None) # pick up pen
        ys.append(row['Index'])
        ys.append(row['Index'])
        ys.append(row['Index']) # out of range float values are not JSON compliant
        # Assign color based on Type
        groups.append(row[input.group_by()])
        groups.append(row[input.group_by()])
        groups.append(row[input.group_by()]) # we have to keep this as the id column when picking up pen

    return xs, ys, groups

#%% UI

ui.include_css(
    'css/index.css'
)

with ui.card():

    ui.h2("Resume")
        
    with ui.layout_column_wrap(gap="1rem"):
        
        ui.input_selectize(
            "group_by", 
            "Group by", 
            choices=['Type','Interests'], 
            selected='Type'
        )
        ui.input_selectize(
            "filter_by", 
            "Filter by", 
            choices=['Main','Jobs','Awards','All'], 
            selected='Main'
        )

    with ui.layout_columns(gap="1rem"):
                
        # Create Gantt chart
        # The native function does not work with Shiny for some reason
        @render_plotly  
        def gantt_chart():  
                    
            gantt_data = filter_data()

            xs, ys, groups = make_groups(gantt_data)
                
            #%% hover data layer 
            # color-coded can only be created with individual traces 

            # Create a mapping of groups to colors
            unique_groups = gantt_data[input.group_by()].unique()
                    
            fig = go.Figure(
                data=create_traces(
                    xs=xs,
                    ys=ys,
                    groups=groups,
                    group_colors=make_color_scale(unique_groups)
                ), 
                layout=create_layout(gantt_data),
            )

            fig.update_layout(   
                template='plotly_white',
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=0-1/(len(gantt_data)**1.1)*3.5,
                    xanchor="left",
                    x=-.04
                )
            )

            # plot as input
            # https://shiny.posit.co/py/components/outputs/plot-plotly/
            # https://stackoverflow.com/questions/78989286/how-to-pass-config-options-to-plotly-in-shiny-for-python
            widget = go.FigureWidget(fig) 
            widget.data[0].on_hover(on_hover) 
            widget.data[0].on_click(on_hover) 
            widget._config = config

            return widget

        @render.express
        def hover_info():
            point = hover_reactive.get()

            if not isinstance(point,str):
                gantt_data = filter_data()
                try:
                    text = gantt_data.loc[gantt_data['Index']==point['_ys'][0],'Text'].values[0]
                except Exception as e:
                    text = gantt_data['Text'].head(1).values[0]

                # express does not allow returns but displays each line dynamically 
                ui.HTML(text)
            else:
                point


with ui.card():
    ui.h2("Experience")

    'Experiences are connected if the former was either useful to or directly inspired the latter.'

    # https://plotly.com/python/network-graphs/
    @render_plotly  
    def network_graph():  

        # load graph object from file
        edge_trace = pickle.load(open('edge_trace.pickle', 'rb'))
        node_trace = pickle.load(open('node_trace.pickle', 'rb'))

        minimum = min([x for x in edge_trace['x'] if x!=None])
        maximum = max([x for x in edge_trace['x'] if x!=None])
        axis = dict(
            showgrid=False, 
            zeroline=False, 
            showticklabels=False,
            minallowed=minimum-(maximum-minimum)*.5,
            maxallowed=maximum+(maximum-minimum)*.5,
        )

        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                showlegend=False,
                dragmode='pan',
                hovermode='closest',
                xaxis=axis,
                yaxis=axis,
                height=750,
                width=750,
            ),
        )

        fig.update_layout(   
            template='plotly_white',
        )
    
        widget = go.FigureWidget(fig) 
        widget._config = config

        return widget
