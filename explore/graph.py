OUTPUT_TYPE = None # 'png', 'pdf', or None
OUTPUT_TYPE = 'png'#, 'pdf', or None

import random
import logging
import math
import bisect
import contextlib
from collections import defaultdict, namedtuple
from datetime import datetime as dt
from datetime import timedelta

import networkx as nx
import matplotlib

# this needs to happen before pyplot is imported - it cannot be changed
if OUTPUT_TYPE:
    matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy

from settings import settings
from explore import peek
#from base.models import *
from base.utils import dist_bins, coord_in_miles
from base import gob


@contextlib.contextmanager
def axes(path='', figsize=(12,8), legend_loc=4,
         xlabel=None, ylabel=None, xlim=None, ylim=None, ):
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111)
    yield ax
    if xlim is not None:
        try:
            ax.set_xlim(*xlim)
        except TypeError:
            ax.set_xlim(0,xlim)
    if ylim is not None:
        try:
            ax.set_ylim(*ylim)
        except TypeError:
            ax.set_ylim(0,ylim)

    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if legend_loc:
        ax.legend(loc=legend_loc)
    if OUTPUT_TYPE:
        fig.savefig('../www/'+path+'.'+OUTPUT_TYPE,bbox_inches='tight')


def linhist(ax, row, bins, dist_scale=False, window=None, normed=False,
            marker='-', **hargs):
    "works like ax.hist, but without jagged edges"
    hist,b = numpy.histogram(row,bins)
    step_size = b[2]/b[1]
    hist = hist*(1.0*step_size/(step_size-1))
    if window is not None:
        hist = numpy.convolve(hist,window,mode='same')/sum(window)
    if normed:
        hist = hist * (1.0/len(row))
    if dist_scale:
        hist = hist/b[1:]
        ax.set_yscale('log')
    ax.set_xscale('log')
    ax.plot((b[:-1]+b[1:])/2, hist, marker, **hargs)

def ugly_graph_hist(data,path,kind="sum",figsize=(12,8),legend_loc=None,normed=False,
        sample=None, histtype='step', marker='-', logline_fn=None,
        label_len=False, auto_ls=False, dist_scale=False, ax=None,
        window=None, ordered_label=False, **kwargs):
    # DEPRECATED - TOO COMPLEX!
    if ax:
        fig = None
    else:
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111)
    
    if not isinstance(data,dict):
        data = {"":data}

    hargs = {}
    if kind == 'power':
        ax.set_xscale('log')
        ax.set_yscale('log')
        hargs['log']=True
    elif kind == 'linear':
        pass
    elif kind == 'logline':
        ax.set_xscale('log')
        if dist_scale:
            ax.set_yscale('log')
            legend_loc = 3
        elif legend_loc is None:
            legend_loc = 9
    elif kind == 'cumulog':
        ax.set_xscale('log')
        hargs['cumulative']=True
        if legend_loc is None:
            legend_loc = 4
    else:
        hargs['cumulative']=True
        if legend_loc is None:
            legend_loc = 4

    for known in ['bins']:
        if known in kwargs:
            hargs[known] = kwargs[known]

    for index,key in enumerate(sorted(data.iterkeys())):
        if isinstance(key,basestring):
            hargs['label'] = key
        else:
            for k,v in zip(['label','color','linestyle','linewidth'],key):
                if v is not None:
                    hargs[k] = v
        if ordered_label:
            hargs['label'] = hargs['label'][2:]

        if auto_ls:
            hargs['linestyle'] = ('solid','dashed','dashdot','dotted')[index/7]

        row = data[key]
        if sample:
            row = random.sample(row,sample)
        if normed:
            weight = 1.0/len(row)
            hargs['weights'] = [weight]*len(row)
        if label_len:
            hargs['label'] = "%s (%d)"%(hargs['label'],len(row))

        if kind=="logline":
            for k in ['weights','log','bins']:
                if k in hargs:
                    del hargs[k]
            hist,b = numpy.histogram(row,kwargs['bins'])
            step_size = b[2]/b[1]
            hist = hist*(1.0*step_size/(step_size-1))
            if window is not None:
                hist = numpy.convolve(hist,window,mode='same')/sum(window)
            if normed:
                hist = hist*weight
            if dist_scale:
                hist = hist/b[1:]
            if logline_fn:
                logline_fn(ax, row, b, hist)
            ax.plot((b[:-1]+b[1:])/2, hist, marker, **hargs)
        else:
            ax.hist(row, histtype=histtype, **hargs)
    if normed and kind!='logline':
        ax.set_ylim(0,1)
    elif 'ylim' in kwargs:
        try:
            ax.set_ylim(*kwargs['ylim'])
        except TypeError:
            ax.set_ylim(0,kwargs['ylim'])
    if 'xlim' in kwargs:
        try:
            ax.set_xlim(*kwargs['xlim'])
        except TypeError:
            ax.set_xlim(0,kwargs['xlim'])
    if len(data)>1:
        ax.legend(loc=legend_loc)
    ax.set_xlabel(kwargs.get('xlabel'))
    ax.set_ylabel(kwargs.get('ylabel'))
    if fig is not None:
        fig.savefig('../www/'+path,bbox_inches='tight')


