import networkx as nx # library for graphs
from csv import reader # read in the data
from time import strptime, mktime # understanding dates/times
from collections import defaultdict # key-value pairs

# TODO: analyze by weekday / hour of day / day of month

import re # pattern matching
skip = '[^a-zA-Z ]+'

def clean(t):
    return re.sub(skip, '', t).lower().strip().lstrip()

# category inference
threshold = 0.5 # at least half a match to qualify

def similarity(w1, w2):
    return len(w1 & w2) / len(w1 | w2)

timeformat = '%Y-%m-%d %H:%M:%S'

G = nx.Graph()

cohorts = [ 'jan', 'feb' ]

# jan has an 'l1' column that feb does not have
offset = { 'jan' : -1, 'feb' : 0 } 

devices = set()
cities = set()
expected = { 'Mobile_site',
             'Tablet',
             'Desktop',
             'Android_app',
             'iOS_App' }

# category inference preparation
category = {}
undefined = set()
descr = {}

# brand inference preparation
prbrand = {}

cutoff = { 'jan': strptime('01012016', "%d%m%Y"),
            'feb': strptime('01022016', "%d%m%Y") }

subgroup = dict()


for cf in cohorts:
    o = offset[cf]
    with open(cf + '.csv') as source:
        header = source.readline()
        subtotal = []
        quantity = []
        maxprice = []
        sellingprice = []
        for fields in reader(source, skipinitialspace = True):
            oid = fields[0]
            sku = fields[1]
            prname = fields[2]
            try:
                t = strptime(fields[7], timeformat)
            except:
                # in case the date format is inconsistent
                print('Time error:', fields) 
                quit()
            cid = cf + fields[8].replace('Customer', '').lstrip().strip()

            # group into four subgroups: with and without prior orders per cohort

            if cid not in subgroup:
                subgroup[cid] = 'post-' + cf
            if t < cutoff[cf]: # purchase happens prior to cohort start
                subgroup[cid] = 'pre-' + cf
            
            brand = fields[9].strip().lstrip()
            city = fields[-5 + o]
            if city not in cities:
                G.add_node(city, kind = 'city')
                cities.add(city)

            device = fields[-3 + o]
            if device not in devices:
                devices.add(device)
                G.add_node(device, kind = 'device')
                if device not in expected:
                    print(cf, fields)
                    quit()                

            pid = clean(sku + prname)
            if len(brand) > 0 and pid in prbrand:
                storedbrand = prbrand[pid]
                if storedbrand != brand:
                    print(pid, 'had brand', storedbrand, 'but now has', brand)
                brand = storedbrand
            else:
                if len(brand) > 0:
                    prbrand[pid] = brand
                
            descr[pid] = clean(prname + ' ' + brand) # used for category inference
            cat = 'undefined'
            if cf == 'jan':
                cat = fields[-3]
                category[pid] = cat
            else: # feb
                if pid not in category:
                    undefined.add(pid)
                else:
                    cat = category[pid]
            try:
                subtotal.append(float(fields[6]))
            except:
                subtotal.append(0) # for blank subtotals
            quantity.append(int(fields[3]))
            try:
                sellingprice.append(float(fields[4]))
            except:
                sellingprice.append(0) # for blank prices
            mp = fields[5].strip()
            if len(mp) == 0:
                mp = sellingprice[-1] # use the selling price instead when max price is blank
            else:
                mp = float(mp) # not blank -> parse it
            maxprice.append(mp) # note that the selling price sometimes exceeds this for mystery reasons
            ordertotal = sum(subtotal)
            producttotal = sum([ q * sp for (q, sp) in zip(quantity, sellingprice) ])
            maxtotal = sum([ q * sp for (q, sp) in zip(quantity, maxprice) ])
            difference = maxtotal - producttotal
            percentage = 100 * (difference / maxtotal if maxtotal > 0 else 1) # free samples -> full discount            
            if fields[16] == 'YES': 
                # reset the collector lists for the next order
                subtotal = []
                quantity = []
                maxprice = []
                sellingprice = []

            # the one with the 'YES' in col. 16 will overwrite the attributes of the former versions
            G.add_node(oid, kind = 'order', time = t,
                       total = ordertotal, discount = percentage, fees = ordertotal - producttotal)
            G.add_node(pid, kind = 'product', special = (fields[15] == 'YES'))
            G.add_edge(oid, pid) # order to product
            G.add_edge(oid, cid) # order to customer
            G.add_edge(cid, city) # customer to city
            G.add_edge(cid, device) # customer to device


from collections import Counter
print(Counter(subgroup.values()))
            
