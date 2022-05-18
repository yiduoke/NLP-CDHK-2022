import re
import json
from collections import Counter
from Levenshtein import distance
from typing import List, Dict
from tqdm import tqdm

from string_utils import parse_hashtags_from_tweet, parse_PascalCase_to_representations
from string_utils import is_ascii, clean_tweet, is_award_hashtag, tweet_to_alphanumeric
from string_utils import clean_award_regex, split_award_regex


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
        # initialization boolean
        self.is_initialized = False

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
        self.all_hashtags = []

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
        if self.attempt_hashtag_linking(hashtag, frequency, abbreviations, chunks):
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

    def add_child_to_parent(self, hashtag, frequency, abbreviations, parent):
        """
        TODO
        :param hashtag:
        :param abbreviations:
        :param parent:
        :return:
        """
        self.hashtag_to_parent[hashtag] = parent
        self.general_hashtags[parent]['children'].append(hashtag)
        self.general_hashtags[parent]['frequency'] += frequency
        for abbr in abbreviations:
            if abbr not in self.general_hashtags[parent]['abbreviations']:
                self.general_hashtags[parent]['abbreviations'].append(abbr)

    def attempt_hashtag_linking(self, hashtag, frequency, abbreviations, chunks):
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
                        self.general_hashtags[parent]['frequency'] += self.general_hashtags[p]['frequency']
                        for c in p_children:
                            self.hashtag_to_parent[c] = parent
            else:
                parent = self.hashtag_to_parent[close_tags[0]]
                self.add_child_to_parent(hashtag, frequency, abbreviations, parent)
            return False

        # check if a hashtag is a ***subset*** of more popular hashtags
        #   - ignore if other hashtags are significantly more popular
        #   - (very helpful for names of actors/actresses -- #GeorgeClooney vs. #George)
        superset_hashtags = [p for t, p in self.hashtag_to_parent.items() if all([chunk in t for chunk in chunks])]
        superset_hashtags = list(set(superset_hashtags + [p for t, p in self.hashtag_to_parent.items() if hashtag in t]))
        if len(superset_hashtags):
            if len(superset_hashtags) == 1:
                parent = superset_hashtags[0]
                self.add_child_to_parent(hashtag, frequency, abbreviations, parent)
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
                self.add_child_to_parent(hashtag, frequency, abbreviations, parent)
            else:
                # if superset of multiple hashtags, then don't group or reject the hashtag
                #   - example: #accesshollywood --> #access, #hollywood
                pass

        # all checks were passed!
        return True

    def resolve_abbreviated_hashtags(self, abbreviated_hashtags):
        for tag, freq in abbreviated_hashtags:
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
                self.add_child_to_parent(tag, freq, [tag_copy], parent)
                children_references = {k: v for k, v in self.general_hashtags.items() if tag_copy in v['split']}
                for k, v in children_references.items():
                    self.add_child_to_parent(k, v['frequency'], [], parent)
                    for child in v['children']:
                        self.add_child_to_parent(child, 0, [], parent)

    def finalize(self):
        """
        Remove extraneous hashtags
        TODO: write out a better docstring
        :return:
        """
        all_parent_hashtags = list(set(self.hashtag_to_parent.values()))
        del_hashtags = []
        for candidate_hashtag in self.general_hashtags:
            if candidate_hashtag not in all_parent_hashtags:
                del_hashtags.append(candidate_hashtag)

        for hashtag in del_hashtags:
            del self.general_hashtags[hashtag]

        self.all_hashtags = list(set(self.hashtag_to_parent.keys()))




