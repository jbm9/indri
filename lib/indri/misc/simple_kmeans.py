#!/usr/bin/env python

import random
import numpy as np
        
def two_means(x, iterations):
    """This is a quick-and-dirty implementation of k-means for the special case of k=2 in 1D Euclidean space.  It's good enough to figure out where squelch belongs efficiently."""

    if not x:
        return None
    
    c0 = random.choice(x)
    c1 = random.choice(x)

    midpt = (c0+c1)/2

    base_std = np.std(x)
    
    for _ in range(iterations):
        cluster0 = [ pt for pt in x if pt <= midpt ]
        cluster1 = [ pt for pt in x if pt >  midpt ]

        c0 = np.mean(cluster0)
        c1 = np.mean(cluster1)
        midpt = (c0+c1)/2

    std0 = np.std(cluster0)
    std1 = np.std(cluster1)
    std_model = std0+std1

    #print "midpt=%f, std=%f, base=%f std0=%f std1=%f" % (midpt, std_model, base_std, std0, std1)

    if std_model != std_model: # NaN != NaN, cover that case
        return None

    if  std_model >= 0.8*base_std: # simple heuristic
        return None
    
    return midpt
