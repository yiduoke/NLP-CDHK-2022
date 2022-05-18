'''Version 0.35'''
import re
import json
import csv
import spacy 
import pandas as pd

# ----------------------------------- Global Variables -----------------------------------
OFFICIAL_AWARDS_1315 = ['cecil b. demille award', 'best motion picture - drama', 'best performance by an actress in a motion picture - drama', 'best performance by an actor in a motion picture - drama', 'best motion picture - comedy or musical', 'best performance by an actress in a motion picture - comedy or musical', 'best performance by an actor in a motion picture - comedy or musical', 'best animated feature film', 'best foreign language film', 'best performance by an actress in a supporting role in a motion picture', 'best performance by an actor in a supporting role in a motion picture', 'best director - motion picture', 'best screenplay - motion picture', 'best original score - motion picture', 'best original song - motion picture', 'best television series - drama', 'best performance by an actress in a television series - drama', 'best performance by an actor in a television series - drama', 'best television series - comedy or musical', 'best performance by an actress in a television series - comedy or musical', 'best performance by an actor in a television series - comedy or musical', 'best mini-series or motion picture made for television', 'best performance by an actress in a mini-series or motion picture made for television', 'best performance by an actor in a mini-series or motion picture made for television', 'best performance by an actress in a supporting role in a series, mini-series or motion picture made for television', 'best performance by an actor in a supporting role in a series, mini-series or motion picture made for television']
OFFICIAL_AWARDS_1819 = ['best motion picture - drama', 'best motion picture - musical or comedy', 'best performance by an actress in a motion picture - drama', 'best performance by an actor in a motion picture - drama', 'best performance by an actress in a motion picture - musical or comedy', 'best performance by an actor in a motion picture - musical or comedy', 'best performance by an actress in a supporting role in any motion picture', 'best performance by an actor in a supporting role in any motion picture', 'best director - motion picture', 'best screenplay - motion picture', 'best motion picture - animated', 'best motion picture - foreign language', 'best original score - motion picture', 'best original song - motion picture', 'best television series - drama', 'best television series - musical or comedy', 'best television limited series or motion picture made for television', 'best performance by an actress in a limited series or a motion picture made for television', 'best performance by an actor in a limited series or a motion picture made for television', 'best performance by an actress in a television series - drama', 'best performance by an actor in a television series - drama', 'best performance by an actress in a television series - musical or comedy', 'best performance by an actor in a television series - musical or comedy', 'best performance by an actress in a supporting role in a series, limited series or motion picture made for television', 'best performance by an actor in a supporting role in a series, limited series or motion picture made for television', 'cecil b. demille award']
answers = {"hosts": ["amy poehler","tina fey"],"award_data": {"best screenplay - motion picture": {"nominees": ["the grand budapest hotel","gone girl","boyhood","the imitation game"],"presenters": ["bill hader","kristen wiig"],"winner": "birdman"},"best director - motion picture": {"nominees": ["wes anderson","ava duvernay","david fincher","alejandro inarritu gonzalez"],"presenters": ["harrison ford"],"winner": "richard linklater"},"best performance by an actress in a television series - comedy or musical": {"nominees": ["lena dunham","edie falco","julia louis-dreyfus","taylor schilling"],"presenters": ["bryan cranston","kerry washington"],"winner": "gina rodriguez"},"best foreign language film": {"nominees": ["force majeure","gett: the trial of viviane amsalem","ida","tangerines"],"presenters": ["colin farrell","lupita nyong'o"],"winner": "leviathan"},"best performance by an actor in a supporting role in a motion picture": {"nominees": ["robert duvall","edward norton","mark ruffalo"],"presenters": ["jennifer aniston","benedict cumberbatch"],"winner": "j.k. simmons"},"best performance by an actress in a supporting role in a series, mini-series or motion picture made for television": {"nominees": ["uzo aduba","kathy bates","allison janney","michelle monaghan"],"presenters": ["jamie dornan","dakota johnson"],"winner": "joanne froggatt"},"best motion picture - comedy or musical": {"nominees": ["birdman","into the woods","pride","st. vincent"],"presenters": ["robert downey, jr."],"winner": "the grand budapest hotel"},"best performance by an actress in a motion picture - comedy or musical": {"nominees": ["emily blunt","helen mirren","julianne moore","quvenzhane wallis"],"presenters": ["ricky gervais"],"winner": "amy adams"},"best mini-series or motion picture made for television": {"nominees": ["the missing","the normal heart","olive kitteridge","true detective"],"presenters": ["jennifer lopez","jeremy renner"],"winner": "fargo"},"best original score - motion picture": {"nominees": ["the imitation game","birdman","gone girl","interstellar"],"presenters": ["sienna miller","vince vaughn"],"winner": "the theory of everything"},"best performance by an actress in a television series - drama": {"nominees": ["claire danes","viola davis","julianna margulies","robin wright"],"presenters": ["anna faris","chris pratt"],"winner": "ruth wilson"},"best performance by an actress in a motion picture - drama": {"nominees": ["jennifer aniston","felicity jones","rosamund pike","reese witherspoon"],"presenters": ["matthew mcconaughey"],"winner": "julianne moore"},"cecil b. demille award": {"nominees": [],"presenters": ["don cheadle","julianna margulies"],"winner": "george clooney"},"best performance by an actor in a motion picture - comedy or musical": {"nominees": ["ralph fiennes","bill murray","joaquin phoenix","christoph waltz"],"presenters": ["amy adams"],"winner": "michael keaton"},"best motion picture - drama": {"nominees": ["foxcatcher","the imitation game","selma","the theory of everything"],"presenters": ["meryl streep"],"winner": "boyhood"},"best performance by an actor in a supporting role in a series, mini-series or motion picture made for television": {"nominees": ["alan cumming","colin hanks","bill murray","jon voight"],"presenters": ["katie holmes","seth meyers"],"winner": "matt bomer"},"best performance by an actress in a supporting role in a motion picture": {"nominees": ["jessica chastain","keira knightley","emma stone","meryl streep"],"presenters": ["jared leto"],"winner": "patricia arquette"},"best television series - drama": {"nominees": ["downton abbey (masterpiece)","game of thrones","the good wife","house of cards"],"presenters": ["adam levine","paul rudd"],"winner": "the affair"},"best performance by an actor in a mini-series or motion picture made for television": {"nominees": ["martin freeman","woody harrelson","matthew mcconaughey","mark ruffalo"],"presenters": ["jennifer lopez","jeremy renner"],"winner": "billy bob thornton"},"best performance by an actress in a mini-series or motion picture made for television": {"nominees": ["jessica lange","frances mcdormand","frances o'connor","allison tolman"],"presenters": ["kate beckinsale","adrien brody"],"winner": "maggie gyllenhaal"},"best animated feature film": {"nominees": ["big hero 6","the book of life","the boxtrolls","the lego movie"],"presenters": ["kevin hart","salma hayek"],"winner": "how to train your dragon 2"},"best original song - motion picture": {"nominees": ["big eyes","noah","annie","the hunger games: mockingjay - part 1"],"presenters": ["prince"],"winner": "selma"},"best performance by an actor in a motion picture - drama": {"nominees": ["steve carell","benedict cumberbatch","jake gyllenhaal","david oyelowo"],"presenters": ["gwyneth paltrow"],"winner": "eddie redmayne"},"best television series - comedy or musical": {"nominees": ["girls","jane the virgin","orange is the new black","silicon valley"],"presenters": ["bryan cranston","kerry washington"],"winner": "transparent"},"best performance by an actor in a television series - drama": {"nominees": ["clive owen","liev schreiber","james spader","dominic west"],"presenters": ["david duchovny","katherine heigl"],"winner": "kevin spacey"},"best performance by an actor in a television series - comedy or musical": {"nominees": ["louis c.k.","don cheadle","ricky gervais","william h. macy"],"presenters": ["jane fonda","lily tomlin"],"winner": "jeffrey tambor"}}}
nlp = spacy.load("en_core_web_sm")
# ----------------------------------- Helper Functions -----------------------------------
def find_persons(text):
    # Create Doc object
    doc2 = nlp(text)

    # Identify the persons
    persons = [ent.text for ent in doc2.ents if ent.label_ == 'PERSON']

    # Return persons
    return persons