def graph_results(path="results"):
    linestyle = defaultdict(lambda: 'solid')
    linestyle['Median'] = 'dotted'
    linestyle['Omniscient *'] = 'dotted'
    linestyle['Mode'] = 'dotted'
    data = defaultdict(list)
    for block in read_json(path):
        for k,v in block.iteritems():
            k = k.replace('lul','contacts')
            data[(k,None,linestyle[k])].extend(v)
    for k,v in data.iteritems():
        print k[0], 1.0*sum(1 for d in v if d<25)/len(v)
    ugly_graph_hist(data,
            "top_results.pdf",
            bins=dist_bins(120),
            xlim=(1,15000),
            kind="cumulog",
            normed=True,
            ordered_label=True,
            xlabel = "error in prediction in miles",
            ylabel = "fraction of users",
            )


def diff_mode_fl():
    mode=[]
    fl=[]
    for block in read_json('results'):
        mode.extend(block['Mode'])
        fl.extend(block['FriendlyLocation'])
    mode = numpy.array(mode)+1
    fl = numpy.array(fl)+1

    fig = plt.figure(figsize=(12,12))
    ax = fig.add_subplot(111)
    ax.loglog(mode, fl, '+',
            color='k',
            alpha='.05',
            markersize=5,
            )
    ax.set_xlim(1,15000)
    ax.set_ylim(1,15000)
    ax.set_xlabel("mode")
    ax.set_ylabel("fl")
    fig.savefig('../www/mode_fl.png')

 
def filter_rtt(path=None):
    format = "%a %b %d %H:%M:%S +0000 %Y"
    for tweet in read_json(path):
        if tweet.get('in_reply_to_status_id'):
            #ca = time.mktime(dt.strptime(t[2],format).timetuple())
            print "%d\t%d\t%s"%(
                tweet['id'],
                tweet['uid'],
                tweet['in_reply_to_status_id'],
                tweet['created_at']
                )


def graph_rtt(path=None):
    #FIXME: This is for crowdy, not FriendlyLocation!
    reply = namedtuple("reply",['id','uid','rtt','ca'])
    file = open(path) if path else sys.stdin
    tweets = [reply([int(f) for f in t])
        for t in (line.strip().split('\t') for line in file)]
    time_id = {}
    for t in tweets:
        time_id[t.ca] = max(t.id, time_id.get(t.ca,0))
    cas = sorted(time_id.iterkeys())
    ids = [time_id[ca] for ca in cas]
    deltas = [
        t.ca - cas[bisect.bisect_left(ids,t.rtt)]
        for t in tweets[len(tweets)/2:]
        if t.rtt>ids[0]]
    ugly_graph_hist(deltas,
            "reply_time_sum",
            bins=xrange(0,3600*12,60),
            xlabel="seconds between tweet and reply",
            ylabel="count of tweets in a minute",
        )


