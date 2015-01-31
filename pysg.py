#!/usr/bin/python

import sys
import csv
import re

from pysvg.shape import *
from pysvg.structure import *
from pysvg.style import *
from pysvg.text import *
from pysvg.builders import StyleBuilder

config = {
	'vscale': 1.5,
	'fontsize': 9,
	'linespan': 150,
	'minvgap': 9,
	'nohooky': False,
	'scalebars': True,
	'cutoff': '1:30:00',
	'alllinks': True,
	'curvy': 50
}

# List of dicts with keys: RACE, NAME, TIME, SECONDS
data = []
racekeys = []

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
reader = csv.DictReader(sys.stdin)
for row in reader:
	row['SECONDS'] = seconds(row['TIME'])
	if row['RACE'] not in racekeys:
		racekeys.append(row['RACE'])
	data.append(row)

# optionally take only those that are present for all races
# (retain record q if there are as many records w/that name as unique racekeys)
if config['nohooky']:
	data = filter(lambda q: len(filter(lambda k: k['NAME'] == q['NAME'], data)) == len(racekeys), data)

# discard results slower than cutoff time, if defined ("H:MM:SS" format)
if config['cutoff'] != None:
	cutoff = seconds(config['cutoff'])
	data = filter(lambda q: q['SECONDS'] <= cutoff, data)

# determine range of times
mins = min(data, key=lambda q: q['SECONDS'])['SECONDS']
maxs = max(data, key=lambda q: q['SECONDS'])['SECONDS']

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
svg_style.setFilling(fill='black')

svg_linkline = StyleBuilder()
svg_linkline.setStrokeWidth(1)
svg_linkline.setStroke('#ccc')

svg_fadeline = StyleBuilder()
svg_fadeline.setStrokeWidth(1)
svg_fadeline.setStroke('#dfdfdf')

svg_labels = g()
svg_labels.set_style(svg_style.getStyle())
svg_labels.setAttribute('xml:space', 'preserve')

svg_llines = g()
svg_llines.set_style(svg_linkline.getStyle())

svg_flines = g()
svg_flines.set_style(svg_fadeline.getStyle())

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
		svg_label = text(label, races[r]['xl'], y-2)
		svg_lgroup.addElement(svg_label)
		
		# hacky flag to keep track of linked results for underlining
		races[r]['results'][i]['LINKED'] = False
		
		p = r
		while p > 0:
			p -= 1
			
			# don't look for name links in earlier races if not requested
			if (not config['alllinks']) and (p < r - 1):
				break
			
			# look for results with the same name in this previous race
			matches = filter(lambda cand: cand['NAME'] == rec['NAME'], races[p]['results'])
			
			# if a match is found, draw a link and stop looking for matches
			if len(matches) == 1:
				
				# underline linked labels
				underline = line(races[r]['xl'], y, races[r]['xr'], y)
				svg_llines.addElement(underline)
				races[r]['results'][i]['LINKED'] = True
				
				# backtrack to underline first instance of a linked label
				if not matches[0]['LINKED']:
					underline = line(races[p]['xl'], matches[0]['y'], races[p]['xr'], matches[0]['y'])
					svg_llines.addElement(underline)
				
				if config['curvy'] > 0:
					svg_link = path('M ' + str(races[p]['xr']) + ',' + str(matches[0]['y']))
					svg_link.setAttribute('fill', 'none')
					svg_link.appendCubicCurveToPath(
						races[p]['xr'] + config['curvy'], matches[0]['y'],
						races[r]['xl'] - config['curvy'], y,
						races[r]['xl'], y,
						relative=False)
				else:
					svg_link = line(races[p]['xr'], matches[0]['y'], races[r]['xl'], y)
				
				if p == r - 1:
					# links to the immediately previous race are emphasized
					svg_llines.addElement(svg_link)
				else:
					# links to earlier races are drawn in a separate group
					svg_flines.addElement(svg_link)
				
				break
	
	svg_labels.addElement(svg_lgroup)

# scale bars every minute from before first to after last finisher
if config['scalebars']:
	svg_scalestyle = StyleBuilder()
	svg_scalestyle.setStrokeWidth(16)
	svg_scalestyle.setStroke('#f8f8ff')
	svg_scale = g()
	svg_scale.set_style(svg_scalestyle.getStyle())
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
print svg_file.getXML()
