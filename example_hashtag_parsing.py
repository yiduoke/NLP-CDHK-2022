from hashtag_parsing import HashtagParser
from loading_utils import load_tweet_text_from_json

data = load_tweet_text_from_json('gg2015.json')
hp = HashtagParser(data)
hp.parse_hashtag_concepts(data)