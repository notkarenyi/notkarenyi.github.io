import pickle
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
# future: use dash instead of shiny
from shiny.express import input, render, ui
import plotly.graph_objects as go
from shiny import reactive
from shinywidgets import render_plotly

from clean import make_color_scale

#%% UI and server

ui.include_css(
    'resources/css/index.css'
)

@reactive.calc
def filter_data():
    gantt = pd.read_excel('resources/gantt.xlsx',index_col=None)
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

config = {
    'displayModeBar': True,  # Show the mode bar
    'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'autoscale', 'zoomin', 'zoomout'],  # Remove some modebar options
    'scrollZoom': True,  # Allow scroll zoom
}

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
                    
            gantt = filter_data()

            xs = []
            ys = []
            groups = []
            # insight: can copy the syntax for graphing edges because this is also a discontinuous line chart
            for _, row in gantt.iterrows():
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
                
            #%% hover data layer 
            # click data events only register the top layer :/

            traces = []
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
                
            #%% color-coded can only be created with individual traces 

            # Create a mapping of groups to colors
            unique_groups = gantt[input.group_by()].unique()
            group_colors = make_color_scale(unique_groups)

            # group the gantt-compatible dataframe
            gantt_df = pd.DataFrame({
                'x':xs,
                'y':ys,
                'group':groups
            })

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

            layout = go.Layout(
                xaxis=dict(
                    showgrid=True,
                    showline=True,
                    range=[
                        min(
                            gantt.loc[gantt['Start']>datetime(1970,1,1),'Start']
                        ), 
                        datetime.today() + relativedelta(years=1)
                    ],
                    type='date',
                    dtick='M12',
                    ticklabelstep=1,
                    minallowed=min(
                        gantt.loc[gantt['Start']>datetime(1970,1,1),'Start']
                    ),
                    maxallowed=datetime.today() + relativedelta(years=3)
                ),
                yaxis=dict(
                    showgrid=False,
                    showticklabels=False,
                    zeroline=False,
                    range=[-1,len(gantt)+1],
                    minallowed=-1,
                    maxallowed=len(gantt)+1
                ),
                hovermode='y',
                dragmode='pan',
                height=min(len(gantt)*25+100,750),  # Adjust height based on number of rows
            )

            fig = go.Figure(
                data=traces, 
                layout=layout,
            )

            fig.update_layout(   
                template='plotly_white',
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=0-1/(len(gantt)**1.1)*3,
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
                gantt = filter_data()
                try:
                    text = gantt.loc[gantt['Index']==point['_ys'][0],'Text'].values[0]
                except Exception as e:
                    text = gantt['Text'].head(1).values[0]

                # express does not allow returns but displays each line dynamically 
                ui.HTML(text)
            else:
                point

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
            showticklabels=False,
            minallowed=-1.1,
            maxallowed=1.1,
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