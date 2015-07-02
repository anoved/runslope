#!/usr/bin/python

import sys
import csv
import re

from pysvg.shape import *
from pysvg.structure import *
from pysvg.style import *
from pysvg.text import *
from pysvg.builders import StyleBuilder

# Default configuration
config = {
	
	# Y value scaling. 1 is one vertical pixel per second.
	'vscale': 1.8,
	
	# Result label text
	'label_style': {'fill': 'black', 'font-family': 'Monospace'},
	'label_font_height': 9,
	'label_font_width': 5.436,
	
	# Scale bar label text
	'scale_style': {'fill': '#b8b8bf', 'font-family': 'Monospace'},
	'scale_font_height': 16,
	'scale_font_width': 9.6,

	# Minimum allowable y overlap. If >0, overlapping labels are pushed down.
	'overlap': 10,
	
	# Pixel spacing between columns
	'linespan': 233,
	
	# If not None, linespan is adjusted so chart fills a multiple of pagewidth
	# (Scalebar labels are *not* considered towards 
	'pagewidth': None,
	
	# Spacing between labels and link lines
	'gutter': 3,
	
	# If true, omit all results for names that did not compete in and
	# finish all races under cutoff time.
	'strict': False,
	
	# If true, create reference lines and label marking every minute
	'scalebars': True,
	
	# If true, place scale bars on left; otherwise, on right.
	'scaleleft': True,
	
	# If not None, omit results slower than stated H:MM:SS time
	'cutoff': None,
	
	# If true, all results links including those that skip races will be shown
	# If false, only links between consecutive race results will be shown
	'weaklink': True,
	
	# If 0, links will be drawn as straight lines. Otherwise, gives horizontal
	# offset of control points from end points for drawing cubic Bezier curves.
	# Expressed as percent of horizontal distance between endpoints (0.5 = 50%)
	'curvy': 0,
	
	# If 0, linked labels will not be underlined. Otherwise, labels will be
	# underlined; label baseline will be moved this value above underline.
	'underline': 0,
	
	# CSV field names
	'KEY_RACE': 'RACE',
	'KEY_TIME': 'TIME',
	'KEY_NAME': 'NAME',
	
	# Link line style definitions
	'linkline_style': {'stroke': '#bbb', 'stroke-width': '2'},
	'weaklink_style': {'stroke': '#bbb', 'stroke-width': '2', 'stroke-dasharray': '2,4'},
	'underline_style': {'stroke': '#bbb', 'stroke-width': '2'},
	'scaleline_style': {'stroke': '#eee', 'stroke-width': '16'},
}

if len(sys.argv) == 2:
	try:
		import yaml
		import os.path
		with open(sys.argv[1]) as config_file:
			config.update(yaml.safe_load(config_file))
	except ImportError:
		sys.exit('pyyaml is required to read external config files')

# List of dicts with keys: RACE, NAME, TIME, SECONDS, RANK
data = []
racekeys = []
racecounts = {}

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
		racecounts[row['RACE']] = 0
	racecounts[row['RACE']] += 1
	rec = {
		'RACE': row[config['KEY_RACE']],
		'NAME': row[config['KEY_NAME']],
		'TIME': row[config['KEY_TIME']],
		'SECONDS': seconds(row[config['KEY_TIME']]),
		'RANK': racecounts[row['RACE']]
	}
	data.append(rec)

# discard results slower than cutoff time, if defined ("H:MM:SS" format)
if config['cutoff'] != None:
	cutoff = seconds(config['cutoff'])
	data = filter(lambda q: q['SECONDS'] <= cutoff, data)

# in strict attendance mode, only retain results still present for all races 
# (retain record q if there are as many records w/that name as unique racekeys)
if config['strict']:
	data = filter(lambda q: len(filter(lambda k: k['NAME'] == q['NAME'], data)) == len(racekeys), data)