for cid in subgroup:
    G.add_node(cid, kind = 'customer', cohort = subgroup[cid])
            
#  link each product to brand            
for br in prbrand.values():
    G.add_node(br, kind = 'brand')
for pid in prbrand:
    G.add_edge(prbrand[pid], pid) 
            
cats = category.values()            
print(len(set(cats)), 'known categories')
print(len(cats), 'products with defined categories')
u = len(undefined)
print(u, 'products with no defined category')

import os
from sys import argv

inferred = dict()
if 'infer' in argv or not os.path.exists('./inferred.csv'):
    score = dict()
    words = dict()
    for pid in descr: # create bags of words
        words[pid] = set(descr[pid].split())
    for p1 in undefined: # find matches
        t1 = words[p1]
        scores = [ (p2, similarity(t1, words[p2])) for p2 in category ]
        best = max(scores, key = lambda s : s[1])
        record = best[1]
        if record > threshold: # if the highest score exceed the threshold
            if p1 not in score or record > score[p1]: # new or better
                # then that product's category will be used                
                inferred[p1] = category[best[0]] 
                score[p1] = record # remember that score
    if len(inferred) > 0:
        with open('inferred.csv', 'w') as target: # create a mapping (overwrite if one exists)
            for pid in inferred:
                print(f'{pid},{score[pid]},"{inferred[pid]}","{descr[pid]}"',
                      file = target)    
else:
    score = dict()
    with open('inferred.csv') as source: # use an existing mapping
        for fields in reader(source, skipinitialspace = True):
            pid = fields[0]
            inferred[pid] = fields[2]
            score[pid] = float(fields[1])
    for pid in undefined:
        if pid in inferred:
            G.add_edge(cat, pid, score = score[pid]) # add the inferred edges with the weights being the scores

            
i = len(inferred)
print(i, 'products with inferred categories')
print(u - i, 'products that could not be assigned an inferred category')

#  link each product to category
for cat in category.values():
    G.add_node(cat, kind = 'category')
for pid in category:
    G.add_edge(category[pid], pid) 

ordertimes = open('ordertimes.csv', 'w')    
ordertotals = open('ordertotals.csv', 'w')
orderdiscount = open('orderdiscounts.csv', 'w')
productvariety = open('productvariety.csv', 'w')
brandvariety = open('brandvariety.csv', 'w')
categoryvariety = open('categoryvariety.csv', 'w')
varietyseeking = open('varietyseeking.csv', 'w')

with open('interpurchase.csv', 'w') as target:    
    for node in G.nodes:
        nd = G.nodes[node]
        if nd['kind'] == 'customer':
            times = list()
            totals = list()
            discounts = list()
            productvarieties = list()
            brandvarieties = list()
            categoryvarieties = list()
            for n in G.neighbors(node):
                nnd = G.nodes[n]
                if nnd['kind'] == 'order':
                    times.append(nnd['time'])
                    totals.append(nnd['total'])
                    discounts.append(nnd['discount'])
                    
                    # count how many different products/brands were in the order (not counting duplicates)
                    ons = G.neighbors(n) # neighbors of the order (includes products)
                    cproducts = set()
                    cbrands = set()
                    cats = set()
                    for on in ons:
                        if G.nodes[on]['kind'] == 'product':
                            cproducts.add(on)
                            cats.add(category.get(on, inferred.get(on, 'unknown')))
                            for onn in G.neighbors(on):
                                if G.nodes[onn]['kind'] == 'brand':
                                    cbrands.add(onn)
                    productvarieties.append(len(cproducts))
                    brandvarieties.append(len(cbrands))
                    categoryvarieties.append(len(cats))

            if len(totals) > 0:
                up = len(set(cproducts))
                ub = len(set(cbrands))
                if ub > up:
                    print('Customer', node, 'has more brands than products:', ub, 'vs', up)
                prop = ub / up
                vsb = f'{node},{subgroup[node]},{prop:.3f}'
                print(vsb, file = varietyseeking)

                sg = subgroup[node]
                ot = ','.join([ f'{mktime(time):.0f},{total:.3f}' for (time, total) in zip(times, totals) ])
                print(f'{node},{sg},{ot}', file = ordertimes)
                
                t = ','.join([ f'{total:.2f}' for total in totals ])
                print(f'{node},{sg},{t}', file = ordertotals)

                d = ','.join([ f'{discount:.2f}' for discount in discounts ])                    
                print(f'{node},{sg},{d}', file = orderdiscount)                

                pv = ','.join([ str(var) for var in productvarieties ])                    
                print(f'{node},{sg},{pv}', file = productvariety)

                bv = ','.join([ str(var) for var in brandvarieties ])                    
                print(f'{node},{sg},{bv}', file = brandvariety)

                cv = ','.join([ str(var) for var in categoryvarieties ])                    
                print(f'{node},{sg},{cv}', file = categoryvariety)

            times.sort() # just in case it was not ascending (it SHOULD be)                                    
            previous = times.pop(0)
            intervals = []
            while len(times) > 0:
                following = times.pop(0)
                seconds = mktime(following) - mktime(previous) # time interval in seconds
                intervals.append(seconds / 60 / 60 / 24) # seconds to minutes to hours to days
                previous = following
            if len(intervals) > 0:
                l = ','.join([ f'{i:.2f}' for i in intervals ])
                print(f'{node},{sg},{l}', file = target)
                
