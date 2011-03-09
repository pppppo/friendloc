#!/usr/bin/env python
import sys
import numpy
import random
import itertools

import maroon
from restkit.errors import Unauthorized

from localcrawl.models import Edges, User, Tweet
from localcrawl.twitter import TwitterResource
from localcrawl.gisgraphy import GisgraphyResource

from splitproc import SplitProcess
import utils

class GeoLookup(SplitProcess):
    def __init__(self,path,db_name,**kwargs):
        SplitProcess.__init__(self, **kwargs)
        self.path = path
        self.db_name = db_name

    def produce(self):
        users = {}
        for t in utils.read_json(self.path):
            uid = t['user']['id']
            if 'coordinates' not in t: continue
            if uid not in users:
                users[uid] = t['user']
                users[uid]['locs'] = []
            users[uid]['locs'].append(t['coordinates']['coordinates'])
        for uid,user in users.iteritems():
            spots = user['locs']
            if len(spots)<2: continue
            if user['followers_count']==0 and user['friends_count']==0: continue
            median = utils.median_2d(spots)
            dists = [utils.coord_in_miles(median,spot) for spot in spots]
            if numpy.median(dists)>50: continue
            del user['locs']
            user['mloc'] = median
            yield user

    def map(self,users):
        self.twitter = TwitterResource()
        self.gis = GisgraphyResource()
        maroon.Model.database = maroon.MongoDB(name=self.db_name)

        for user_d in users:
            self.twitter.sleep_if_needed()
            user = User(from_dict=user_d)

            try:
                tweets = self.twitter.user_timeline(user._id)
            except Unauthorized:
                yield None
                continue
            Tweet.database.bulk_save_models(tweets)

            self.save_neighbors(user)
            user.save()
            yield None

    def save_neighbors(self,user):
        edges = self.twitter.get_edges(user._id)
        edges.attempt_save()
        frds = set(edges.friends)
        fols = set(edges.followers)
        sets = dict(
            rfriends = frds&fols,
            just_friends = frds-fols,
            just_followers = fols-frds,
            )
        for k,s in sets.iteritems():
            if len(s)>33:
                sets[k] = set(random.sample(s,33))
        uids = list(itertools.chain(*sets.values()))
        users = self.twitter.user_lookup(user_ids=uids)
        for amigo in users:
            place = self.gis.twitter_loc(amigo.location)
            #ignore states and regions with more than 5 million people
            if( not place or place.feature_code=="ADM1"
                    or place.population>5000000):
                for k,s in sets.iteritems():
                    s.discard(amigo._id)
                continue
            amigo.geonames_place = place
            amigo.attempt_save()
        for k,s in sets.iteritems():
            if s:
                group = list(s)
                random.shuffle(group)
                setattr(user,k,group)
                #for each of the three types, get the edges for one of them
                edges = self.twitter.get_edges(group[0])
                edges.attempt_save()


if __name__ == '__main__':
    proc = GeoLookup(sys.argv[0])
    proc.run_single()
