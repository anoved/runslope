#!/usr/bin/python

import csv
import re

from pysvg.shape import *
from pysvg.structure import *
from pysvg.style import *
from pysvg.text import *
from pysvg.builders import StyleBuilder

config = {
	'vscale': 1.25,
	'fontsize': 9,
	'linespan': 120,
	'minvgap': 7
}

# List of dicts with keys: RACE, NAME, TIME, SECONDS
data = []

# convert elapsed time string (eg, "H:MM:SS.S") to seconds
def seconds(elapsed):
	m = re.match("^(?:(?:(\d+)\:)?(\d+)\:)?(\d+(?:\.\d+)?)$", elapsed)
	seconds = float(m.group(3))
	if m.group(2) != None:
		seconds += float(m.group(2)) * 60
		if m.group(1) != None:
			seconds += float(m.group(1)) * 60 * 60
	return seconds

# read results table into data list
with open('freeze.csv', 'rb') as f:
	reader = csv.DictReader(f)
	for row in reader:
		row['SECONDS'] = seconds(row['TIME'])
		data.append(row)

# optionally take only those that are present for all races (hardcoded == 4 hack)
#data = filter(lambda q: len(filter(lambda k: k['NAME'] == q['NAME'], data)) == 4, data)

# first, sort by time for bounds checking
data.sort(key=lambda row: row['SECONDS'])

# min and max second value
mins = data[0]['SECONDS']
maxs = data[-1]['SECONDS']
srange = maxs - mins

# unique race ids
racekeys = []

for i in range(1, len(data)):
	if data[i]['RACE'] not in racekeys:
		racekeys.append(data[i]['RACE'])

# next, sort by RACE, then SECONDS, then NAME (basically, restore input format)
# could probably sort and filter at once with one list expression...
data.sort(key=lambda rec: (rec['RACE'], rec['SECONDS'], rec['NAME']))

races = []
for key in sorted(racekeys):
	results = filter(lambda result: result['RACE'] == key, data)
		
	for n in range(0, len(results)):
		results[n]['RANK'] = n + 1
	
	# result count per race (for char count for column)
	resultcount = len(results)
	mc_rank = len("%d" % resultcount)
	
	# super clumsiest way to do this
	ns = sorted(results, key=lambda rec: len(rec['NAME']), reverse=True)
	mc_name = len(ns[0]['NAME'])
	
	ts = sorted(results, key=lambda rec: (len(rec['TIME']), rec['SECONDS']), reverse=True)
	mc_time = len(ts[0]['TIME'])
	
	races.append({
		'wmax_label': mc_rank + 2 + mc_name + 1 + mc_time,
		'label_format': '%' + str(mc_rank) + 'd. %-' + str(mc_name) + 's %' + str(mc_time) + 's',
		'results': results
	})

svg_file = svg()

svg_style = StyleBuilder()
svg_style.setFontFamily(fontfamily="monospace")
svg_style.setFontSize('9px')
svg_style.setFilling(fill='gray')

svg_linkline = StyleBuilder()
svg_linkline.setStrokeWidth(1)
svg_linkline.setStroke('#ccc')

svg_fadeline = StyleBuilder()
svg_fadeline.setStrokeWidth(0.5)
svg_fadeline.setStroke('#ddd')

svg_scalestyle = StyleBuilder()
svg_scalestyle.setStrokeWidth(6)
svg_scalestyle.setStroke('#eef')

svg_labels = g()
svg_labels.set_style(svg_style.getStyle())
svg_labels.setAttribute('xml:space', 'preserve')

svg_llines = g()
svg_llines.set_style(svg_linkline.getStyle())

svg_flines = g()
svg_flines.set_style(svg_fadeline.getStyle())

svg_scale = g()
svg_scale.set_style(svg_scalestyle.getStyle())

for r in range(0, len(races)):
	
	# left and right positions of race results - could calc in earlier loop
	races[r]['xl'] = (races[r-1]['xr'] + config['linespan'] if r > 0 else 0)
	races[r]['xr'] = races[r]['xl'] + 0.666 * (races[r]['wmax_label'] * config['fontsize'])
	# max label char count * font size seems a poor estimate of actual label width
	# - it's about 1.5 times larger than actual rendered label width.
	# experiment with http://www.w3.org/TR/SVG/text.html#TextElementTextLengthAttribute
	#  to specify *intended* label width, and see if the browser/layout engine
	#  will automatically fudge the text dimensions satisfactorily for alignment
	
	svg_lgroup = g()
	
	for i in range(0, len(races[r]['results'])):
		
		rec = races[r]['results'][i]
		
		# value we have to position
		y = config['vscale'] * (rec['SECONDS'] - mins)
		
		# push collisions downward
		if i > 0 and y - races[r]['results'][i-1]['y'] < config['minvgap']:
			y = races[r]['results'][i-1]['y'] + config['minvgap']
		
		races[r]['results'][i]['y'] = y
		
		# draw result label
		label =  races[r]['label_format'] % (rec['RANK'], rec['NAME'], rec['TIME'])
		svg_label = text(label, races[r]['xl'], y)
		svg_lgroup.addElement(svg_label)
		
		p = r
		while p > 0:
			p -= 1
			
			# look for results with the same name in this previous race
			matches = filter(lambda cand: cand['NAME'] == rec['NAME'], races[p]['results'])
			
			# if a match is found, draw a link and stop looking for matches
			if len(matches) == 1:
				
				svg_link = line(
					races[p]['xr'] - 5,
					matches[0]['y'] - 3,
					races[r]['xl'] + 5,
					y - 3)
				
				if p == r - 1:
					# links to the immediately previous race are emphasized
					svg_llines.addElement(svg_link)
				else:
					# links to earlier races are drawn in a separate group
					svg_flines.addElement(svg_link)
				
				break
	
	svg_labels.addElement(svg_lgroup)

# scale bars every minute from before first to after last finisher
start_s = (int(mins)/60) * 60
end_s = 120 + ((int(maxs)/60) * 60)
for s in range(start_s, end_s, 60):
	y = config['vscale'] * (s - mins)
	scaleline = line(0, y, races[-1]['xr'], y)
	svg_scale.addElement(scaleline)

svg_file.addElement(svg_scale)
svg_file.addElement(svg_flines)
svg_file.addElement(svg_llines)
svg_file.addElement(svg_labels)
svg_file.save('./test.svg')

