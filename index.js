console.log('hello world');

// d3
//     .select('#d3')
//     .append('svg')
//     .attr("width", 100)
//     .attr("height", 100)
//     .append("text")
//     .attr("x", 10) // Set the x position of the text
//     .attr("y", 50) // Set the y position of the text
//     .text('hello world') // Add the text content
//     .style('fill', 'black'); // Set the text color

// const svg = d3
//     .select('#d3')
//     .append('svg')
//     .attr("width", 100)
//     .attr("height", 100)
//     .attr("viewBox", `0 0 ${width} ${height}`);

// // // create lines
// svg
//     .selectAll("line")
//     .data(data)
//     .join("line")
//     .attr("x1", 0)
//     // within our attr functions, we access attributes of the data
//     // here we scale our river length to the same
//     .attr("x2", function (d, i) {
//         return (d.lengthKm / maxLength) * width;
//     })
//     .attr("y1", yOffset)
//     .attr("y2", yOffset)
//     .style("stroke", (d) => `hsl(200, 90%, 40%)`);

const layout = {
    title: {
        text: "Karen's Resume",
        subtitle: {
            text: 'Click a data point to visit the source article.'
        },
        x: 0.14
    },
    font: {
        family: 'serif'
    },
    xaxis: {
        showgrid: true,
        showline: true,
        range: ['2014-1-1', '2026-1-1'],
        type: 'date',
        dtick: 'M12',
        ticklabelstep: 1
    },
    yaxis: {
        showgrid: false,
        showticklabels: false,
        range: [0, 40],
    },
    hovermode: 'closest',
    hoverlabel: {
        bgcolor: 'white'
    },
    showlegend: false,
    margin: {
        l: 120,
        r: 0,
    },
    height: 800
};

const config = {
    displayModeBar: false,
    responsive: true
};

var data;

function drawPlot(d) {
    // console.log(d);
    // console.log(d.map(row => row['Course/Role']))
    // var myPlot = document.getElementById('chart-div');

    let data = []; // Array to hold all traces

    // Get unique groups (e.g., Interests)
    const uniqueGroups = [...new Set(d.map(row => row.Type))];

    // Create a color scale using Plotly's color scheme
    const colorScale = d3.scaleOrdinal(d3.schemeAccent);
    console.log(colorScale)

    // Create a mapping of groups to colors
    const groupColors = {};
    uniqueGroups.forEach((group, index) => {
        groupColors[group] = colorScale(index); // Assign a color to each group
    });

    console.log(groupColors)

    // Iterate over each row in the dataset
    d.forEach(row => {
        // Create a line trace for each Start and End pair
        if (row.Type != 'student') {
            let lineTrace = {
                type: 'scatter',
                mode: 'lines',
                x: [row.Start, row.End], // X-coordinates for the line
                y: [row.Index, row.Index], // Y-coordinates for the line
                line: {
                    color: groupColors[row.Type], // Assign color based on Interest
                    width: 12
                },
                text: [row['Course/Role'], row['Course/Role']], // Hover text
                hoverinfo: 'text',
                hovertemplate: '%{text}<extra></extra>'
            };
    
            // Add the line trace to the data array
            data.push(lineTrace);
        }
    });

    console.log(data)

    Plotly.newPlot(
        'd3',
        data,
        layout,
        config
    );
}

async function init() {
    d3.json('./resources/resume.json', drawPlot);
}

// when page is loaded, define custom JS
document.addEventListener('DOMContentLoaded', function () {
    init();
});
