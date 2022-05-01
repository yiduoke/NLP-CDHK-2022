import nltk
import json

f = open('gg2015.json')
data = json.load(f)

for tweet in data[:300000]:
  tweet_text = tweet['text']
    # print(tweet['text'], data[i]['user']['screen_name'])
  if ("award for best" in tweet_text.lower() and "predict" not in tweet_text):
    print(tweet['text'])
f.close()