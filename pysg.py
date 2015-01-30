#!/usr/bin/python

import csv
import re


config = {
	'vscale': 1,
	'fontsize': 9,
	'linespan': 50,
	'margin': 10
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

# first, sort by time for bounds checking
data.sort(key=lambda row: row['SECONDS'])

# min and max second value
mins = data[0]['SECONDS']
maxs = data[-1]['SECONDS']
srange = maxs - mins

# min and max deltas between neighborhing values
mind = srange
maxd = 0

# unique race ids
racekeys = []

for i in range(1, len(data)):
	if data[i]['RACE'] not in racekeys:
		racekeys.append(data[i]['RACE'])
	diff = abs(data[i]['SECONDS'] - data[i-1]['SECONDS'])
	if diff != 0:
		if diff < mind:
			mind = diff
		if diff > maxd:
			maxd = diff


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


for r in range(0, len(races)):
	
	# left and right positions of race results - could calc in earlier loop
	races[r]['xl'] = (
		config['margin']
		+ (r * config['linespan'])
		+ sum([(races[pr]['wmax_label'] * config['fontsize']) for pr in range(0, r - 1)])
	)
	races[r]['xr'] = races[r]['xl'] + (races[r]['wmax_label'] * config['fontsize'])
	
	for i in range(0, len(races[r]['results'])):
		rec = races[r]['results'][i]
		label =  races[r]['label_format'] % (rec['RANK'], rec['NAME'], rec['TIME'])
		
		# value we have to position
		v = rec['SECONDS'] - mins
		y = config['margin'] + v
		
		races[r]['results'][i]['y'] = y
		
		print (label, y)
		
		# draw label at (xl, y)
		
		p = r
		while p > 0:
			p -= 1
			matches = filter(lambda cand: cand['NAME'] == rec['NAME'], races[p]['results'])
			if len(matches) == 1:
				m = matches[0]
				print (p, m['y'])
				
				# draw link from
				# (races[p][xr], m[y]) to (races[r][xl], y)
				
				# style link according to difference between p & r
				# if p < r-1, this is a different category.
				
				break




#for i in range(0, len(data)-1):
#	d = data[i]
	
	# 1 check for new race id & start new column & svg group for labels
	
	# 2 duplicate/close call adjustments (todo; as yet ignored)
	
	# 3 calculate vertical position based on seconds value (& any adjustments from above)
	
	# 4 format label (for now as a single string in fixed-width font)
	
	# 5 push result (& calculated positions) into temp array for this race
	
	# 6. at end of race set (inc. end of all results), loop through this race's
	# result array and look for any name matches in previous race. If found,
	# connect with a slopegraph line.
	# todo: if not found, step back through *earlier* races and connect with
	#       a muted background slopegraph line. Requires full results by race
	#       rather than flat result list and temp race arrays.

