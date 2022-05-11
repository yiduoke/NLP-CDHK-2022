'''Version 0.35'''

OFFICIAL_AWARDS_1315 = ['cecil b. demille award', 'best motion picture - drama', 'best performance by an actress in a motion picture - drama', 'best performance by an actor in a motion picture - drama', 'best motion picture - comedy or musical', 'best performance by an actress in a motion picture - comedy or musical', 'best performance by an actor in a motion picture - comedy or musical', 'best animated feature film', 'best foreign language film', 'best performance by an actress in a supporting role in a motion picture', 'best performance by an actor in a supporting role in a motion picture', 'best director - motion picture', 'best screenplay - motion picture', 'best original score - motion picture', 'best original song - motion picture', 'best television series - drama', 'best performance by an actress in a television series - drama', 'best performance by an actor in a television series - drama', 'best television series - comedy or musical', 'best performance by an actress in a television series - comedy or musical', 'best performance by an actor in a television series - comedy or musical', 'best mini-series or motion picture made for television', 'best performance by an actress in a mini-series or motion picture made for television', 'best performance by an actor in a mini-series or motion picture made for television', 'best performance by an actress in a supporting role in a series, mini-series or motion picture made for television', 'best performance by an actor in a supporting role in a series, mini-series or motion picture made for television']
OFFICIAL_AWARDS_1819 = ['best motion picture - drama', 'best motion picture - musical or comedy', 'best performance by an actress in a motion picture - drama', 'best performance by an actor in a motion picture - drama', 'best performance by an actress in a motion picture - musical or comedy', 'best performance by an actor in a motion picture - musical or comedy', 'best performance by an actress in a supporting role in any motion picture', 'best performance by an actor in a supporting role in any motion picture', 'best director - motion picture', 'best screenplay - motion picture', 'best motion picture - animated', 'best motion picture - foreign language', 'best original score - motion picture', 'best original song - motion picture', 'best television series - drama', 'best television series - musical or comedy', 'best television limited series or motion picture made for television', 'best performance by an actress in a limited series or a motion picture made for television', 'best performance by an actor in a limited series or a motion picture made for television', 'best performance by an actress in a television series - drama', 'best performance by an actor in a television series - drama', 'best performance by an actress in a television series - musical or comedy', 'best performance by an actor in a television series - musical or comedy', 'best performance by an actress in a supporting role in a series, limited series or motion picture made for television', 'best performance by an actor in a supporting role in a series, limited series or motion picture made for television', 'cecil b. demille award']

import re
import json

def isHypothetical(text):
    if '?' in text or 'last year' in text or 'hope' in text or 'hoping' in text or 'bet' in text or 'betting' in text:
        return True
    return False

def isHistorical(text):
    if re.findall(r"\d\d\d\d", text) and '2015' not in text and '2014' not in text:
        return True
    return False

def isReasonable(text):
    if not isHypothetical(text) and not isHistorical(text):
        return True
    return False


def get_hosts(year):
    '''Hosts is a list of one or more strings. Do NOT change the name
    of this function or what it returns.'''
    import json
    import re

    # Opening JSON file
    fname = 'gg' + str(year) + '.json'
    f = open('gg2015.json')

    # returns JSON object as
    # a dictionary
    data = json.load(f)


    matches = []
    namePattern = r"[A-Z][a-z]+ [A-Z][a-z]+"

    #finding tweets that contain 'host'
    for i, tweet in enumerate(data):
        if 'host' in tweet['text'].lower() and isReasonable(tweet['text'].lower()):
            matches.append(re.findall(namePattern, tweet['text']))

    namesDict = {}
    for match in matches:
        for name in match:
            if name in namesDict.keys():
                namesDict[name] += 1
            else:
                namesDict[name] = 1

    counts = (sorted(namesDict.items(), key=lambda item: 1/item[1]))
    hosts = []
    hosts.append(counts[0][0].lower())
    hosts.append(counts[1][0].lower())
    print(hosts)
    f.close()

def get_awards(year):
    '''Awards is a list of strings. Do NOT change the name
    of this function or what it returns.'''
    try:
        f = open('gg' + str(year) + '.json')
    except:
        f = open('../Data/gg' + str(year) + '.json')
    data = json.load(f)
    hashtag_dict = {}
    award_names_dict = {}

    for tweet in data:
        tweet_text = " " + tweet['text'] + " "
  
        # populating hashtag dict
        if ("#" in tweet_text):
            hashtags = re.findall(" #\w+ ", tweet_text)
            for hashtag in hashtags:
                if hashtag not in hashtag_dict:
                    hashtag_dict[hashtag] = 1
                else:
                    hashtag_dict[hashtag] += 1

        topics = ['comedy', 'drama', 'television', 'tv', 'series', 'picture', 'film', 'movie']
        tweet = tweet['text'].lower().split()
        if 'tv' in tweet:
            tweet[tweet.index('tv')] = 'television'
        if ('best' in tweet):
            for topic in topics:
                if (topic in tweet):
                    if tweet.index('best') < tweet.index(topic):
                        ## add to dic or update
                        item = tweet[tweet.index('best'):tweet.index(topic) + 1 ]
                        item_str = " ".join(item)
                        if item_str not in award_names_dict:
                            award_names_dict[item_str] = 1
                        else:
                            award_names_dict[item_str] += 1
    print(dict(sorted(award_names_dict.items(), key=lambda item: item[1])))  
    awards = "work to be done still."
    return awards

def get_nominees(year):
    '''Nominees is a dictionary with the hard coded award
    names as keys, and each entry a list of strings. Do NOT change
    the name of this function or what it returns.'''
    # Your code here
    return nominees

def get_winner(year):
    '''Winners is a dictionary with the hard coded award
    names as keys, and each entry containing a single string.
    Do NOT change the name of this function or what it returns.'''
    # Your code here
    return winners

def get_presenters(year):
    '''Presenters is a dictionary with the hard coded award
    names as keys, and each entry a list of strings. Do NOT change the
    name of this function or what it returns.'''
    # Your code here
    return presenters

def pre_ceremony():
    '''This function loads/fetches/processes any data your program
    will use, and stores that data in your DB or in a json, csv, or
    plain text file. It is the first thing the TA will run when grading.
    Do NOT change the name of this function or what it returns.'''
    # Your code here
    print("Pre-ceremony processing complete.")
    return

def main():
    '''This function calls your program. Typing "python gg_api.py"
    will run this function. Or, in the interpreter, import gg_api
    and then run gg_api.main(). This is the second thing the TA will
    run when grading. Do NOT change the name of this function or
    what it returns.'''
    pass


    return

if __name__ == '__main__':
    main()
