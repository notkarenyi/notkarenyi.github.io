import pandas as pd
from datetime import datetime
from shiny.express import input, render, ui
import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive
from shinywidgets import render_plotly

df = pd.read_excel('resources/resume.xlsx',sheet_name='Graph',parse_dates=['Start','End'])

df['Start'] = df['Start'].fillna(datetime(2000,1,1))
df['End'] = df['End'].fillna(datetime(2000, 1, 1))

df = df.sort_values('Start')
df['Dummy'] = 1

# print(df['StartMonth'])
# print(df.loc[df['StartYear']==2023])
# print(df.columns)

# df.to_json('resources/resume.json', orient='records')

not_student = df.loc[df['Type']!='student'].sort_values('Start')
not_student = not_student.loc[not_student['End']>datetime(2000,1,1)]
not_student['Text'] = not_student['Course/Role'] + '<br /><a href="' +  not_student['URL'] + '" target="blank_">' + not_student['Organization'] + '</a><br />' + not_student['Type']
not_student['Index'] = not_student.groupby('Dummy').cumcount() + 1

ui.h1("Karen's Resume")

ui.input_selectize(
    "group_by", 
    "Group by", 
    choices=not_student.columns.tolist(), 
    selected='Type'
)

@render.code
def greeting():
    return 'm'

"Click info"
@render.code
def click_info():
    return str(click_reactive.get())

"""
Create Gantt chart
The native function does not work with Shiny for some reason
"""
@render_plotly  
def plot():  

    traces = []  # List to hold all traces

    # Get unique groups (e.g., Interests)
    unique_groups = not_student['Type'].unique()

    # Create a mapping of groups to colors
    color_scale = px.colors.qualitative.Safe 
    group_colors = {group: color_scale[i % len(color_scale)] for i, group in enumerate(unique_groups)}

    # Iterate over each row in the dataset
    for _, row in not_student.iterrows():
        if row['Type'] != 'student':  # Filter out rows with Type == 'student'
            line_trace = go.Scatter(
                x=[row['Start'], row['End']],  # X-coordinates for the line
                y=[row['Index'], row['Index']],  # Y-coordinates for the line
                mode='lines',
                line=dict(
                    color=group_colors[row['Type']],  # Assign color based on Type
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