ordertimes.close()
ordertotals.close()
orderdiscount.close()
productvariety.close()
brandvariety.close()
varietyseeking.close()

print(G)

# visualization

if 'vis' not in argv:
    quit()
    
from random import random
sample = 0.005

if 'vis' in argv: # subsample orders / products / customers
    ditch = set()
    total = 0
    for n in G.nodes:
        nd = G.nodes[n]
        if nd['kind'] == 'customer':
            total += 1
            if random() > sample:
                ditch.add(n)
    print(f'Customers pruned down for visualization, removing {len(ditch)} / {total}')
    G.remove_nodes_from(ditch)
    ditch2 = set()
    for n in G.nodes(): # prune the orders of the pruned customers
        if G.nodes[n]['kind'] == 'order':
            keep = False
            for p in G.neighbors(n):
                if G.nodes[p]['kind'] == 'customer' and p not in ditch:
                    keep = True
                    break
            if not keep: # no reason to keep this in the sample
                ditch2.add(n)
    G.remove_nodes_from(ditch2)
    ditch3 = set()
    for n in G.nodes(): # prune the products of the pruned orders
        if G.nodes[n]['kind'] == 'product':
            keep = False
            for p in G.neighbors(n):
                if G.nodes[p]['kind'] == 'order' and p not in ditch2:
                    keep = True
                    break
            if not keep: # no reason to keep this in the sample
                ditch3.add(n)
    G.remove_nodes_from(ditch3)
    ditch4 = set()
    for n in G.nodes(): # prune the brands of the pruned products
        if G.nodes[n]['kind'] == 'brand':
            keep = False
            for p in G.neighbors(n):
                if G.nodes[p]['kind'] == 'product' and p not in ditch3:
                    keep = True
                    break
            if not keep: # no reason to keep this in the sample
                ditch4.add(n)
    G.remove_nodes_from(ditch4)

    print(f'Graph pruned down for visualization', len(ditch2), len(ditch3), len(ditch4))
    print(G)
    
import matplotlib.pyplot as plt
from itertools import count
from math import log, ceil
from collections import Counter

attr = nx.get_node_attributes(G, 'kind').values()
groups = set(attr)
counts = Counter(attr)
h = max(counts.values())
    
mapping = dict(zip(sorted(groups), count()))
nodes = G.nodes()
palette = [ mapping[G.nodes[n]['kind']] for n in nodes ]
edges = G.edges()
scorepalette = [ (0, 0, 0, G[u][v].get('score', 1)) for u, v in edges ]
deg = dict(G.degree)
sizes = [ 10 * v for v in deg.values() ] 

b = 50 * max(sizes) + 1

x = { 'category': 0,
      'brand' : b,
      'product': 2 * b,
      'order': 3 * b,
      'customer': 4 * b,
      'city': 5 * b,
      'device': 6 * b
     }

y = { 'category': 0,
      'brand' : 0,
      'product': 0,
      'order': 0,
      'customer': 0,
      'city': 0,
      'device': 0
      }

i = dict()
for k in x:
    i[k] = b * ceil(h / (counts[k] + 1))

pos = dict()
for node in G.nodes:
    n = G.nodes[node]
    xc = x[n['kind']]
    yc = y[n['kind']]
    y[n['kind']] += i[n['kind']]
    pos[node] = (xc, yc)

fig = plt.figure(1, figsize = (50, 150), dpi=150)
ec = nx.draw_networkx_edges(G, pos,
                            nodelist = nodes,
                            edgelist = edges,
                            edge_color = scorepalette)
nc = nx.draw_networkx_nodes(G, pos,
                            nodelist = nodes,
                            node_color = palette,
                            node_size = sizes,
                            cmap = plt.cm.jet)
plt.axis('off')
plt.savefig('commerce.png', bbox_inches = 'tight')
