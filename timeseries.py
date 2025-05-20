import csv
import pandas as pd
from sys import argv
from math import sqrt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

spacer = 20
scale = 5

threshold = 12
if len(argv) > 1:
    try:
        threshold = int(argv[1])
    except:
        threshold = 12 # how many orders at least
minlength = 2 + 2 * threshold

time = []
client = []
amount = []
colors = []
markers = []
ax = plt.subplot(1, 1, 1)
count = 0
longest = 0
with open('ordertimes.csv') as data:
    reader = csv.reader(data)
    c = 0
    for row in reader: # ID subgroup order times in seconds
        l = len(row)
        if l < minlength:
            continue
        longest = max(longest, l)
        count += 1
        row.pop(0) # skip ID
        subgroup = row.pop(0)
        color  = 'blue' if 'jan' in subgroup else 'green'
        shape = 1 if 'post' in subgroup else 2
        while len(row) > 2:
            colors.append(color) # repeat for each dot
            markers.append(shape) # repeat for each dot
            time.append(int(row.pop(0)))
            amount.append(scale * sqrt(float(row.pop(0))))
            client.append(c)
        c -= spacer


assert len(time) == len(amount) and len(client) == len(colors)

time = [ pd.to_datetime(t, unit='s') for t in time ] # seconds since epoch

import pandas as pd
import seaborn as sns

data = pd.DataFrame ( { 'horizontal' : time,
                        'vertical' : client,
                        'size' : amount,
                        'color' : colors,
                        'symbol' : markers } )


print(data.shape)
count = data.shape[0] # rows

from math import log, ceil

w = ceil(log(count, 2))
h = ceil(log(longest, 2))
print(w, h)

fig, ax = plt.subplots(figsize = (w, h))

plt.title(f'{count} clients with at least {threshold} orders', fontsize = 20)
fig = sns.scatterplot(data = data, x = 'horizontal', y = 'vertical', style = 'symbol', size = 'size', hue = 'color', ax = ax)

t = ax.get_xticks()
ax.set_xticks(t)
k = len(t)

dates = data['horizontal'].dt.strftime('%Y-%m-%d').sort_values().unique()
n = len(dates)
step = n // k

ax.set_xticklabels(labels = dates[::step][:k], rotation = 45, ha='right')
ax.get_yaxis().set_visible(False)

plt.legend([],[], frameon=False)

fig.figure.savefig(f'timeseries{threshold}.png')