def find_films(text):
    # Create Doc object
    doc2 = nlp(text)

    # ID the films
    films = [ent.text for ent in doc2.ents if ent.label_ == 'WORK_OF_ART']

    return films

def isHypothetical(text):
    indicator = r"\?|\bhope\b|\bhoping\b|\bbet|\bthink|\bwill\b|\bpredict|\bgoing to\b|\bgonna\b|\bshould|\bif\b"
    if re.search(indicator, text):
        return True
    return False

def isHistorical(text):
    if (re.findall(r"\d\d\d\d", text) and '2015' not in text and '2014' not in text) or 'last year' in text:
        return True
    return False

def isReasonable(text):
    if not isHypothetical(text.lower()) and not isHistorical(text.lower()):
        return True
    return False

def indicatesWin(text):
    winIndicators = ['won', 'win', 'congrat', 'goes to', 'went to', 'snag', 'takes home', 'took home']
    for word in winIndicators:
        if word in text:
            return True
    return False

def isWinningTweet(text, awardIndicators, trips = []):
    """
        <text> = tweet text
        <award> = list of indicators that belong to a given award
    """
    text = text.lower()
    missingWordCount = 0
    
    if indicatesWin(text):
        for a in awardIndicators:
            if a not in text:
                # return False # we want an indication of our relevant award
                missingWordCount += 1

        if float(missingWordCount) > 0.5 * float(len(awardIndicators)) - 2: #no missing words allowed from 4-word award, 1 missing word allowed from 6-word award
            return False # not enough of our award indicator words in tweet

        for t in trips:
            if t in text:
                return False # we do not want indication of a tripword

        return True

    # does not contain an indicator of a winning tweet
    return False

