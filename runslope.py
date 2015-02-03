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
	
	# Y value scaling. 1 is one vertical pixel per second.
	'vscale': 2,
	
	# Fixed width font characteristics
	'fontface': 'Monospace',
	'fontheight': 9,
	'fontwidth': 5.436,
	
	# Minimum allowable y overlap. If >0, overlapping labels are pushed down.
	'overlap': 10,
	
	# Pixel spacing between columns
	'linespan': 200,
	
	# If true, omit all results for names that did not attend all races
	'nohooky': False,
	
	# If true, create reference lines and label marking every minute
	'scalebars': True,
	
	# If not None, omit results slower than stated H:MM:SS time
	'cutoff': '1:30:00',
	
	# If true, link results even if the runner skipped intervening races
	# If false, links will only be drawn between consecutive races
	'alllinks': True,
	
	# If 0, links will be drawn as straight lines. Otherwise, gives horizontal
	# offset of control points from end points for drawing cubic Bezier curves.
	'curvy': 0,
	
	# If true, linked labels will be underlined, forming continuous lines
	'underline': True,
	
	# CSV field names
	'KEY_RACE': 'RACE',
	'KEY_TIME': 'TIME',
	'KEY_NAME': 'NAME'
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

def time(seconds):
	h = int(seconds) / 3600
	seconds -= h * 3600
	m = int(seconds) / 60
	seconds -= m * 60
	if (h > 0):
		return "%d:%02d:%02d" % (h, m, seconds)
	elif m > 0:
		return "%4d:%02d" % (m, seconds)
	return "%2d" % seconds

# read results table into data list
reader = csv.DictReader(sys.stdin)
for row in reader:
	row['SECONDS'] = seconds(row['TIME'])
	if row['RACE'] not in racekeys:
		racekeys.append(row['RACE'])
	rec = {
		'RACE': row[config['KEY_RACE']],
		'NAME': row[config['KEY_NAME']],
		'TIME': row[config['KEY_TIME']],
		'SECONDS': seconds(row[config['KEY_TIME']]),
	}
	data.append(rec)

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

# We assume input is pre-sorted by finishing order (per RACE, of course)
#data.sort(key=lambda rec: (rec['RACE'], rec['SECONDS'], rec['NAME']))

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
svg_style.setFontFamily(fontfamily=config['fontface'])
svg_style.setFontSize(str(config['fontheight']) + 'px')
svg_style.setFilling(fill='black')

svg_linkline = StyleBuilder()
svg_linkline.setStrokeWidth(1)
svg_linkline.setStroke('#bbb')

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
	races[r]['xr'] = races[r]['xl'] + (races[r]['wmax_label'] * config['fontwidth'])
	
	svg_lgroup = g()
	
	for i in range(0, len(races[r]['results'])):
		
		rec = races[r]['results'][i]
		
		# value we have to position
		y = config['vscale'] * (rec['SECONDS'] - mins)
		
		# push collisions downward
		if config['overlap'] > 0 and i > 0 and y - races[r]['results'][i-1]['y'] < config['overlap']:
			y = races[r]['results'][i-1]['y'] + config['overlap']
		
		races[r]['results'][i]['y'] = y
		
		# draw result label
		label =  races[r]['label_format'] % (rec['RANK'], rec['NAME'], rec['TIME'])
		y_label = (y - 2 if config['underline'] else y + (config['fontheight']/2))
		svg_label = text(label, races[r]['xl'], y_label)
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
				
				races[r]['results'][i]['LINKED'] = True
				
				if config['underline']:
					
					# underline linked labels
					underline = line(races[r]['xl'], y, races[r]['xr'], y)
					svg_llines.addElement(underline)
					
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

def Scalebars(smin, smax, xmin, xmax):
	
	c_lines = StyleBuilder()
	c_lines.setStrokeWidth(16)
	c_lines.setStroke('#f8f8ff')
	
	c_times = StyleBuilder()
	c_times.setFontFamily(fontfamily=config['fontface'])
	c_times.setFontSize('16px')
	c_times.setFilling(fill='#d8d8df')
	
	g_scale = g()
	g_scale_lines = g()
	g_scale_times = g()
	g_scale_lines.set_style(c_lines.getStyle())
	g_scale_times.set_style(c_times.getStyle())
	g_scale_times.setAttribute('xml:space', 'preserve')
	
	start = (int(smin) / 60) * 60
	end = 120 + ((int(smax) / 60) * 60)
	for s in range(start, end, 60):
		y = config['vscale'] * (s - smin)
		sline = line(xmin, y, xmax, y)
		stime = text(time(s), xmax + 5, y + 6)
		g_scale_lines.addElement(sline)
		g_scale_times.addElement(stime)
	
	g_scale.addElement(g_scale_lines)
	g_scale.addElement(g_scale_times)
	return g_scale

# scale bars every minute from before first to after last finisher
if config['scalebars']:
	svg_file.addElement(Scalebars(mins, maxs, 0, races[-1]['xr']))

svg_file.addElement(svg_flines)
svg_file.addElement(svg_llines)
svg_file.addElement(svg_labels)
print svg_file.getXML()

