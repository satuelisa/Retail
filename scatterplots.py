import csv
inputs = [ 'brand', 'category', 'product' ]
suffix = 'variety.csv'

counts = dict()
clients = []

for prefix in inputs:
    counts[prefix] = dict()
    with open(prefix + suffix) as data:
        reader = csv.reader(data)
        for row in reader: # ID subgroup order times in seconds
            client = row.pop(0)
            subgroup = row.pop(0)
            label = client + ';' + subgroup
            assert label not in counts[prefix]
            clients.append(label)
            counts[prefix][label] = ','.join(row)

cohorts = [ 'post-jan', 'pre-jan', 'post-feb', 'pre-feb' ]
            
bra = dict()
cat = dict()
pro = dict()
vol = dict()
cli = dict()
for c in cohorts:
    bra[c] = []
    cat[c] = []
    pro[c] = []
    vol[c] = []
    cli[c] = []

threshold = 10 # how many orders by minimum
from math import log

for label in clients:
    pp = label.split(';')
    g = pp[-1]
    c = pp[0]
    bd = [ int(v) for v in counts['brand'][label].split(',') ]
    cd = [ int(v) for v in counts['category'][label].split(',') ]
    pd = [ int(v) for v in counts['product'][label].split(',') ]
    k = len(bd)
    if k < threshold:
        continue # too few purchases, skip
    assert k == len(cd) and k == len(pd)
    for i in range(k):
        bra[g].append(bd[i])
        cat[g].append(cd[i])
        pro[g].append(pd[i])
        vol[g].append(log(k + 1, 10))
        cli[g].append(c) # categorical (client ID)

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
plt.rcParams["figure.figsize"] = (16, 9)

for c in cohorts:
    data = pd.DataFrame ( { 'brands' : bra[c],
                            'categories' : cat[c],
                            'products' : pro[c],
                            'counts' : vol[c],
                            'clients' : cli[c] } )

    sns.scatterplot(data = data, x = 'brands', y = 'products', hue = 'clients', size = 'counts', legend = False, alpha = 0.3)
    plt.savefig(f'scatter_b2p_{c}_t{threshold}.png')
    plt.clf()
    
    sns.scatterplot(data = data, x = 'categories', y = 'products', hue = 'clients', size = 'counts', legend = False, alpha = 0.3)
    plt.savefig(f'scatter_c2p_{c}_t{threshold}.png')
    plt.clf()    
    
    sns.scatterplot(data = data, x = 'brands', y = 'categories', hue = 'clients', size = 'counts', legend = False, alpha = 0.3)
    plt.savefig(f'scatter_b2c_{c}_t{threshold}.png')
    plt.clf()    
    
