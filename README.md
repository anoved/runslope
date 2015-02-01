# runslope

Visualize race results as a [slopegraph](http://www.edwardtufte.com/bboard/q-and-a-fetch-msg?msg_id=0003nk) with finishing times for each race in a series as the variable. The distribution of finishers at each race can be compared and each individual's performance can be traced through the series.

## Usage

Reads race results in CSV format from standard input. Prints SVG XML to standard output. 

Expected CSV fields are: `RACE` (arbitrary sequentially-sortable identifiers), `NAME` (assumed unique; may appear multiple times, no more than once per `RACE`), and `TIME` (H:MM:SS format).

Options are set by editing `config` values directly in the code.

	./runslope.py <results.csv >slopegraph.svg

## Scope

The focus is on positioning result labels and link lines. Not intended to support every option needed to produce arbitrary publication-ready graphics. Import the output into a page layout program and select element groups to adjust styles or add annotations.

## Prerequisites

Requires [PySVG](https://code.google.com/p/pysvg/).

## Acknowledgements

Modeled after Ben Concutere's [sg](https://github.com/concutere/sg).

## License

This project is released under an open source [MIT license](http://opensource.org/licenses/MIT).