def _plot_dist_model(ax, row, *ignored):
    inner = 1.0*sum(1 for r in row if r<1)/len(row)
    ax.plot([.001,1000],[inner,inner],'-',color='k',alpha=.2)

    bins = 10**numpy.linspace(0,1,11)
    hist,bins = numpy.histogram(row,bins)
    step_size = bins[2]/bins[1]
    centers = numpy.sqrt(bins[1:]*bins[:-1])
    #scale for distance and the width of the bucket
    line = hist/bins[1:] * (step_size/(step_size-1)/len(row))
    a,b = numpy.polyfit(numpy.log(centers),numpy.log(line),1)
    
    #data = [(10**b)*(x**a) for x in bins]
    X = 10**numpy.linspace(0,2,21)
    Y = (math.e**b) * (X**a)
    ax.plot(X, Y, '-', color='k',alpha=.2)


class VectFit(object):
    def __init__(self,env):
        self.env = env

    @gob.mapper(all_items=True)
    def graph_vect_fit(self, vect_fit, in_paths):
        if in_paths[0][-1] != '0':
            return
        ratios = (ratio for cutoff,ratio in self.env.load('vect_ratios.0'))
        fits = (fit for cutoff,fit in vect_fit)

        bins = dist_bins(120)
        miles = numpy.sqrt([bins[x-1]*bins[x] for x in xrange(2,482)])

        with axes('graph_vect_fit') as ax:
            ax.set_xlim(1,15000)
            ax.set_xscale('log')
            ax.set_yscale('log')
            ax.set_xlabel('distance in miles')
            ax.set_ylabel('probablility of being a contact')

            colors = iter('rgbc')
            for index,(ratio,fit) in enumerate(zip(ratios, fits)):
                if index%3!=0:
                    continue

                color = next(colors)
                ax.plot(miles, ratio, '-', color=color)
                ax.plot(miles, peek.contact_curve(miles,*fit), '-',
                        linestyle='dashed', color=color)


@gob.mapper(all_items=True)
def gr_preds(preds, in_paths):
    data = dict(preds)
    clump = in_paths[0][-1]
    for key,vals in data.iteritems():
        print key,sum(1 for v in vals if v<25)

    ugly_graph_hist(data,
            "gr_preds%s.png"%clump,
            xlim= (1,15000),
            normed=True,
            label_len=True,
            kind="cumulog",
            ylabel = "fraction of users",
            xlabel = "error in prediction (miles)",
            bins = dist_bins(120),
            )


CONTACT_GROUPS = dict(
    jfol = dict(label='just followers',color='g'),
    jfrd = dict(label='just friends',color='b'),
    rfrd = dict(label='recip friends',color='r'),
    jat = dict(label='just mentioned',color='c'),
)


@gob.mapper(all_items=True)
def graph_edge_types_cuml(edge_dists):
    data = defaultdict(list)

    for key,dists in edge_dists:
        if key[0]=='rand':
            continue
        conf = CONTACT_GROUPS[key[0]]
        data[(conf['label'],conf['color'],'solid')].extend(dists)

    for k,v in data.iteritems():
        print k,sum(1.0 for x in v if x<25)/len(v)

    ugly_graph_hist(data,
            "edge_types_cuml.pdf",
            xlim= (1,15000),
            normed=True,
            label_len=True,
            kind="cumulog",
            ylabel = "fraction of users",
            xlabel = "distance to contact in miles",
            bins = dist_bins(120),
            )

@gob.mapper(all_items=True)
def graph_edge_types_prot(edge_dists):
    data = defaultdict(list)

    for key,dists in edge_dists:
        if key[0]=='rand':
            continue
        conf = CONTACT_GROUPS[key[0]]
        fill = 'solid' if key[-1] else 'dotted'
        data[(conf['label'],conf['color'],fill)].extend(dists)

    ugly_graph_hist(data,
            "edge_types_prot.pdf",
            xlim = (1,15000),
            normed=True,
            label_len=True,
            kind="cumulog",
            ylabel = "fraction of users",
            xlabel = "distance to contact in miles",
            bins = dist_bins(80),
            )

