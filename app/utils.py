
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

config = {
    'displayModeBar': True,  # Show the mode bar
    'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'autoscale', 'zoomin', 'zoomout'],  # Remove some modebar options
    # 'scrollZoom': True,  # Allow scroll zoom
}