# determine range of times
mins = min(data, key=lambda q: q['SECONDS'])['SECONDS']
maxs = max(data, key=lambda q: q['SECONDS'])['SECONDS']

races = []
for key in sorted(racekeys):
	results = filter(lambda result: result['RACE'] == key, data)
		
	# longest rank string (represented by last place in result set)
	mc_rank = len(str(results[-1]['RANK']))
	
	# longest name string
	ns = sorted(results, key=lambda rec: len(rec['NAME']), reverse=True)
	mc_name = len(ns[0]['NAME'])
	
	# longest time string
	ts = sorted(results, key=lambda rec: (len(rec['TIME']), rec['SECONDS']), reverse=True)
	mc_time = len(ts[0]['TIME'])
	
	races.append({
		'wmax_label': mc_rank + 1 + mc_name + 1 + mc_time,
		'rank_label': '%-' + str(mc_rank) + 'd',
		'name_label': '%-' + str(mc_name) + 's',
		'time_label': '%' + str(mc_time) + 's',
		'name_xcoffset': (mc_rank + 1) * config['label_font_width'],
		'time_xcoffset': (mc_rank + 1 + mc_name + 1) * config['label_font_width'],
		'results': results
	})

# recalculate linespan to fill target page width (or a multiple thereof)
if config['pagewidth'] != None:
	actual_page_width = config['pagewidth']
	total_label_width = 0
	for r in races:
		total_label_width += r['wmax_label'] * config['label_font_width']
	while total_label_width > actual_page_width:
		actual_page_width += config['pagewidth']
	gap_count = len(races) - 1
	free_space = actual_page_width - total_label_width - (gap_count * 2 * config['gutter'])
	calc_linespan = free_space / gap_count
	config['linespan'] = calc_linespan

# SVG styles

s_label = StyleBuilder(config['label_style'])
s_label.setFontSize(str(config['label_font_height']) + 'px')

# SVG Groups

g_label = g()
g_label.set_style(s_label.getStyle())
g_label.setAttribute('xml:space', 'preserve')
g_linkline = g()
g_linkline.set_style(StyleBuilder(config['linkline_style']).getStyle())
g_weaklink = g()
g_weaklink.set_style(StyleBuilder(config['weaklink_style']).getStyle())
g_underline = g()
g_underline.set_style(StyleBuilder(config['underline_style']).getStyle())

