#!/usr/bin/env python
from collections import defaultdict
import itertools

import numpy

from base import utils,gob
from base.gisgraphy import GisgraphyResource
from base.models import User


def fix_user_mdist():
    gis = GisgraphyResource()
    users = User.find(User.geonames_place.exists(), timeout=False)
    for user in users:
        if not user.geonames_place.mdist:
            user.geonames_place.mdist = gis.mdist(user.geonames_place)
            user.save()


@gob.mapper(all_items=True)
def gnp_gps(users):
    gis = GisgraphyResource()
    for user in itertools.islice(users,2600,None):
        gnp = gis.twitter_loc(user['location']).to_d()
        yield User.mod_id(user),(gnp,user['mloc'])


@gob.mapper(all_items=True)
def mdists(gnp_gps):
    item_cutoff=2
    kind_cutoff=5
    mdist = {}

    dists = defaultdict(list)
    gnps = {}
    for gnp,mloc in gnp_gps:
        d = utils.coord_in_miles(gnp,mloc)
        id = gnp.get('fid','COORD')
        dists[id].append(d)
        gnps[id] = gnp

    codes = defaultdict(list)
    for k,gnp in gnps.iteritems():
        if len(dists[k])>item_cutoff:
            #add an entry for each feature that has a meaningful median
            mdist[str(k)] = numpy.median(dists[k])
        else:
            codes[gnp.get('code')].append(dists[k][0])
    other = []

    for k,code in codes.iteritems():
        if len(code)>kind_cutoff:
            #add an entry for each feature code that has a meaningful median
            mdist[k] = numpy.median(codes[k])
        else:
            other.extend(code)
    #add a catch-all for everything else
    mdist['other'] = numpy.median(other)
    yield mdist