class HashtagParser(object):
    def __init__(self, data=None, hashtag_parser_config_path='hashtag_parser_config.json',
                 award_word_config_path='award_word_config.json'):

        # ---------- internal data structs ----------
        self.raw_hashtag_counter = Counter()

        self.hashtag_total_count = 0
        self.uncased_to_cased = None
        self.uncased_ordered = None
        self.hashtags = HashtagLogger()
        self.award_name_to_hashtags = None

        # ---------- Award words config ----------
        with open(award_word_config_path) as f:
            award_word_config = json.load(f)

        # awards might start with "best"
        self.awards_might_start_with = award_word_config['awards_might_start_with']
        # awards might end with "award"
        self.awards_might_end_with = award_word_config['awards_might_end_with']
        # award-related words = both of the above
        self.award_related_words = self.awards_might_start_with + self.awards_might_end_with

        # award *winner*-related strings
        #    award suffix phrases: phrases *after* an award name that might indicate winning
        #      <award_name> suffix phrase <recipient> (e.g. <best hair> goes to <walker demel>)
        #    award prefix phrases: phrases *before* an award name that might indicate winning
        #      <recipient> prefix phrase <award_name> (e.g. <walker demel> takes home <best hair>)
        self.award_suffix_phrases = award_word_config['award_suffix_phrases']
        self.award_prefix_phrases = award_word_config['award_prefix_phrases']

        # expand prefix phrase list with reasonable modifiers: <recipient> prefix phrase + modifier <award_name>
        #   (e.g. <walker demel> takes home *the award for* <best hair>)
        temp_prefix_phrases = []
        for prefix_modifier in award_word_config['award_prefix_modifiers']:
            temp_prefix_phrases.extend([phrase + prefix_modifier for phrase in self.award_suffix_phrases])
        self.award_prefix_phrases = temp_prefix_phrases + self.award_prefix_phrases

        # regex for awards might start/end with (current assumption: only one string in each)
        self.award_suffix_regex = r'(' + self.awards_might_start_with[0] + r' [\w \-,/]+) '
        self.award_prefix_starts_with_regex = r' ' + self.award_suffix_regex
        self.award_prefix_ends_with_regex = r' ((?:[\w\-,/]| \w\. | )+ ' + self.awards_might_end_with[0] + r') '


        # ---------- Hashtag filtering config ----------
        with open(hashtag_parser_config_path) as f:
            parser_config = json.load(f)

        # stopwords: hashtags that appear with more than 1% of all hashtags
        self.stopword_proportion_threshold = float(parser_config['stopword_proportion_threshold'])

        # frequent: popular hashtags that appear occur more times than the "frequent hashtag threshold" (100)
        # infrequent: not-so-popular hashtags but appear more times than the "infrequent hashtag threshold" (10)
        self.frequent_hashtag_threshold = int(parser_config['frequent_hashtag_threshold'])
        self.infrequent_hashtag_threshold = int(parser_config['infrequent_hashtag_threshold'])

        # params related to keeping frequent hashtags
        #   - a frequent hashtag must be at least 4 characters long to keep
        self.frequent_hashtag_len_min = int(parser_config['frequent_hashtag_len_min'])

        # params related to keeping infrequent hashtags
        #   - keep hashtags that are possible children of others if they occur at least 1/10 times parent occurrence
        #   - an infrequent hashtag must be at least 7 characters long to keep
        self.keep_hashtag_subset_ratio = int(parser_config['keep_hashtag_subset_ratio'])
        self.infrequent_hashtag_len_min = int(parser_config['infrequent_hashtag_len_min'])

        # params for tracking natural language utterances related to hashtags
        #   - a frequent utterance appears at least 100 times (just like hashtag threshold for "frequent")
        #   - if the utterance appears more than 10x or less than 1/10x the hashtag occurrence, ignore it
        self.frequent_utterance_threshold = int(parser_config['frequent_utterance_threshold'])
        self.keep_hashtag_nl_ratio = int(parser_config['keep_hashtag_nl_ratio'])

        # params for tracking candidate award names via win-related strings
        self.award_winner_candidate_threshold_capture = int(parser_config['award_winner_candidate_threshold_capture'])
        self.award_winner_candidate_threshold_filter = int(parser_config['award_winner_candidate_threshold_filter'])

        if data is not None:
            self.initialize_hashtag_counter(data)
            self.initialize_uncased_mappings()

    def initialize_hashtag_counter(self, data: List[Dict]) -> None:
        """
        Initial storage of all hashtags in dataset.
        :param data: List[Dict] of tweet instances, where Dict must have key='text'
        :return: None - update self.hashtag_counter
        """
        for line in tqdm(data, desc='Counting all hashtags in the corpus'):
            tweet = line['text']
            self.raw_hashtag_counter.update(parse_hashtags_from_tweet(tweet))

    def initialize_uncased_mappings(self):
        """
        Initializes an "uncased_to_cased" counter which maps lower-case hashtags to cased variants found in the data
            self.uncased_to_cased = {'lowercasehashtag':
                                        {'PascalCaseHashtag': <frequency>, 'UPPERCASEHASHTAG': <frequency>, ... }
                                     , ...}

            example: 'grandbudapest': {'grandbudapest': 7, 'GrandBudapest': 17, 'GRANDBUDAPEST': 1, 'Grandbudapest': 1}
        :return: None, instead store mapping in self.uncased_ordered:
            sorted dictionary of aggregated lower-case hashtags (sorted by hashtag frequency sum over all casings)
        """
        uncased_hashtags = list(set([tag.lower() for tag in self.raw_hashtag_counter.keys()]))
        uncased_counter = {tag: 0 for tag in uncased_hashtags}
        self.uncased_to_cased = {tag: {} for tag in uncased_hashtags}
        for tag, freq in self.raw_hashtag_counter.items():
            uncased_tag = tag.lower()
            uncased_counter[uncased_tag] += freq
            self.hashtag_total_count += freq
            self.uncased_to_cased[uncased_tag][tag] = freq
        self.uncased_ordered = dict(sorted(uncased_counter.items(), key=lambda item: item[1], reverse=True))

    def get_candidate_hashtags(self, verbose: bool = False):
        """
        Generate a unique set of hashtags which are maybe important and might map to utterances outside of hashtags
            + hashtag filtering:
                - store all hashtags that start with "best" or end with "award" (only hardcoding used)
                - ignore hashtags that are effectively "stopwords", adding no useful information (#GoldenGlobes)
                - ignore hashtags if too infrequent (hardcoded in __init__ to 10 occurrences)
                - ignore hashtags if too short (hardcoded, threshold is conditioned on how popular the hashtag is)
            + heuristics for combining concepts/entities:
                (handled by HashtagLogger)
        :param verbose: if True, print out general (i.e. not award-related) hashtags after filtering and linking
        :return: None (instead, initialize self.hashtags)
        """
        # map hashtags (with collision) to lowercase - casing doesn't change semantics - then sort by frequency
        if self.uncased_ordered is None:
            self.initialize_uncased_mappings()

        # clean hashtag set: since our mapping above is sorted by frequency, we sequentially encounter:
        #   - stopwords -- greater than 1% of all hashtag occurrences -- reject these hashtags
        #   - popular hashtags -- at least 100 occurrences -- less strict rules for filtering/rejection
        #   - infrequent hashtags -- at least 10 occurrences -- strict rules for filtering/rejection
        abbreviated_hashtags = []
        for tag, freq in self.uncased_ordered.items():
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
                abbreviated_hashtags.append([tag, freq])
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
        self.hashtags.finalize()
        self.hashtags.is_initialized = True
        if verbose:
            for k, v in self.hashtags.general_hashtags.items():
                print('Concept hashtag:', k, '\n\tlinked children hashtags:', v['children'])

    def parse_award_names(self, data: List[Dict], verbose: bool = True) -> List[str]:
        """
        Leverages hashtag co-occurrence to generate a probable list of award names.

        :param data: List[Dict], where Dict must have key='text'
        :return: list of best-guess award names from the data.
        """
        if not self.hashtags.is_initialized:
            self.get_candidate_hashtags()

        # we want natural language (i.e. not hashtag) candidates for award names mined from tweets related to awards
        #   - lowercase the tweets
        #   - remove twitter account mentions (don't yet have a way of linking/interpreting them)
        #   - ignore tweets without "best" or "award"
        #       (set in 'award_word_config.json' --> saved to self.award_related_words)
        # separate cleaned + filtered tweets into "retweets" and "non-retweet" lists
        tweets_filtered_list = []
        retweets_filtered_list = []
        for line in tqdm(data, desc="Filtering tweets for award-related words"):
            tweet = line['text'].lower()
            tweet = clean_tweet(tweet, remove_hashtags=False)

            if not any([award_word in tweet for award_word in self.award_related_words]):
                continue

            if tweet.startswith('"') or tweet.startswith('rt '):
                retweets_filtered_list.append(' ' + tweet + ' ')
            else:
                tweets_filtered_list.append(' ' + tweet + ' ')

        # enforce uniqueness of (non-retweet) tweets via set cast
        tweets_filtered_list = list(set(tweets_filtered_list))

        # get unfiltered list of candidate award names via win-related regular expressions
        award_phrase_counter = Counter()
        award_hashtags = {}
        for tweet in tqdm(tweets_filtered_list + retweets_filtered_list,
                          desc="Searching for award name candidates using win-related phrases"):
            regex_found, award_regex = False, []

            # search for award-winner suffix-related strings
            for verb_phrase in self.award_suffix_phrases:
                award_regex = re.findall(self.award_suffix_regex + verb_phrase, tweet)
                if len(award_regex):
                    award_regex = clean_award_regex(award_regex)
                    award_phrase_counter.update(award_regex)
                    regex_found = True
                    break

            # search for award-winner prefix-related strings (if suffix-related search failed)
            if not regex_found:
                for verb_phrase in self.award_prefix_phrases:
                    award_regex = re.findall(verb_phrase + self.award_prefix_starts_with_regex, tweet)
                    if len(award_regex):
                        award_regex = clean_award_regex(award_regex)
                        award_phrase_counter.update(award_regex)
                        regex_found = True
                        break
                    else:
                        award_regex = re.findall(verb_phrase + self.award_prefix_ends_with_regex, tweet)
                        if len(award_regex):
                            award_regex = clean_award_regex(award_regex)
                            award_phrase_counter.update(award_regex)
                            regex_found = True
                            break

            # if either step succeeded, then get co-occurring hashtags
            if regex_found:
                hashtags = parse_hashtags_from_tweet(tweet)
                hashtags = [self.hashtags.hashtag_to_parent[tag] for tag in hashtags if tag in self.hashtags.all_hashtags]
                hashtags = list(set(hashtags))
                for award in award_regex:
                    if award not in award_hashtags:
                        award_hashtags[award] = Counter()
                    award_hashtags[award].update(hashtags)

        # filter through candidate award strings
        award_counter = sorted(award_phrase_counter.items(), key=lambda item: item[1], reverse=True)
        award_counter = [list(tup) for tup in award_counter]
        kept_awards = []
        for ix, (k, freq) in enumerate(tqdm(award_counter, desc="Performing initial filtering and linking of potential award names")):
            # sorted list --> break will skip anything with less than 10 occurrences
            # this initial filtering is more relaxed, permitting consolidation of award names in this first step
            if freq < self.award_winner_candidate_threshold_capture:
                continue
            # ignore awards with our stopword chunks in them, e.g. "golden"
            if any([' ' + stop + ' ' in k for stop in self.hashtags.stopword_chunks]):
                continue

            # regex might erroneously capture a trailing comma or period -- if true, remove it
            if k.endswith(',') or k.endswith('.'):
                k = k[:-1]

            # check if award string's words are mostly stop-words -- if so, ignore
            k_set = split_award_regex(k)
            if len(k_set) == 0:
                continue

            # check if award string is a punctuation-insensitive match to already added award candidates -- if so, ignore
            k_reduce = tweet_to_alphanumeric(k)
            reject = False
            for jx, (k_, _) in enumerate(kept_awards):
                k_set_ = split_award_regex(k_)
                if tweet_to_alphanumeric(k_) == k_reduce or k_set_ == k_set:
                    reject = True
                    kept_awards[jx][1] += freq
                    award_hashtags[k_] += award_hashtags[k]
                    break

            # if not rejection boolean, then everything passed! add the candidate
            if not reject:
                kept_awards.append([k, freq])

        # re-sort on frequency of candidate award strings
        #   (since we might have perturbed frequency ordering by linking awards above)
        kept_awards = sorted(kept_awards, key=lambda item: item[1], reverse=True)
        filtered_award_hashtags = {}
        for k, _ in kept_awards:
            temp_hashtags = {}
            children_to_parent = {}
            temp_award_hashtags = sorted(award_hashtags[k].items(), key=lambda item: item[1], reverse=True)
            for tag, freq in temp_award_hashtags:
                # check if hashtag is a child of another hashtag
                if tag in children_to_parent:
                    parent = children_to_parent[tag]
                    temp_hashtags[parent] += freq
                    continue
                # otherwise, keep it
                temp_hashtags[tag] = freq
                for child in self.hashtags.general_hashtags[tag]['children']:
                    children_to_parent[child] = tag
            filtered_award_hashtags[k] = Counter(temp_hashtags)

        temp_kept = []
        acceptable_set_differences = []
        for ix, (k, freq) in enumerate(tqdm(kept_awards, desc="Performing final filtering and linking of award names")):
            # filter on a more aggressive occurrence requirement for the award string (100 occurrences)
            if freq < self.award_winner_candidate_threshold_filter:
                continue
            k_set = split_award_regex(k)
            k_hash = filtered_award_hashtags[k]
            reject = False
            swap = False
            all_subset_other = []
            if not len(k_hash):
                reject = True
            else:
                # if two awards are similar enough, check if they have similar co-occurring hashtags
                top_hash = max(k_hash, key=k_hash.get)

                # reject if
                #   1. the award string has limited co-occurring hashtags
                #   2. the award string co-occurs with top hashtag too much (likely noise, then!)
                #   3. the top hashtag doesn't appear at least 250 times in full corpus (likely noise as well)
                #   4. the award string appears less than 250 times and it's top hashtag co-occurs less than 10 times
                if k_hash[top_hash] == 1 or k_hash[top_hash] >= freq * 0.9:
                    continue
                if self.hashtags.general_hashtags[top_hash]['frequency'] < 250:
                    continue
                if freq < 250 and k_hash[top_hash] < 10:
                    continue

                # track award name vs. other already added award names
                for k_other, _ in temp_kept:
                    k_set_other = split_award_regex(k_other)
                    k_hash_other = filtered_award_hashtags[k_other]

                    top_hash_other = max(k_hash_other, key=k_hash_other.get)
                    if top_hash_other == top_hash or top_hash in k_hash_other or top_hash_other in k_hash:
                        # true subset of other
                        if not len(k_set.difference(k_set_other)):
                            if k_set.difference(k_set_other) not in acceptable_set_differences:
                                all_subset_other.append(k_other)
                                reject = True
                        # subset of other + not an acceptable difference
                        elif not len(k_set_other.difference(k_set)):
                            if k_set.difference(k_set_other) not in acceptable_set_differences:
                                swap = k_other
                                reject = True
                                break
                    else:
                        # if hashtag sets are not related, then this is a permissible alteration of the award set
                        if not len(k_set_other.difference(k_set)):
                            acceptable_set_differences.append(k_set.difference(k_set_other))

            if not reject:
                temp_kept.append([k, freq])
            elif swap:
                # TODO: comment description of swapping procedure
                for ix, (k_other, freq_other) in enumerate(temp_kept):
                    if k_other == swap:
                        temp_kept[ix] = [k, freq_other + freq]
                        filtered_award_hashtags[k] += filtered_award_hashtags[k_other]
            else:
                if len(all_subset_other) == 1:
                    for jx, (k_other, freq_other) in enumerate(temp_kept):
                        if k_other == all_subset_other[0]:
                            temp_kept[jx][1] += freq
                            filtered_award_hashtags[k_other] += filtered_award_hashtags[k]
                            break

        if verbose:
            print('internal use: award name strings + hashtag info')
            print()
            for k, v in temp_kept:
                top_hash = max(filtered_award_hashtags[k], key=filtered_award_hashtags[k].get)
                top_hash_global_info = self.hashtags.general_hashtags[top_hash]
                print('\t' + '-'*30)
                print('\taward name:', k)
                print('\t\t.............. award name utterance frequency in corpus:', v)
                print('\t\t... top co-occurring hashtags with award name utterance:', filtered_award_hashtags[k])
                print('\t\t............... global corpus statistics on top hashtag:', top_hash)
                print('\t\t          \t...  global frequency:', top_hash_global_info['frequency'])
                print('\t\t          \t... children hashtags:', top_hash_global_info['children'])
        award_name_list = [tup[0] for tup in temp_kept]
        self.award_name_to_hashtags = {k: filtered_award_hashtags[k] for k in award_name_list}

        return award_name_list

    def parse_hashtag_concepts(self, data: List[Dict]):
        """
        TODO

        :param data: List[Dict], where Dict must have key='text'
        :return: TODO
        """
        if not self.hashtags.is_initialized:
            self.get_candidate_hashtags()

        # we want "natural language" matches over a diverse set of tweets
        #   - lowercase the tweets
        #   - remove twitter account mentions (don't yet have a way of linking/interpreting them)
        tweets_filtered = []
        retweets_filtered = []
        for line in data:
            tweet = line['text'].lower()
            # # ignore tweets which don't include "best" or "award" -- significant speedup
            # if 'best' not in tweet and 'award' not in tweet:
            #     continue
            tweet = clean_tweet(tweet, remove_hashtags=False)
            if tweet.startswith('"') or tweet.startswith('rt '):
                retweets_filtered.append(' ' + tweet + ' ')
            else:
                tweets_filtered.append(' ' + tweet + ' ')

        # enforce uniqueness of tweets and join with ~ as a special token --> can search on regex without iterating
        tweets_filtered_list = list(set(tweets_filtered))
        # retweets_filtered_list = list(set(retweets_filtered))
        retweets_filtered_list = retweets_filtered
        tweets_full_reduce = '~'.join([tweet_to_alphanumeric(t) for t in tweets_filtered])
        tweets_filtered = '~'.join(tweets_filtered_list)

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
        print("","","",hash_to_award.keys())
        all_hash_to_award_keys = []

        def recursively_get_all_keys(dictionary, running_list):
            for key, value in hash_to_award:
                if type(value) != dict:
                    return running_list
                else:
                    for key in value:
                        recursively_get_all_keys(value, running_list.append(value))

        # recursively_get_all_keys(hash_to_award, [])
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

        for k, v in tqdm(hash_to_concept.items()):
            best_counter = {}
            for _, best_v in bests_clean:
                best_str = best_v['utterance']
                best_counter[best_str] = 0

            for tweet in tweets_filtered_list:
                tweet = tweet.lower()
                if not any([utt in tweet for utt in v['utterance_forms']]) and v['hashtag'].lower().replace('#', '') not in tweet:
                    continue

                for _, best_v in bests_clean:
                    best_utt = best_v['utterance']
                    if any([best_str in tweet for best_str in best_v['utterance_forms']]):
                        best_counter[best_utt] += 1

            best_counter = {k: v for k, v in sorted(best_counter.items(), key=lambda item: item[1], reverse=True) if v != 0}
            hash_to_concept[k]['bests'] = best_counter

        print('\n' + '---' * 20)
        print('general hashtags\n')
        for k, v in hash_to_concept.items():
            print('%s (total uses: %i); hashtag: %s (total uses: %i)' %
                  (v['utterance'], v['utterance_total'], v['hashtag'], v['hashtag_total']))
            print('\tutterances:', v['utterance_forms'])
            print('\thashtags:', v['hashtag_forms'])
            print('\tbests:', v['bests'])
            print()

        return hash_to_concept


