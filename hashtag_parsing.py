import re
from collections import Counter
from Levenshtein import distance
from typing import List, Dict
from tqdm import tqdm

from string_utils import parse_hashtags_from_tweet, parse_PascalCase_to_representations
from string_utils import is_ascii, clean_tweet, is_award_hashtag, tweet_to_alphanumeric


class HashtagLogger(object):
    def __init__(self):
        """
        Stores and links/coalesces hashtags (stopwords, concepts/entities, awards)
            - abbreviation linking: #OITNB <--> #OrangeIsTheNewBlack
            - edit distance linking: #KeiraKnightley <--> #KeiraKnigthley, #KieraKnightly, #KieraKnightley, ...
            - subset-hashtag filtering: #AmalClooney, #GeorgeClooney --> ignore #Clooney
            - superset-hashtag linking: #Selma <--> #SelmaMovie, #SelmaTheMovie, #TeamSelma, #Selma50, #SelmaIsNow
                - but *not* related to #SelmaHayek, a misspelling of #SalmaHayek
        """
        # stopword data
        self.stopword_hashtags = []
        self.stopword_chunks = []
        self.stopword_abbreviations = []

        # general hashtags and award hashtags: Dicts of:
        #   str: lowercase hashtag --> {
        #       'frequency' - int: frequency count
        #       'children' - List[str]: lowercase hashtags that are related but less frequent than the parent hashtag
        #       'abbreviations' - List[str]: abbreviations for hashtag based on parent + children
        #       'split' - List[str]: (an attempted) parse of the PascalCase casing of the hashtag into word chunks
        self.general_hashtags = {}
        self.award_hashtags = {}

        # hashtag to parent -- dict that links "children" hashtags to parent hashtags
        #   e.g. #Selma50 --> #Selma; #Selma --> #Selma
        self.hashtag_to_parent = {}

    def add_stopword_hashtag(self, hashtag, abbreviations, chunks):
        self.stopword_hashtags.append(hashtag)
        self.stopword_abbreviations.extend(abbreviations)
        self.stopword_chunks.extend(chunks)

    def add_award_hashtag(self, hashtag, frequency, abbreviations, chunks):
        self.award_hashtags[hashtag] = {
            'frequency': frequency, 'children': [], 'abbreviations': abbreviations, 'split': chunks
        }
        # self.hashtag_to_parent[hashtag] = hashtag

    def add_general_hashtag(self, hashtag, frequency, abbreviations, chunks):
        if self.attempt_hashtag_linking(hashtag, abbreviations, chunks):
            self.general_hashtags[hashtag] = {
                'frequency': frequency, 'children': [], 'abbreviations': abbreviations, 'split': chunks
            }
            self.hashtag_to_parent[hashtag] = hashtag

    def get_edit_distance_rule(self, hashtag):
        """
        return hardcode for Levenshtein distance based on hashtag length
        :param hashtag:
        :return:
        """
        if len(hashtag) < 7:
            return 1
        elif len(hashtag) < 13:
            return 2
        else:
            return 3

    def add_child_to_parent(self, hashtag, abbreviations, parent):
        """
        TODO
        :param hashtag:
        :param abbreviations:
        :param parent:
        :return:
        """
        self.hashtag_to_parent[hashtag] = parent
        self.general_hashtags[parent]['children'].append(hashtag)
        for abbr in abbreviations:
            if abbr not in self.general_hashtags[parent]['abbreviations']:
                self.general_hashtags[parent]['abbreviations'].append(abbr)

    def attempt_hashtag_linking(self, hashtag, abbreviations, chunks):
        # ignore if hashtag has small edit distance to another (dependent on hashtag length)
        edit_distance = self.get_edit_distance_rule(hashtag)
        close_tags = list(set([p for t, p in self.hashtag_to_parent.items() if distance(hashtag, t) <= edit_distance]))
        close_filtered = []
        for p in close_tags:
            if any([abbr in self.general_hashtags[p]['abbreviations'] for abbr in abbreviations]):
                close_filtered.append(p)

        if len(close_filtered):
            if len(close_filtered) > 1:
                # resolve to highest frequency parent -- a "triangulated misspelling" case
                #   - example: #keiraknightly maps to both #kieraknightly and #keiraknightley
                parent = close_filtered[0]
                max_freq = self.general_hashtags[parent]['frequency']
                for p in close_filtered[1:]:
                    p_freq = self.general_hashtags[p]['frequency']
                    if p_freq > max_freq:
                        max_freq = p_freq
                        parent = p
                for p in close_filtered:
                    if p != parent:
                        # coalesce the multiple parents + their children
                        p_children = self.general_hashtags[p]['children'] + [p]
                        self.general_hashtags[parent]['children'].extend(p_children)
                        for c in p_children:
                            self.hashtag_to_parent[c] = parent
            else:
                parent = self.hashtag_to_parent[close_tags[0]]
                self.add_child_to_parent(hashtag, abbreviations, parent)
            return False

        # check if a hashtag is a ***subset*** of more popular hashtags
        #   - ignore if other hashtags are significantly more popular
        #   - (very helpful for names of actors/actresses -- #GeorgeClooney vs. #George)
        superset_hashtags = [p for t, p in self.hashtag_to_parent.items() if all([chunk in t for chunk in chunks])]
        superset_hashtags = list(set(superset_hashtags + [p for t, p in self.hashtag_to_parent.items() if hashtag in t]))
        if len(superset_hashtags):
            if len(superset_hashtags) == 1:
                parent = superset_hashtags[0]
                self.add_child_to_parent(hashtag, abbreviations, parent)
                return False
            else:
                # throw out hashtag if more than one superset hashtag -- hashtags like #George
                return False

        # check if a hashtag is a ***superset*** of a more popular hashtag
        #   - #SelmaMovie --> #Selma
        subset_hashtags = [t for t, v in self.general_hashtags.items() if all([chunk in hashtag for chunk in v['split']])]
        subset_hashtags = list(set(subset_hashtags + [p for t, p in self.hashtag_to_parent.items() if t in hashtag]))
        if len(subset_hashtags):
            if len(subset_hashtags) == 1:
                # if the hashtag is a subset of only one hashtag, then group them together
                parent = subset_hashtags[0]
                self.add_child_to_parent(hashtag, abbreviations, parent)
            else:
                # if superset of multiple hashtags, then don't group or reject the hashtag
                #   - example: #accesshollywood --> #access, #hollywood
                pass

        # all checks were passed!
        return True

    def resolve_abbreviated_hashtags(self, abbreviated_hashtags):
        for tag in abbreviated_hashtags:
            # fix stopword abbreviations like RDJGG (robert downey jr. golden globes)
            tag_copy = tag[:]
            for abbr in self.stopword_abbreviations:
                tag_copy = tag_copy.replace(abbr, '')
            # ignore if (possibly altered) abbreviation is too short
            if len(tag_copy) < 3:
                continue
            candidate_references = [k for k, v in self.general_hashtags.items() if tag_copy in v['abbreviations'] and k != tag_copy]
            if len(candidate_references) == 1:
                parent = candidate_references[0]
                self.add_child_to_parent(tag, [tag_copy], parent)
                children_references = {k: v for k, v in self.general_hashtags.items() if tag_copy in v['split']}
                for k, v in children_references.items():
                    self.add_child_to_parent(k, [], parent)
                    for child in v['children']:
                        self.add_child_to_parent(child, [], parent)