@gob.mapper(all_items=True)
def graph_edge_types_norm(edge_dists):
    data = defaultdict(list)
    for key,dists in edge_dists:
        if key[0]=='rand':
            continue
        conf = CONTACT_GROUPS[key[0]]
        data[(conf['label'],conf['color'],'solid')].extend(dists)
    for key,dists in data.iteritems():
        data[key] = [d+1 for d in dists]

    ugly_graph_hist(data,
            "edge_types_norm.pdf",
            xlim = (1,15000),
            normed=True,
            label_len=True,
            kind="logline",
            ylabel = "fraction of users",
            xlabel = "distance to contact in miles",
            bins = dist_bins(40),
            ylim = .6,
            )


def shuffled_dists(edges,kind="rfrd"):
    good = [e for e in edges if kind in e and e[kind]['mdist']<1000]
    dists = (
        coord_in_miles(me['mloc'],you[kind])
        for me,you in zip(good, random.sample(good, len(good)))
        )
    return numpy.fromiter(dists, float, len(good))


def gen_rand_dists():
    users = list(User.find_connected())
    collection = User.database.User
    dests = dict(
        (user['_id'],user['gnp'])
        for user in collection.find({'gnp':{'$exists':1}},fields=['gnp']))
    keys = ('just_followers','just_friends','rfriends') 
    for user in users:
        for key in keys:
            amigo_id = getattr(user,key)[0]
            if dests[amigo_id]['mdist']<1000:
                other = random.choice(users)
                print coord_in_miles(other.median_loc,dests[amigo_id])

def find_urls():
    #for New Zealand project and Krishna
    start = dt(2011,2,22,0)
    tweets = Tweet.find(Tweet.created_at.range(start,start+timedelta(hours=2)))
    for t in tweets:
        print t.to_d(long_names=True,dateformat="%a %b %d %H:%M:%S +0000 %Y")


