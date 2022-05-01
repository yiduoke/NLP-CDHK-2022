import ijson

def load_tweet_text_from_json(fp):
    tweets = []
    with open(fp, "r") as f:
        for record in ijson.items(f, "item"):
            tweets.append({'text': record['text']})
    return tweets

def load_all_from_json(fp):
    tweets = []
    with open(fp, "r") as f:
        for record in ijson.items(f, "item"):
            tweets.append({
                'id': record['int'],
                'text': record['text'],
                'user': {
                    'id': record['user']['id'],
                    'screen_name': record['user']['screen_name'],
                },
                'timestamp_ms': record['timestamp_ms']
            })
    return tweets

# data = load_tweet_text_from_json('gg2015.json')