def awardNameToKeywords(text):
    stops = ['by', 'an', 'a', 'or', 'in', 'for', '-']
    l = text.lower().split()
    for s in stops:
        for i in range(l.count(s)):
            l.remove(s)
    for i in range(len(l)):
        l[i] = l[i].replace(',', '')
    return l

def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3

def listDif(lst1, lst2): #lst1 - lst2
    lst3 = [value for value in lst1 if value not in lst2]
    return lst3

def findTripwords(award, awardList):
    tripwords = set(())
    for b in awardList:
        if award.keywords == b.keywords: # avoid comparing
            pass
        elif float(len(intersection(award.keywords,b.keywords))) / float(len(award.keywords)) > .5 or \
            float(len(intersection(award.keywords,b.keywords))) / float(len(b.keywords)) > .5: #sufficiently similar award names
        # else:
            for word in listDif(b.keywords, award.keywords): # pulls out words that are in other award names but not in our award of interest
                # if word not in tripwords:
                    # print("adding ", word)
                tripwords.add(word)
    return list(tripwords)

def tweet_cleaner(year):
    '''
    Returns a dataframe of the cleaned tweets.
    '''
    # Opening JSON file
    fname = 'gg' + str(year) + '.json'
    f = open(fname)
    data = json.load(f)
    tt = []
    # print first 100 tweets
    for tweet in data:
        # print(tweet['text'], data[99]['user']['screen_name'])
        tt.append(tweet['text'])
    del data
    #df_tweets = pd.DataFrame(data, columns=['text'])
    f.close()
    return tt