for r in range(0, len(races)):
	
	# left and right positions of race results - could calc in earlier loop
	races[r]['xl'] = (races[r-1]['xr'] + config['linespan'] + (2 * config['gutter']) if r > 0 else 0)
	races[r]['xr'] = races[r]['xl'] + (races[r]['wmax_label'] * config['label_font_width'])
	
	# Group of labels for this race
	g_racelabels = g()
	g_ranklabels = g()
	g_namelabels = g()
	g_timelabels = g()
	
	for i in range(0, len(races[r]['results'])):
		
		rec = races[r]['results'][i]
		
		# value we have to position
		y = config['vscale'] * (rec['SECONDS'] - mins)
		
		# push collisions downward
		if config['overlap'] > 0 and i > 0 and y - races[r]['results'][i-1]['y'] < config['overlap']:
			y = races[r]['results'][i-1]['y'] + config['overlap']
		
		races[r]['results'][i]['y'] = y
		
		# draw result labels
		y_label = (y - config['underline'] if config['underline'] != 0 else y + (config['label_font_height']/2))
		g_ranklabels.addElement(text(races[r]['rank_label'] % (rec['RANK']), races[r]['xl'], y_label))
		g_namelabels.addElement(text(races[r]['name_label'] % (rec['NAME']), races[r]['xl'] + races[r]['name_xcoffset'], y_label))
		g_timelabels.addElement(text(races[r]['time_label'] % (rec['TIME']), races[r]['xl'] + races[r]['time_xcoffset'], y_label))
		
		# hacky flag to keep track of linked results for underlining
		races[r]['results'][i]['LINKED'] = False
		
		p = r
		while p > 0:
			p -= 1
			
			# don't look for name links in earlier races if not requested
			if (not config['weaklink']) and (p < r - 1):
				break
			
			# look for results with the same name in this previous race
			matches = filter(lambda cand: cand['NAME'] == rec['NAME'], races[p]['results'])
			
			# if a match is found, draw a link and stop looking for matches
			if len(matches) == 1:
				
				yy = matches[0]['y']
				races[r]['results'][i]['LINKED'] = True
				
				if config['underline'] != 0:
					
					# underline linked labels
					underline = line(
						races[r]['xl'] - config['gutter'], y,
						races[r]['xr'] + (0 if r + 1 == len(races) else config['gutter']), y)
					g_underline.addElement(underline)
					
					# backtrack to underline first instance of a linked label
					if not matches[0]['LINKED']:
						underline = line(
							races[p]['xl'] - (0 if p == 0 else config['gutter']), yy,
							races[p]['xr'] + config['gutter'], yy)
						g_underline.addElement(underline)
				
				if config['curvy'] > 0:
					l_link = path('M ' + str(races[p]['xr'] + config['gutter']) + ',' + str(yy))
					l_link.setAttribute('fill', 'none')
					linkspan = (races[r]['xl'] - config['gutter']) - (races[p]['xr'] + config['gutter']) 
					ctrlspan = linkspan * config['curvy']
					l_link.appendCubicCurveToPath(
						races[p]['xr'] + config['gutter'] + ctrlspan, yy,
						races[r]['xl'] - config['gutter'] - ctrlspan, y,
						races[r]['xl'] - config['gutter'], y,
						relative=False)
				else:
					l_link = line(races[p]['xr'] + config['gutter'], yy, races[r]['xl'] - config['gutter'], y)
				
				# slope tagging
				#if matches[0]['SECONDS'] < rec['SECONDS']:
				#	# got slower
				#	color = "#fbb"
				#elif matches[0]['SECONDS'] > rec['SECONDS']:
				#	# got faster
				#	color = "#bfb"
				#else:
				#	color = "#bbb"
				#svg_link.setAttribute('style','stroke:' + color)
				
				if p == r - 1:
					# links to the immediately previous race are emphasized
					g_linkline.addElement(l_link)
				else:
					# links to earlier races are drawn in a separate group
					g_weaklink.addElement(l_link)
				
				break
	
	# Group label components together
	g_racelabels.addElement(g_ranklabels)
	g_racelabels.addElement(g_namelabels)
	g_racelabels.addElement(g_timelabels)
	
	# Add group of labels for this race to group of all labels
	g_label.addElement(g_racelabels)

def Scalebars(smin, smax, xmin, xmax):
		
	c_lines = StyleBuilder(config['scaleline_style'])
	c_times = StyleBuilder(config['scale_style'])
	c_times.setFontSize(str(config['scale_font_height']) + 'px')
	
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
		if config['scaleleft']:
			# note hard coded assumption of max 7 char time() label
			# that would be fine, with a 5px margin between the end of
			# the label and the start of the scale bar, but some issue
			# with character width mis-estimation is bungling the spacing
			lx = xmin - 5 - (7 * config['scale_font_width'])
		else:
			lx = xmax + 5
		stime = text(time(s), lx, y + 6)
		g_scale_lines.addElement(sline)
		g_scale_times.addElement(stime)
	
	g_scale.addElement(g_scale_lines)
	g_scale.addElement(g_scale_times)
	return g_scale

s = svg()

if config['scalebars']:
	s.addElement(Scalebars(mins, maxs, 0, races[-1]['xr']))

s.addElement(g_weaklink)
s.addElement(g_linkline)

if config['underline'] != 0:
	s.addElement(g_underline)

s.addElement(g_label)

print s.getXML()
