import csv
import pandas as pd
from math import floor, ceil, sqrt
import matplotlib.pyplot as plt
from itertools import compress
from collections import defaultdict
from sksurv.nonparametric import kaplan_meier_estimator

howmany = 6

orderhist = defaultdict(int)
lengths = []
cohort = []

with open('ordertotals.csv') as data:
    reader = csv.reader(data)
    for row in reader:
        # ID cohort orders
        cohort.append(row[1])
        count = len(row) - 2
        orderhist[count] += 1
        lengths.append(count)

values = orderhist.values()
low = min(values) + 1
high = max(values) - 1

r = floor(sqrt(howmany))
c = ceil(howmany / r)

assert howmany <= r * c

fig, ax = plt.subplots(nrows = r, ncols = c, figsize=(6*c, 4*r), constrained_layout = True)
plt.xlabel('order count')

# https://scikit-survival.readthedocs.io/en/stable/user_guide/00-introduction.html

cohorts = list(set(cohort)) # should be four

i = 0
j = 0
l = 2
while l <= 2**howmany:
    data = pd.DataFrame({'status': [ x > l for x in lengths ],
                         'count': lengths, 'cohort': cohort})
    for c in cohorts:
        m = data['cohort'] == c
        time_treatment, survival_prob_treatment, conf_int = kaplan_meier_estimator(
            data['status'][m],
            data['count'][m],
            conf_type="log-log",
        )
        ax[j, i].step(time_treatment, survival_prob_treatment, where="post", label=f"{c} cohort")
        ax[j, i].fill_between(time_treatment, conf_int[0], conf_int[1], alpha=0.25, step="post")
    ax[j, i].set_ylabel(f'at least {l} orders')
    ax[j, i].legend()
    j += 1
    if j == r:
        i += 1
        j = 0
    l *= 2

    
fig.savefig(f'survival.png')
    

