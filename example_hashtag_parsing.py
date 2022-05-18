from hashtag_parsing import HashtagParser
from loading_utils import load_tweet_text_from_json

data = load_tweet_text_from_json('gg2015.json')
hp = HashtagParser(data)
award_names = hp.parse_award_names(data, verbose=True)

print('------- official output --------')
print('Found ' + str(len(award_names)) + ' award names:')
for name in award_names:
    print('\t', name)
