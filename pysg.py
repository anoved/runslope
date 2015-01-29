#!/usr/bin/python

import csv
import re

config = {
	'fontsize': 9,
	'linespan': 50
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

# min and max deltas between neighborhing values
mind = maxs - mins
maxd = 0
for i in range(1, len(data)-1):
	diff = abs(data[i]['SECONDS'] - data[i-1]['SECONDS'])
	if diff != 0:
		if diff < mind:
			mind = diff
		if diff > maxd:
			maxd = diff

print("Fastest time:", mins)
print("Slowest time:", maxs)

print("Min gap:", mind)
print("Max gap:", maxd)

# next, sort by RACE, then SECONDS, then NAME (basically, restore input format)
data.sort(key=lambda rec: (rec['RACE'], rec['SECONDS'], rec['NAME']))

# list unique names and times
unames = [data[0]['NAME']]
utimes = [data[0]['SECONDS']]
nraces = 1
for i in range(1, len(data)-1):
	# add new names to unique names list
	if data[i]['NAME'] not in unames:
		unames.append(data[i]['NAME'])
	# add new times to unique times list
	if data[i]['SECONDS'] not in utimes:
		utimes.append(data[i]['SECONDS'])
	# increment race count on race id change
	if data[i-1]['RACE'] != data[i]['RACE']:
		nraces += 1

# I think it might actually be more useful at this point
# to break the data into a dict of result lists, with one
# for each races. Think it might simplify graph loop.

# todo: find max char count of names, times, and rank (results per race)
#       in order to calculate label column width. Char counts should be
#       calculated on a per-race basis so each race column is best fitted

# use unique 'RACE' values as keys for sorted result lists:
# {'1': [{'NAME': 'Bob', 'SECONDS': 3423}, ...], '2': [...], ...}

# then, instead of conditional context switching blocks within
# a loop of all results, we'll have a more structured pair of loops:
# the outer loop goes through races (only a few), and the inner loop
# goes through sorted results from that race. 
#
# Simplifies #1 & #6 conditions below.
# Still have to do #2, #3, and #4 as usual
# No need for temp arrays used in #5 & #6;
#  just push calculated values into the same data obj


# graph!
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


# for output, preferably stash relevant coordinates and strings in results dict,
# but defer SVG generation for a separate pass - to keep styling and different
# output format possibilities separate from the main layout loop.
