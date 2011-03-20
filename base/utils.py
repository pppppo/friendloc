import itertools
import time
import os
import errno
import sys
import random
import math
import logging
from collections import defaultdict
from datetime import datetime as dt
from operator import itemgetter

import numpy

try:
    import simplejson as json
except:
    import json

from settings import settings
import twitter as twitter
from models import *
from maroon import ModelCache, CouchDB, MongoDB


def all_users():
    return User.get_all()


def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.izip_longest(*args, fillvalue=fillvalue)

def couch(name):
    return CouchDB(settings.couchdb_root+name,True)

def mongo(name):
    return MongoDB(name=name,slave_okay=True)


def in_local_box(place):
    box = settings.local_box
    return all(box[d][0]<place[d]<box[d][1] for d in ('lat','lng'))

def tri_users_dict_set(users_path):
    users = dict((int(d['id']),d) for d in _read_json(users_path))
    return users,set(users)


def read_gis_locs(path=None):
    for u in _read_json(path or "hou_tri_users"):
        yield u['lng'],u['lat']


def noisy(ray,scale):
    return ray+numpy.random.normal(0.0,scale,len(ray))

def median_2d(spots):
    return [numpy.median(x) for x in zip(*spots)]

def triangle_set(strict=True):
    Model.database = connect('houtx_user')
    users = Model.database.paged_view('_all_docs',include_docs=True,endkey="_")
    for row in users:
        user = row['doc']
        if user['prot'] or user['prob']==.5:
            continue
        if user['frdc']>2000 and user['folc']>2000:
            continue
        if strict and (user['prob']==0 or user['gnp'].get('pop',0)>1000000):
            continue
        yield user


def parse_ats(ats_path):
    ats =defaultdict(lambda: defaultdict(int))
    ated =defaultdict(lambda: defaultdict(int))
    for line in open(ats_path):
        uid,at = [int(i) for i in line.strip().split('\t')]
        ats[uid][at]+=1
        ated[at][uid]+=1
    return ats,ated

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as ex:
        if ex.errno!=errno.EEXIST:
            raise

def mainstream_edges(edges):
    return [ e for e in edges
        if 47<=e['lmfrd']+e['lmfol']<=300
        if 101<=e['lyfrd']+e['lyfol']<=954
        ]


def split_tri_counts(counts_path):
    edges = list(mainstream_edges(_read_json(counts_path)))
    third = len(edges)/3
    return (edges[:third],edges[2*third:3*third],edges[third:2*third])


def _coord_delta(p1,p2):
    """estimate the distance between two points in miles - points can be 
    (lng,lat) tuple or dict(lng=lng,lat=lat)"""
    points = [
            (p['lng'],p['lat']) if isinstance(p, dict) else p
            for p in (p1,p2)]
    lng,lat=zip(*points)
    mlat = 69.1
    mlng = mlat*math.cos(sum(lat)*math.pi/360)
    return (mlat*(lat[0]-lat[1]), mlng*(lng[0]-lng[1]))


def coord_angle(p, p1, p2):
    "find the angle between rays from p to p1 and p2, return None if p in (p1,p2)"
    vs = [_coord_delta(p,x) for x in (p1,p2)]
    mags = [numpy.linalg.norm(v) for v in vs]
    if any(m==0 for m in mags):
        return math.pi
    cos = numpy.dot(*vs)/mags[0]/mags[1]
    return math.acos(min(cos,1))*180/math.pi


def coord_in_miles(p1, p2):
    return math.hypot(*_coord_delta(p1,p2))


def read_json(path=None):
    file = open(path) if path else sys.stdin
    return (json.loads(l) for l in file)

def peek(iterable):
    it = iter(iterable)
    first = it.next()
    return first, itertools.chain([first],it)