import re
from typing import List, Set

# hardcoded regex rules
ACCOUNT_REGEX = r"@[^\W]+"
HASHTAG_REGEX = r"#[^\W_]+"
LINK_REGEX = r"http://[^ ]+"


def clean_tweet(tweet_string: str,
                remove_account_tags: bool = True,
                remove_hashtags: bool = True,
                remove_links: bool = True,
                remove_symbols: bool = False) -> str:
    """
    Util for normalizing spacing + misc. cleaning + optional removal of usernames, hashtags, and links in a tweet
    :param tweet_string: raw tweet string
    :param remove_account_tags: if true, remove all matches on @ + alphanumeric + underscores
    :param remove_hashtags: if true, remove all matches on # + alphanumeric
    :param remove_links: if true, remove all matches on http:// - TODO: this probably misses some links
    :param remove_hashtags: if true, remove all symbols
    :return: cleaned tweet string
    """
    tweet_string = tweet_string.replace('&amp;', '&')
    tweet_string = tweet_string.replace('“', '"').replace('”', '"')
    tweet_string = tweet_string.replace("'s", " 's")
    tweet_string = tweet_string.replace('\t', ' ').replace('\n', ' ')
    if remove_account_tags:
        tweet_string = re.sub(ACCOUNT_REGEX, '', tweet_string)
    if remove_hashtags:
        tweet_string = re.sub(HASHTAG_REGEX, '', tweet_string)
    if remove_links:
        tweet_string = re.sub(LINK_REGEX, '', tweet_string)
    if remove_symbols:
        strict_hyphens = re.findall(r'\w+\-\w+', tweet_string)
        for h in strict_hyphens:
            tweet_string = tweet_string.replace(h, h.replace('-', ''))
        tweet_string = re.sub(r'[^A-Za-z\d]', ' ', tweet_string)
    return re.sub(r' +', ' ', tweet_string).strip()


def tweet_to_alphanumeric(tweet_string: str) -> str:
    """
    Util for removing all spacing + symbols of a tweet. Can be used to find hashtags that map to NL utterances.
    Only keeps alphanumeric characters.
    :param tweet: raw tweet string
    :return: reduced tweet string
    """
    tweet_string = tweet_string.lower()
    tweet_string = clean_tweet(tweet_string)
    tweet_string = re.sub(r'[^a-z\d]', '', tweet_string)
    return tweet_string


def is_ascii(string: str) -> bool:
    try:
        string.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    return True


def parse_PascalCase(string: str) -> str:
    """
    TODO: description
    example i/o: 'OKParseMyPascalCase2022' --> 'OK Parse My Pascal Case 2022'
    :param string:
    :return:
    """
    # pad before any sequence of all caps
    string = re.sub('([A-Z]+)', r' \1', string)
    # pad before any sequence of (Upper + lower(s))
    string = re.sub('([A-Z][a-z]+)', r' \1', string)
    # pad between letters and numbers
    string = re.sub('([A-Za-z]+)(\d+)', r'\1 \2', string)
    string = re.sub('(\d+)([A-Za-z]+)', r'\1 \2', string)

    # standardize spacing
    string = re.sub(r' +', ' ', string)
    return string.strip()


def parse_PascalCase_to_representations(cased_hashtag_string: str) -> List[List[str]]:
    """
    TODO
    :param hashtag_string:
    :return: hashtag "chunks", hashtag possible abbreviations
    """
    cased_tag = parse_PascalCase(cased_hashtag_string)
    cased_chunks = cased_tag.lower().split()
    cased_abbreviation = [''.join([chunk[0] if not chunk.isupper() else chunk for chunk in cased_chunks])]
    if not cased_hashtag_string.isalpha():
        cased_abbreviation.append(re.sub(r'\d', '', cased_abbreviation[0]))
    if len(cased_chunks) > 1 and cased_tag.split()[-1].isupper():
        cased_abbreviation.append(''.join([chunk[0] for chunk in cased_chunks[:-1]]))
    return [cased_chunks, cased_abbreviation]

def clean_hashtag(hashtag_string: str) -> str:
    return hashtag_string.strip().replace('#', '')


def parse_hashtags_from_tweet(tweet_string: str) -> List[str]:
    """
    Get all hashtags in a tweet and update the internal log of hashtags
    :param tweet_string: raw string of a tweet
    :return: list of cleaned hashtags
    """
    # fix truncated hashtags
    tweet_string = re.sub(HASHTAG_REGEX + '\.{3}', '', tweet_string)
    tweet_string = re.sub(HASHTAG_REGEX + '…', '', tweet_string)
    hashtags = re.findall(HASHTAG_REGEX, tweet_string)
    hashtag_list = [clean_hashtag(hashtag) for hashtag in hashtags]
    return hashtag_list


def is_award_hashtag(hashtag_string: str) -> bool:
    """
    this is the only hardcoding of strings in the HashtagParser pipeline
    :param hashtag_string: lowercase hashtag without the preceding # symbol
    :return: true if the string starts with "best" or ends with "award"; otherwise, false
    """
    return hashtag_string.startswith('best') or hashtag_string.endswith('award')


def clean_award_regex(string_list: List[str]) -> List[str]:
    # best X at the golden globes --> best X
    string_list = [r.split(' at ')[0] for r in string_list]
    # best X for their role in Y --> best X
    # string_list = [r.split(' for ')[0] for r in string_list]
    # best X at / best X for --> best X
    for ix, string in enumerate(string_list):
        if ' and ' in string:
            string_list[ix] = ''
        elif string.endswith(' at'):
            # string_list[ix] = string[:-3]
            string_list[ix] = ''
        elif string.endswith(' for'):
            # string_list[ix] = string[:-4]
            string_list[ix] = ''
        elif string.endswith(' a') or string.endswith(' an') or string.endswith(' or') or string.endswith(' and'):
            string_list[ix] = ''
        elif string.startswith('a ') or string.startswith('an '):
            string_list[ix] = ''
    return [string for string in string_list if len(string)]


def split_award_regex(string: str) -> Set[str]:
    string_split = clean_tweet(string, remove_symbols=True).split()
    temp_set = set([chunk for chunk in string_split if chunk not in ['in', 'a', 'an', 'or', 'and', 'the', 'for', 'at', 'of', '']])
    if len(temp_set) < 2:
        return set()

    return temp_set.difference({'best', 'award'})