def pass_cap_ratio(sentence, ratio_filter = 0.66, sentence_length = 3):
    words = sentence.split(" ")
    return sum(1 for word in words if word.istitle())/len(words) > ratio_filter and len(sentence) > sentence_length

def keyword_hits(words, array):
    print("array: ", array)
    return functools.reduce(lambda a, b: (a in array) + (b in array), words)



# ----------------------------------- parsing functions -----------------------------------
class award:
    def __init__(self, name = "", keywords = [], tripwords = []):
        self.name = name
        self.keywords = keywords
        self.tripwords = tripwords
        self.winner = ""

def get_hosts(year):
    '''Hosts is a list of one or more strings. Do NOT change the name
    of this function or what it returns.'''

    # Opening JSON file
    fname = 'gg' + str(year) + '.json'
    f = open(fname)

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
    f.close()
    return hosts

def get_awards(year):
    '''Awards is a list of strings. Do NOT change the name
    of this function or what it returns.'''
    # Opening JSON file
    fname = 'gg' + str(year) + '.json'
    f = open(fname)

    # returns JSON object as
    # a dictionary
    data = json.load(f)
    award_names_dict = {}
    for tweet in data:
        tweet_text = " " + tweet['text'] + " "
        stop_words = ['comedy', 'drama', 'television', 'tv', 'series', 'picture', 'film', 'movie']
        
        tweet = tweet['text'].lower().split()
        
        if ('best' in tweet):
            for topic in stop_words:
                if (topic in tweet):
                    if tweet.index('best') < tweet.index(topic):
                        ## add to dic or update
                        item = tweet[tweet.index('best'):tweet.index(topic) + 1 ]
                        item_str = " ".join(item)
                        if item_str not in award_names_dict:
                            award_names_dict[item_str] = 1
                        else:
                            award_names_dict[item_str] += 1
    #print(dict(sorted(award_names_dict.items(), key=lambda item: item[1])))  
    return sorted(award_names_dict, key=award_names_dict.get, reverse=True)[:25]

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
    year = 2015 # <------- Change to another year. 
    df_tweets = tweet_cleaner(year)

    print("\n**************************** hosts ****************************")
    hosts = get_hosts(year)
    print("         ", hosts[0], "\n         ", hosts[1])

    print("\n**************************** awards ****************************")
    awards = get_awards(year)
    for i in range(25):
        print(awards[i])

    print("\n**************************** Award Winners ****************************")
    ############### KEEP THE HASHTAG SOLUTIONS FOR AWARDS THAT GO TO MOVIES, USE THIS FOR PEOPLE AWARDS
    # create list of award objects
    awardList = []
    for a in answers["award_data"].keys():
        # print(a)
        # print(awardNameToKeywords(a))
        awardList.append(award(name = a, keywords = awardNameToKeywords(a)))

    # find tripwords!
    for a in awardList:
        a.tripwords = findTripwords(award = a, awardList = awardList)

    #filter to only awards that go to people. this info could go in a config file if we really needed to
    peopleAwards = []
    for ggAward in awardList:
        if 'performance' in ggAward.keywords or 'director' in ggAward.keywords or 'cecil' in ggAward.keywords:
            peopleAwards.append(ggAward)

    ttr = [] # pruned tweets by reasonability - i.e. not hypothetical and not historic
    tt = tweet_cleaner(year)
    for t in tt:
        if isReasonable(t) and 'RT' not in t:
            ttr.append(t)

    # find winner of every award
    for ggAward in peopleAwards:
        print("----------------------------------------------------------------")
        print("Award name: ", ggAward.name)


        # print(ggAward.name)
        winningTweets = []
        # iter over tweets and add tweets that could contain the answer to our question
        for t in ttr:
            if isWinningTweet(t, ggAward.keywords, ggAward.tripwords):
                winningTweets.append(t)
        # in the case that we've been too restrictive, loosen constraints - no tripwords
        if len(winningTweets) == 0:
            print('no ideal tweets found, removing tripword requirement')
            for t in ttr:
                if isWinningTweet(t, ggAward.keywords):
                    winningTweets.append(t)
        

        # print("number of relevant winning tweets found: ", len(winningTweets))

        # candWinners is a dict of counts of co-occurance of each candidate for winning. in the end we return the most popular name from the tweets.
        candWinners = {}
        # set for hash table speed
        namesSet = set(())

        for t in winningTweets:
            people = find_persons(t)
            for p in people:
                if '@' in p or 'RT' in p or 'golden' in p:
                    people = people.remove(p)
            if not people:
                continue
            for p in people:
                if p in namesSet:
                    candWinners[p] += 1
                else:
                    candWinners[p] = 1
                namesSet.add(p)

        # post processing - cleaning
        toDelete = []
        for name in candWinners.keys():
            if '@' in name or 'golden' in name.lower():
                toDelete.append(name)
                continue
            ns = name.lower().split()
            # print("ns", ns)
            nsl = 0
            for i in ns:
                if i in ggAward.name:
                    nsl += 1
            if nsl == len(ns):
                toDelete.append(name)

        for d in toDelete:
            candWinners.pop(d)
        
        # sort by popularity then print winner
        winnerCounts = (sorted(candWinners.items(), key=lambda item: 1/item[1]))
        try:
            print("predicted winner: ", winnerCounts[0][0])
        except:
            print("no answer found")
    
    print("\n**************************** nominees ****************************")
    nomTweets = []
    nom_keywords = [" nom", "nom ", "nomin", "robb", "hope ", "should", "deserve"]

    nomDict = {}

    for ggAward in awardList:
        nomDict[ggAward] = {}
        try:
            ggAward.keywords.remove("best")
            # print("removed best")
        except:
            continue
        
        
    for tweet in tt:
        tweet = tweet.replace('\n', ' ')
        candNoms = []
        if any(keyword in tweet for keyword in nom_keywords) and "best" in tweet.lower():
            # print("tweet: ", tweet)
            doc = nlp(tweet)
            noun_phrases = [noun_chunk.text.strip('"').strip("''").lower() for noun_chunk in doc.noun_chunks if 'RT @' not in noun_chunk.text]
            passing_noun_phrases = list(filter(pass_cap_ratio, noun_phrases))

            for ent in doc.ents:
                # print("Entity Recognition: ", ent.text, ent.label_)
                if (ent.label_ == "PERSON" or ent.label_ == "ORG" and "globe" not in ent.text.lower()):
                    candNoms.append(ent.text)
                    
            # print("noun phrases: ", noun_phrases)
            proper_nouns = [tok for tok in nlp(tweet) if tok.pos_ == "PROPN"]
            
            # print("proper nouns: ", proper_nouns)
            # print("possible nominees for this tweet: ", candNoms)
            
            mostRelevantAward = awardList[0]
            highestRelevancy = 0
            for ggAward in awardList:
                currentAwardRelevancy = 0
                
                
                for noun_phrase in noun_phrases:
                    for word in noun_phrase.split(" "):
                        if any(word in award for award in ggAward.keywords if len(word)>2):
                            currentAwardRelevancy += 1
                            
                if currentAwardRelevancy > highestRelevancy or (currentAwardRelevancy == highestRelevancy and len(ggAward.keywords) < len(mostRelevantAward.keywords)):
                    mostRelevantAward = ggAward
                    highestRelevancy = currentAwardRelevancy
                    
                
            if (highestRelevancy>0):
                #print("most relevant nomination for ", mostRelevantAward.name)
                for candNom in candNoms:
                    if candNom in nomDict[mostRelevantAward]:
                        nomDict[mostRelevantAward][candNom] += 1
                    else:
                        nomDict[mostRelevantAward][candNom] = 1
            # else:
            #     print("no nominations from this tweet")
                


            # print('\n')
    for k, v in nomDict.items():
        print(k.name, v)
    return

if __name__ == '__main__':
    main()