class HashtagParser(object):
    def __init__(self, data=None):
        # ---------- internal data structs ----------
        self.raw_hashtag_counter = Counter()

        self.hashtag_total_count = 0
        self.uncased_to_cased = None
        self.hashtags = HashtagLogger()

        # ---------- Hardcoded config ----------
        self.award_words_hardcoded = ['best', 'award']

        # stopwords: hashtags that appear with more than 1% of all hashtags
        self.stopword_proportion_threshold = 0.01

        # frequent: popular hashtags that appear occur more times than the "frequent hashtag threshold"
        # infrequent: not-so-popular hashtags but appear more times than the "infrequent hashtag threshold"
        self.frequent_hashtag_threshold = 100
        self.infrequent_hashtag_threshold = 10

        # params related to keeping frequent hashtags
        self.frequent_hashtag_len_min = 4

        # params related to keeping infrequent hashtags
        self.keep_hashtag_subset_ratio = 10
        self.infrequent_hashtag_len_min = 7

        # params for tracking natural language utterances related to hashtags
        self.frequent_utterance_threshold = 100
        self.keep_hashtag_nl_ratio = 10

        if data is not None:
            self.initialize_hashtag_counter(data)

    def initialize_hashtag_counter(self, data: List[Dict]) -> None:
        """
        Initial storage of all hashtags in dataset.
        :param data: List[Dict] of tweet instances, where Dict must have key='text'
        :return: None - update self.hashtag_counter
        """
        for line in data:
            tweet = line['text']
            self.raw_hashtag_counter.update(parse_hashtags_from_tweet(tweet))

    def initialize_uncased_mappings(self):
        """
        Initializes an "uncased_to_cased" counter which maps lower-case hashtags to cased variants found in the data
            self.uncased_to_cased = {'lowercasehashtag':
                                        {'PascalCaseHashtag': <frequency>, 'UPPERCASEHASHTAG': <frequency>, ... }
                                     , ...}

            example: 'grandbudapest': {'grandbudapest': 7, 'GrandBudapest': 17, 'GRANDBUDAPEST': 1, 'Grandbudapest': 1}
        :return: sorted dictionary of aggregated lower-case hashtags (sorted by hashtag frequency sum over all casings)
        """
        uncased_hashtags = list(set([tag.lower() for tag in self.raw_hashtag_counter.keys()]))
        uncased_counter = {tag: 0 for tag in uncased_hashtags}
        self.uncased_to_cased = {tag: {} for tag in uncased_hashtags}
        for tag, freq in self.raw_hashtag_counter.items():
            uncased_tag = tag.lower()
            uncased_counter[uncased_tag] += freq
            self.hashtag_total_count += freq
            self.uncased_to_cased[uncased_tag][tag] = freq
        return dict(sorted(uncased_counter.items(), key=lambda item: item[1], reverse=True))

    def get_candidate_hashtags(self):
        """
        Return a unique set of hashtags which are maybe important and might map to utterances outside of hashtags
            + hashtag filtering:
                - store all hashtags that start with "best" or end with "award" (only hardcoding used)
                - ignore hashtags that are effectively "stopwords", adding no useful information (#GoldenGlobes)
                - ignore hashtags if too infrequent (hardcoded in __init__ to 10 occurrences)
                - ignore hashtags if too short (hardcoded, threshold is conditioned on how popular the hashtag is)
            + heuristics for combining concepts/entities:
                (handled by HashtagLogger)

        :return: List[str] - where each str is a hashtag without the preceding '#' and is lower-cased.
        """
        # map hashtags (with collision) to lowercase - casing doesn't change semantics - then sort by frequency
        uncased_sorted = self.initialize_uncased_mappings()

        # clean hashtag set: since our mapping above is sorted by frequency, we sequentially encounter:
        #   - stopwords -- greater than 1% of all hashtag occurrences -- reject these hashtags
        #   - popular hashtags -- at least 100 occurrences -- less strict rules for filtering/rejection
        #   - infrequent hashtags -- at least 10 occurrences -- strict rules for filtering/rejection
        abbreviated_hashtags = []
        for tag, freq in uncased_sorted.items():
            # get most frequent capitalization of hashtag
            cased_tag = max(self.uncased_to_cased[tag], key=self.uncased_to_cased[tag].get)

            if cased_tag.isupper():
                # ignore if the hashtag is an abbreviation of our stopword hashtags
                if tag in self.hashtags.stopword_abbreviations:
                    continue
                # ignore if fails frequency threshold
                if freq < self.infrequent_hashtag_threshold:
                    continue
                # otherwise, pass on abbreviated hashtags for now - we'll try to resolve them later
                abbreviated_hashtags.append(tag)
                continue
            elif cased_tag.islower():
                # reject a hashtag if it mainly appears in lowercase form
                continue
            else:
                # tag has mixture of upper and lowercase (hopefully it's PascalCase) - parse it
                cased_chunks, cased_abbreviations = parse_PascalCase_to_representations(cased_tag)

            # stopword = anything that is at least 1% of all hashtags found
            if freq > self.hashtag_total_count * self.stopword_proportion_threshold:
                self.hashtags.add_stopword_hashtag(tag, cased_abbreviations, cased_chunks)
                continue

            # always include hashtags with our hardcodes (ends with "award" or starts with "best")
            if is_award_hashtag(tag):
                self.hashtags.add_award_hashtag(tag, freq, cased_abbreviations, cased_chunks)
                continue

            # --- universal rules for ignoring hashtags
            # ignore hashtags below the "infrequent hashtag threshold"
            if freq < self.infrequent_hashtag_threshold:
                continue
            # ignore hashtags with non-latin characters (i.e. rough filter for other languages)
            if not is_ascii(tag):
                continue

            # ignore hashtags related to stopwords:
            #   - reject if hashtag contains a stopword (or "chunk" of a stopword, e.g. Globes or Golden)
            #   - reject if hashtag is a substring of a stopwords
            #   - close Levenshtein distance to stopwords
            if any([chunk in self.hashtags.stopword_chunks for chunk in cased_chunks]):
                continue
            if any([tag in stopword or distance(tag, stopword) < 3 for stopword in self.hashtags.stopword_hashtags]):
                continue

            # --- case-based rules for ignoring hashtags (common vs. infrequent hashtags)
            if freq > self.frequent_hashtag_threshold:
                # for popular hashtags, ignore hashtags that are less than 4 chars long
                #   (lots of abbreviations/nonsense otherwise)
                if len(tag) < self.frequent_hashtag_len_min:
                    continue
            else:
                # for less popular hashtags, ignore hashtags that are less than 7 chars long
                if len(tag) < self.infrequent_hashtag_len_min:
                    continue

            # ---- All filters were passed! Check for similarity to already added hashtags in HashtagLogger
            #   if similarity checks pass, then hashtag gets added as new "parent" hashtag
            self.hashtags.add_general_hashtag(tag, freq, cased_abbreviations, cased_chunks)

        self.hashtags.resolve_abbreviated_hashtags(abbreviated_hashtags)

        for k, v in self.hashtags.general_hashtags.items():
            print(k, v['children'])

    def parse_hashtag_concepts(self, data: List[Dict]):
        """
        TODO

        :param data: List[Dict], where Dict must have key='text'
        :return: TODO
        """
        self.get_candidate_hashtags()

        # we want "natural language" matches over a diverse set of tweets
        #   - remove retweets and quote tweets (heuristic here: if important/true --> many unique tweets)
        #   - lowercase the tweets
        #   - remove twitter account mentions + hashtags from the tweets
        tweets_filtered = []
        for line in data:
            tweet = line['text'].lower()
            # skip on quote tweets (fancy unicode open quotation mark) and retweets
            #   heuristic here: if something is true/important then many people will tweet about it
            #   TODO: arguably things that are most important get retweeted the most?
            if tweet.startswith('\u201c@') or tweet.startswith('rt @'):
                continue
            if 'best' not in tweet and 'award' not in tweet:
                continue
            tweet = clean_tweet(tweet, remove_hashtags=False)
            tweets_filtered.append(tweet)

        # enforce uniqueness of tweets and join with ~ as a special token --> can search on regex without iterating
        tweets_filtered = list(set(tweets_filtered))
        tweets_full_reduce = '~'.join([tweet_to_alphanumeric(t) for t in tweets_filtered])
        tweets_filtered = ' ' + ' ~ '.join(tweets_filtered) + ' '

        # form a dictionary that maps from the text of a hashtag to related NL utterances, hashtags seen in data
        hash_to_concept = {}
        hash_to_award = {}
        print('looking for hashtags related to "best" and/or "award"')
        for k in tqdm(self.hashtags.award_hashtags):
            if k in tweets_full_reduce:
                tag_counter = {'#' + tag: freq for tag, freq in self.raw_hashtag_counter.items() if k == tag.lower()}
                tag_total = sum(tag_counter.values())

                # wonky regex --> allow any spacing/symbols between alphanumeric characters when searching
                #   - we want to resolve spacing/punctuation of mapping from hashtag to utterances in tweets
                #   - (hashtags are not always easily parsed from capitalization of tweet; also no punctuation allowed)
                nl_regex = r' (' + ''.join([char + r'[^\w~]*' for char in k[:-1]]) + k[-1] + r'\.?)[\.,\)\(\-"\'\!:;]? '
                nl_counter = Counter(re.findall(nl_regex, tweets_filtered))
                nl_total = sum(nl_counter.values())

                try:
                    nl_top_utterance = nl_counter.most_common(1)[0][0]
                except IndexError:
                    continue

                if nl_top_utterance.startswith('best of'):
                    continue
                if not nl_top_utterance.startswith('best ') and not nl_top_utterance.endswith(' award'):
                    continue

                tag_counter = dict(sorted(tag_counter.items(), key=lambda item: item[1], reverse=True))
                nl_counter = dict(sorted(nl_counter.items(), key=lambda item: item[1], reverse=True))

                hash_to_award[k] = {
                    'utterance': nl_top_utterance,
                    'utterance_forms': nl_counter,
                    'utterance_total': nl_total,
                    'hashtag': '#' + k,
                    'hashtag_forms': tag_counter,
                    'hashtag_total': tag_total
                }

        # post-process: sort by sum of total hashtags and utterance counts
        hash_to_award = {k: v for k, v in sorted(hash_to_award.items(), key=lambda item: item[1]['utterance_total'] + item[1]['hashtag_total'], reverse=True)}
        bests, awards = [], []
        chunk_counter = Counter()
        for k, v in hash_to_award.items():
            nl = v['utterance']
            if nl.startswith('best ') and v['utterance_total'] + v['hashtag_total'] > 50:
                nl_clean = ' ' + nl.replace(',', '').replace('-', '') + ' '
                for stopword in ['in', 'a', 'an', 'and', 'of', 'the']:
                    nl_clean = nl_clean.replace(' ' + stopword + ' ', ' ')
                nl_chunks = [chunk for chunk in nl_clean.split() if chunk != '']
                chunk_counter.update(nl_chunks)
                bests.append([set(nl_chunks), k, v])
            elif nl.endswith(' award'):
                awards.append([k, v])

        bests_clean = []
        bests_visited = []
        for root in [best for best in bests if len(best[0]) == 2]:
            bests_queue = [root]
            while len(bests_queue):
                chunks, k, v = bests_queue.pop(0)
                if k in bests_visited:
                    continue
                bests_visited.append(k)
                if any([chunk_counter[chunk] == 1 for chunk in chunks]):
                    continue

                chunk_concept = v
                for chunks_, k_, v_ in bests:
                    if k_ in bests_visited:
                        continue
                    if chunks == chunks_:
                        bests_visited.append(k_)
                        chunk_concept['utterance_total'] += v_['utterance_total']
                        chunk_concept['hashtag_total'] += v_['hashtag_total']
                        chunk_concept['utterance_forms'].update(v_['utterance_forms'])
                        chunk_concept['hashtag_forms'].update(v_['hashtag_forms'])
                    elif len(chunks_.difference(chunks)) == 1 and len(chunks_) - len(chunks) == 1:
                        bests_queue = [[chunks_, k_, v_]] + bests_queue

                utterances = chunk_concept['utterance_forms']
                hashtags = chunk_concept['hashtag_forms']
                chunk_concept['utterance'] = max(utterances, key=utterances.get)
                chunk_concept['hashtag'] = max(hashtags, key=hashtags.get)
                bests_clean.append([len(chunks), chunk_concept])

        print('\n' + '---' * 20)
        print('"best" in hashtag:')
        for t, v in bests_clean:
            print((t - 2) * '\t' + '%s (total uses: %i, %i unique patterns found); top hashtag: %s (total uses: %i, %i unique hashtags found)' %
                  (v['utterance'], v['utterance_total'], len(v['utterance_forms']), v['hashtag'],
                   v['hashtag_total'], len(v['hashtag_forms'])))
            print((t - 1) * '\t' + '- all utterances (and their counts):', v['utterance_forms'])

        print('\n' + '---' * 20)
        print('"award" in hashtag:')
        for k, v in hash_to_award.items():
            if 'award' not in k:
                continue
            print('\n' + 'award (?): ' + v['utterance'] + ' ............')
            print('%s (total uses: %i); hashtag: %s (total uses: %i)' %
                  (v['utterance'], v['utterance_total'], v['hashtag'], v['hashtag_total']))
            print('\tall matching utterances (and their counts):', v['utterance_forms'])
            print('\tall matching hashtags (and their counts):', v['hashtag_forms'])

        print('\n' + '---' * 20)
        print('looking for hashtags that co-occur with "best" and/or "award"')
        for k in tqdm(self.hashtags.general_hashtags):
            if k in tweets_full_reduce:
                v = self.hashtags.general_hashtags[k]
                tag_matches = [k] + v['children']  # TODO
                # gather hashtags that map to uncased (ambiguous) form; compute total # occurrences of uncased hashtag
                tag_counter = {'#' + tag: freq for tag, freq in self.raw_hashtag_counter.items() if tag.lower() in tag_matches}
                tag_total = sum(tag_counter.values())

                # wonky regex --> allow any spacing/symbols between alphanumeric characters when searching
                #   - we want to resolve spacing/punctuation of mapping from hashtag to utterances in tweets
                #   - (hashtags are not always easily parsed from capitalization of tweet; also no punctuation allowed)
                # nl_regex = ''.join([char + r'[^\w~]*' for char in k[:-1]]) + k[-1] + r'\.?[\.,)(-"\'!:;]? '

                nl_counter = Counter()
                for search_tag in tag_matches:
                    nl_regex = r' (' + ''.join([char + r'[^\w~]*' for char in k[:-1]]) + k[-1] + r'\.?)[\.,\)\(\-"\'\!:;]? '
                    nl_counter.update(re.findall(nl_regex, tweets_filtered))
                nl_total = sum(nl_counter.values())

                try:
                    nl_top_utterance = nl_counter.most_common(1)[0][0]
                except IndexError:
                    continue

                if nl_total < self.frequent_utterance_threshold and tag_total < self.frequent_hashtag_threshold:
                    continue
                if nl_total / tag_total > self.keep_hashtag_nl_ratio or tag_total / (nl_total + 1) > self.keep_hashtag_nl_ratio:
                    continue

                tag_counter = dict(sorted(tag_counter.items(), key=lambda item: item[1], reverse=True))
                nl_counter = dict(sorted(nl_counter.items(), key=lambda item: item[1], reverse=True))
                hash_to_concept[k] = {
                    'utterance': nl_top_utterance,
                    'utterance_forms': nl_counter,
                    'utterance_total': nl_total,
                    'hashtag': '#' + k,
                    'hashtag_forms': tag_counter,
                    'hashtag_total': tag_total
                }

        # post-process: sort by sum of total hashtags and utterance counts
        hash_to_concept = {k: v for k, v in sorted(hash_to_concept.items(), key=lambda item: item[1]['utterance_total'] + item[1]['hashtag_total'], reverse=True)}

        print('\n' + '---' * 20)
        print('general hashtags\n')
        for k, v in hash_to_concept.items():
            print('%s (total uses: %i); hashtag: %s (total uses: %i)' %
                  (v['utterance'], v['utterance_total'], v['hashtag'], v['hashtag_total']))
            print('\tutterances:', v['utterance_forms'])
            print('\thashtags:', v['hashtag_forms'])
            print()

        return hash_to_concept


