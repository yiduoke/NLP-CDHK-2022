import nltk
import json
import re
import spacy
from nltk import Tree

f = open('gg2015.json')
data = json.load(f)
hashtag_dict = {}
award_names_dict = {}

nlp = spacy.load("en_core_web_sm")

# en_nlp = spacy.load('en')

# example_tweet = 'Best Performance by an Actress in a Television Series - Musical or Comedy Gina Rodriguez for "Jane the Virgin"'.lower()
example_tweet = 'best performance by an actress in a television series'
doc = nlp(example_tweet)

def to_nltk_tree(node):
    if node.n_lefts + node.n_rights > 0:
        return Tree(node.orth_, [to_nltk_tree(child) for child in node.children])
    else:
        return node.orth_


[to_nltk_tree(sent.root).pretty_print() for sent in doc.sents]


# bests = re.findall("(Best (([A-Z][a-z]+) |- )+)", example_tweet)
# for best in bests:
#       best = best[0]
#       if best not in award_names_dict:
#         award_names_dict[best] = 1
#       else:
#         award_names_dict[best] += 1

# doc = nlp(example_tweet)
# for token in doc:
#   print (token.text, [child for child in token.children])


# for tweet in data:
#   tweet_text = " " + tweet['text'] + " "
  
#   # populating hashtag dict
#   if ("#" in tweet_text):
#     hashtags = re.findall(" #\w+ ", tweet_text)
#     for hashtag in hashtags:
#       if hashtag not in hashtag_dict:
#         hashtag_dict[hashtag] = 1
#       else:
#         hashtag_dict[hashtag] += 1
    
#   #populating award_names_dict
#   if ("Best" in tweet_text):
#     bests = re.findall("(Best (([A-Z][a-z]+) |- )+)", tweet_text)
#     # if not len(bests):
#     #   print(tweet_text)

    # for best in bests:
    #   best = best[0]
    #   if best not in award_names_dict:
    #     award_names_dict[best] = 1
    #   else:
    #     award_names_dict[best] += 1
  
  


# # print(sorted(dict, key=lambda x: x[1]))
# # print(dict(sorted(hashtag_dict.items(), key=lambda item: item[1])))
print(dict(sorted(award_names_dict.items(), key=lambda item: item[1])))
# f.close()