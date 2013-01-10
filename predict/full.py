
from base.models import User
from base import gob, twitter, gisgraphy
from explore import sprawl
from predict import fl

# this is the worst PLE that we are willing to accept
MAX_GNP_MDIST = 25


def _crawl_pred_one(user,twit,gis,pred):
    if user.location and not user.geonames_place:
        user.geonames_place = gis.twitter_loc(user.location)

    gnp = user.geonames_place
    if gnp and gnp.mdist<MAX_GNP_MDIST:
        user.pred_loc = gnp.to_tup()
        return

    nebrs, ats, ated = sprawl.crawl_single(user,twit,gis)
    if nebrs:
        user.pred_loc = pred.predict( user, nebrs, ats, ated )


@gob.mapper(all_items=True,slurp={'mdists':next})
def crawl_predict(user_ds, env, mdists):
    """
    takes a user dictionary, runs the crawler and predictor
    """
    twit = twitter.TwitterResource()
    gis = gisgraphy.GisgraphyResource()
    gis.set_mdists(mdists)

    pred = fl.Predictors(env)
    pred.load_env(env,'0')
    for user_d in user_ds:
        user = User.get_id(user_d['id'])
        if not user or not user.pred_loc:
            user = User(user_d)
            _crawl_pred_one(user,twit,gis,pred)
            user.merge()
        yield user.to_d()


@gob.mapper(all_items=True,slurp={'mdists':next})
def cheap_predict(user_ds, env, mdists):
    """
    takes a user dictionary, runs the geocoder without crawling, adds the
    location if we can find one
    """
    gis = gisgraphy.GisgraphyResource()
    gis.set_mdists(mdists)

    for user_d in user_ds:
        if not user_d['loc']:
            continue
        gnp = gis.twitter_loc(user_d['loc'])
        if gnp and gnp.mdist<MAX_GNP_MDIST:
            user_d['ploc'] = gnp.to_tup()
            yield user_d