def tweets_over_time():
    #for the New Zealand project
    tweets = Tweet.find(
            (Tweet.text//r'twitpic\.com/\w+')&
            Tweet.created_at.range(dt(2011,2,19),dt(2011,3,1)),
            fields=['ca'])
    days = [tweet.created_at.hour/24.0+tweet.created_at.day for tweet in tweets]
    ugly_graph_hist(
            days,
            "twitpic_hr_lim",
            kind="linear",
            xlabel = "March 2011, UTC",
            ylabel = "tweets with twitpic per hour",
            bins=numpy.arange(19,29,1/24.0),
            xlim=(21,29),
            )


def all_ratio_subplot(ax, edges, key, ated):
    CUTOFF=settings.local_max_dist
    BUCKETS=settings.fol_count_buckets
    for kind,color in [['folc','r'],['frdc','b']]:
        dists = defaultdict(list)
        for edge in edges:
            amigo = edge.get(key)
            if amigo and amigo['ated']==ated and amigo['mdist']<1000:
                dist = coord_in_miles(edge['mloc'],amigo)
                bits = min(BUCKETS-1, int(math.log((amigo[kind] or 1),4)))
                dists[bits].append(dist)
        users = 0
        for i in xrange(BUCKETS):
            row = dists[i]
            if not row: continue
            height = 1.0*sum(1 for d in row if d<CUTOFF)/len(row)
            ax.bar(users,height,len(row),color=color,edgecolor=color,alpha=.3)
            users+=len(row)
    ax.set_xlim(0,users)
    ax.set_ylim(0,.8)


def gr_ratio_all():
    edges = list(read_json('edges_json'))
    print "read edges"
    
    conv_labels = [
            "Public I talk to",
            "Public I ignore",
            "Protected I talk to",
            "Protected I ignore"]
    edge_labels = ('just followers','recip friends','just friends','just mentioned')
    edge_types = ('jfol','rfrd','jfrd','jat')

    fig = plt.figure(figsize=(24,12))
    for row, edge_type, edge_label in zip(range(4), edge_types, edge_labels):
        for col,conv_label in enumerate(conv_labels):
            ated = (col%2==0)
            if not ated and row==3:
                continue # this case is a contradiction
            ax = fig.add_subplot(4,4,1+col+row*4)
            edge_key = 'p'+edge_type if col>=2 else edge_type

            all_ratio_subplot(ax, edges, edge_key, ated)
            if col==0:
                ax.set_ylabel(edge_label)
            if row==3:
                ax.set_xlabel('count of users')
            elif row==0:
                ax.set_title('%s users I %s'%(
                    'protected' if col>=2 else 'public', 
                    'talk to' if ated else 'ignore',
                    ))
            ax.tick_params(labelsize="small")
            print 'graphed %d,%d'%(row,col)
    ax = fig.add_subplot(4,4,16,frame_on=False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(
        [Patch(color=c,alpha=.3) for c in "rb"],
        ("follower count","friend count"),
        4)
    fig.savefig('../www/local_all.pdf',bbox_inches='tight')


@gob.mapper(all_items=True)
def graph_edge_count(rfr_dists):
    frd_data = defaultdict(list)
    fol_data = defaultdict(list)
    labels = ["",'1-9','10-99','100-999','1000-9999','10000+']
    key_labels = dict(frdc='Friends',folc='Followers')

    for amigo in rfr_dists:
        for color,key,data in (('r','folc',fol_data),('b','frdc',frd_data)):
            bin = min(5,len(str(int(amigo[key]))))
            label = '%s %s'%(labels[bin],key_labels[key])
            # 1.6**(bin-1) is the line width calculation
            data[label,color,'solid',1.6**(bin-2)].append(amigo['dist'])

    fig = plt.figure(figsize=(18,6))
    for spot,data in enumerate((fol_data,frd_data)):
        ax = fig.add_subplot(1,2,1+spot)
        ugly_graph_hist(data,
            'ignored',
            ax=ax,
            bins=dist_bins(120),
            xlim=(1,15000),
            label_len=True,
            kind="cumulog",
            normed=True,
            xlabel = "distance between edges in miles",
            ylabel = "fraction of users",
            )
    fig.savefig("../www/edge_counts.pdf",bbox_inches='tight')


@gob.mapper(all_items=True)
def graph_local_groups(edges):
    data=defaultdict(list)
    for edge in edges:
        for key,conf in CONTACT_GROUPS.iteritems():
            if key not in edge:
                continue
            amigo = edge.get(key)
            if amigo['lofol'] is None or amigo['lofol']<.5:
                continue
            dist = coord_in_miles(edge['mloc'],amigo)
            data[(conf['label'],conf['color'],'solid')].append(dist)

    ugly_graph_hist(data,
            "local_groups.pdf",
            xlim= (1,15000),
            normed=True,
            label_len=True,
            kind="cumulog",
            ylabel = "fraction of users",
            xlabel = "distance to contact in miles",
            bins = dist_bins(120),
            )



@gob.mapper(all_items=True)
def graph_locals(rfr_dists):
    def _bucket(ratio):
        if ratio is None:
            return None
        elif 0<=ratio<.25:
            return "0.0<=ratio<.25"
        elif ratio<.5:
            return "0.25<=ratio<.5"
        elif ratio<.75:
            return "0.5<=ratio<.75"
        assert ratio<=1
        return "0.75<=ratio<=1"

    data=dict(
        lofrd = defaultdict(list),
        lofol = defaultdict(list),
        cheap = defaultdict(list),
        dirt = defaultdict(list),
    )

    for amigo in rfr_dists:
        for color,key in (('r','dirt'),('b','lofol'),('g','cheap')):
            label = _bucket(amigo[key])
            if label is None:
                data[key][('No leafs','k','dotted')].append(amigo['dist'])
            else:
                data[key][label].append(amigo['dist'])

    titles = dict(
                cheap="Contacts with Local Contacts",
                dirt="10 Contacts with Local Contacts",
                #lofrd="Contacts with Local Friends",
                lofol="Contacts with Local Followers")
    fig = plt.figure(figsize=(18,6))
    for spot,key in enumerate(('lofol','cheap','dirt')):
        ax = fig.add_subplot(1,3,1+spot,title=titles[key])

        for subkey,dists in data[key].iteritems():
            print key, subkey, 1.0*sum(1 for d in dists if d<25)/len(dists)

        ugly_graph_hist(data[key],
            'ignored',
            ax=ax,
            bins=dist_bins(120),
            xlim=(1,15000),
            label_len=True,
            kind="cumulog",
            normed=True,
            xlabel = "distance between edges in miles",
            ylabel = "fraction of users",
            )

    fig.savefig("../flt/figures/local_ratio.pdf",bbox_inches='tight')



@gob.mapper(all_items=True)
def graph_com_types(edge_dists):
    data = defaultdict(lambda: defaultdict(list))

    for key,dists in edge_dists:
        if key[0]=='rand':
            continue
        edge_type,i_at,u_at,prot = key
        # ignore protected
        data[edge_type][i_at,u_at].extend(dists)


    titles = dict(
        jfol="Just Follower",
        rfrd="Reciprical Friend",
        jfrd="Just Friend",
        jat="Just Mentiened")
    labels = {
        (False,False):"We ignore",
        (True,False):"I talk",
        (False,True):"You talk",
        (True,True):"We talk",
        }
    fig = plt.figure(figsize=(18,12))

    for edge_type,sub_d in data.iteritems():
        for mentions,dists in sub_d.iteritems():
            print edge_type, mentions, 1.0*sum(1 for d in dists if d<25)/len(dists)

    for spot,edge_type in enumerate(['rfrd','jfrd','jfol','jat']):
        ax = fig.add_subplot(2,2,1+spot)

        # UGLY
        picked = {
            labels[key]:dists
            for key,dists in data[edge_type].iteritems()
        }

        ugly_graph_hist(picked, "", ax=ax,
                legend_loc=2,
                bins=dist_bins(80),
                kind="cumulog",
                xlim=(1,15000),
                normed=True,
                label_len=True,
                xlabel = "distance between edges in miles",
                ylabel = "number of users",
                )
        ax.set_title(titles[edge_type])
    fig.savefig("../www/com_types.pdf",bbox_inches='tight')


def triad_types():
    fig = plt.figure(figsize=(24,12))
    titles = dict(fol="Just Follower", rfrd="Reciprical Friend", frd="Just Friend", jat="Just Mentiened")
    for col,edge_type in enumerate(['rfrd','frd','fol','jat']):
        ax = fig.add_subplot(2,2,1+col)
        counts = list(read_json('geo_%s_simp'%edge_type))
        data = {}
        for field,color in zip(("star","fan","path","loop"),'rbgk'):
            steps = [
                (False,'dotted',.5,"no"),
                (True,'solid',1,"has"), ]
            for part,style,lw,prefix in steps:
                label = "%s %s"%(prefix,field)
                key = (label, color, style, lw)
                data[key] = [
                    d['dist']
                    for d in counts
                    if part==bool(d[field])]
        ugly_graph_hist(data, "", ax=ax,
                bins=dist_bins(80),
                kind="cumulog",
                xlim=(1,15000),
                label_len=True,
                normed=True,
                xlabel = "distance between edges in miles",
                ylabel = "number of users",
                )
        ax.set_title(titles[edge_type])
    fig.savefig("../www/triad_types.pdf",bbox_inches='tight')


@gob.mapper(all_items=True)
def graph_mloc_mdist(mloc_mdists):
    dists = defaultdict(list)
    labels = ["1",'10','100','1000']
    for mloc,mdist in mloc_mdists:
            bin = len(str(int(mdist))) if mdist>=1 else 0
            for key in labels[bin:]:
                dists['PLE<'+key].append(mloc)
            dists[('all','k','solid',2)].append(mloc)
            dists[('PLE','.6','dashed',1)].append(mdist)
    for key,vals in dists.iteritems():
        print key,sum(1 for v in vals if v<1000)

    ugly_graph_hist(dists,
            "mloc_mdist.pdf",
            bins = dist_bins(120),
            kind="cumulog",
            normed=True,
            label_len=True,
            xlim=(1,15000),
            xlabel = "location error in miles",
            ylabel = "fraction of users",
            )


@gob.mapper(all_items=True)
def near_triads(rfr_triads):
    labels = ["",'0-10','10-100','100-1000','1000+']
    data = defaultdict(list)

    for quad in rfr_triads:
        for key,color in (('my','r'),('our','b')):
            edist = coord_in_miles(quad[key]['loc'],quad['you']['loc'])
            bin = min(4,len(str(int(edist))))
            label = '%s %s'%(key,labels[bin])
            dist = coord_in_miles(quad[key]['loc'],quad['me']['loc'])
            # 1.6**(bin-1) is the line width calculation
            data[label,color,'solid',1.6**(bin-1)].append(dist)
    ugly_graph_hist(data,
            "near_triads.pdf",
            bins=dist_bins(120),
            xlim=(1,15000),
            label_len=True,
            kind="cumulog",
            normed=True,
            xlabel = "distance between edges in miles",
            ylabel = "number of users",
            )


def mine_ours_img():
    bins = dist_bins(40)
    data = numpy.zeros((len(bins),len(bins)))
    for quad in read_json('rfr_triads'):
        if quad['my']['loc']['mdist']<100  and quad['our']['loc']['mdist']<100:
            spot = [
                bisect.bisect_left(bins, 1+coord_in_miles(quad['me']['loc'],quad[key]['loc']))
                for key in ('our','my')
            ]
            data[tuple(spot)]+=1
    
    data = data-numpy.transpose(data)
    fig = plt.figure(figsize=(24,24))
    ax = fig.add_subplot(111)
    ax.imshow(data,interpolation='nearest')

    ax.set_xlim(0,160)
    ax.set_ylim(0,160)
    ax.set_xlabel("mine")
    ax.set_ylabel("ours")
    ax.set_title("closed vs. open triads")
    fig.savefig('../www/mine_ours.png')
    

def plot_mine_ours():
    data = dict(our=[],my=[])
    for quad in read_json('rfr_triads'):
        if quad['my']['loc']!=quad['our']['loc'] and quad['my']['loc']['mdist']<100  and quad['our']['loc']['mdist']<100:
            for key in data:
                dist = coord_in_miles(quad['me']['loc'],quad[key]['loc'])
                data[key].append(1+dist)
    
    fig = plt.figure(figsize=(24,24))
    ax = fig.add_subplot(111)
    ax.loglog(data['our'],data['my'],'+',
            color='k',
            alpha=.05,
            markersize=10,
            )
    ax.set_xlim(1,15000)
    ax.set_ylim(1,15000)
    ax.set_xlabel("ours")
    ax.set_ylabel("mine")
    ax.set_title("closed vs. open triads")
    fig.savefig('../www/mine_ours.png')
    

def graph_from_net(net):
    edges = [(fol,rfr['_id'])
        for rfr in net['rfrs']
        for fol in rfr['fols']]
    g = nx.DiGraph(edges)
    g.add_nodes_from(
        (r['_id'], dict(lat=r['lat'],lng=r['lng']))
        for r in net['rfrs'])
    return g


def draw_net_map():
    size=10
    counter = 0
    fig = plt.figure(figsize=(size*4,size*2))
    for net in read_json('rfr_net'):
        counter+=1
        g = graph_from_net(net)
        if not g.size(): continue
        ax = fig.add_subplot(size,size,counter,frame_on=False)
        ax.bar(net['mloc'][0]-.5,1,1,net['mloc'][1]-.5,edgecolor='b')
        pos = dict((r['_id'],(r['lng'],r['lat'])) for r in net['rfrs'])
        nx.draw_networkx_nodes(g,
                ax=ax,
                pos=pos,
                alpha=.1,
                node_size=50,
                edgecolor='r',
                node_shape='d',
                )
        nx.draw_networkx_edges(g,
                ax=ax,
                pos=pos,
                alpha=.2,
                width=1,
                )
        ax.set_xlim(-126,-66)
        ax.set_ylim(24,50)
        ax.set_xticks([])
        ax.set_yticks([])
        if counter ==size*size:
            break
    fig.savefig('../www/net_map.png')

