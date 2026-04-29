#!/usr/bin/env python3
def main():
    print("IN MAIN")
    print(BANNER.format(
        dict_count=len(CORRECTIONS),
        vocab_count=len(WORDS),
        token_count=TOTAL_WORDS
    ))
    ...
"""
╔══════════════════════════════════════════════════════╗
║        AutoCorrect Daemon v4.0 (Context-Aware)       ║
║    System-wide spell correction across all apps     ║
╚══════════════════════════════════════════════════════╝

INSTALL:
    pip install pynput

RUN:
    python AutoCorrect.py

TOGGLE ON/OFF:  Ctrl + Shift + A
QUIT:           Ctrl + C  (in terminal)

OVERVIEW:
- Uses edit-based candidate generation: deletion, transposition, replacement, insertion
- Uses word frequencies and bigram context to rank corrections
- Retroactively fixes common confusable words (e.g., their -> they're)
- Auto-capitalizes after sentence boundaries (.!?)
- Explicit typo dictionary still has highest priority
- Undo via double backspace

OPTIONAL:
- Put a file named "wordlist.txt" beside this script with one word per line to expand the vocabulary.
- Put a file named "corpus.txt" beside this script to improve word frequency and bigram ranking.
"""

import sys
import time
import threading
import os
import re
import json
import datetime
from collections import Counter, deque

try:
    from pynput.keyboard import Key, Controller, Listener
except ImportError:
    print("\n[ERROR] pynput is not installed.")
    print("Run:  pip install pynput\n")
    sys.exit(1)

# ─────────────────────────────────────────────────────
# GUI HOOKS & STATS
# ─────────────────────────────────────────────────────
GUI_WORDS_SCANNED = 0
GUI_UNKNOWN_TOKENS = 0
GUI_CORRECTIONS_APPLIED = 0
GUI_TOTAL_PROCESSING_TIME = 0.0

ENABLE_BIGRAMS = True
ENABLE_CAPITALIZATION = True
UNDO_WINDOW = 0.15
MASTER_ENABLE = True

# Persistence Files
STATS_FILE = "stats.json"
CUSTOM_DICT_FILE = "custom_dict.txt"
UNKNOWN_FILE = "unknown.txt"

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

def record_daily_stat(stat_key, val=1):
    stats = load_stats()
    today = datetime.date.today().isoformat()
    if today not in stats:
        stats[today] = {"scanned": 0, "corrected": 0, "unknown": 0, "time_ms": 0.0}
    stats[today][stat_key] += val
    save_stats(stats)

def log_unknown(word):
    if not os.path.exists(UNKNOWN_FILE):
        open(UNKNOWN_FILE, "w").close()
    with open(UNKNOWN_FILE, "a") as f:
        f.write(word + "\n")

def load_custom_dict():
    if os.path.exists(CUSTOM_DICT_FILE):
        with open(CUSTOM_DICT_FILE, "r") as f:
            for line in f:
                w = line.strip().lower()
                if w:
                    TRUSTED_WORDS.add(w)
                    WORDS[w] += 1000  # High frequency to ensure it gets picked

def add_custom_word(word):
    w = word.strip().lower()
    if not w: return False
    
    # Add to memory
    TRUSTED_WORDS.add(w)
    WORDS[w] += 1000
    
    # Save to file
    custom_words = set()
    if os.path.exists(CUSTOM_DICT_FILE):
        with open(CUSTOM_DICT_FILE, "r") as f:
            custom_words = set(f.read().splitlines())
    custom_words.add(w)
    with open(CUSTOM_DICT_FILE, "w") as f:
        f.write("\n".join(sorted(custom_words)))
    return True

def remove_custom_word(word):
    w = word.strip().lower()
    if not w: return False
    
    # Remove from memory
    if w in TRUSTED_WORDS:
        TRUSTED_WORDS.remove(w)
    if w in WORDS:
        del WORDS[w]
        
    # Save to file
    if os.path.exists(CUSTOM_DICT_FILE):
        with open(CUSTOM_DICT_FILE, "r") as f:
            custom_words = set(f.read().splitlines())
        if w in custom_words:
            custom_words.remove(w)
            with open(CUSTOM_DICT_FILE, "w") as f:
                f.write("\n".join(sorted(custom_words)))
    return True

GUI_CALLBACKS = {
    "on_log": None,          # func(original, corrected)
    "on_stats_update": None, # func()
    "on_status": None,       # func(msg)
    "on_toggle": None        # func(enabled)
}

def _notify_stats():
    cb = GUI_CALLBACKS["on_stats_update"]
    if cb:
        cb()

def _notify_log(orig, corr):
    cb = GUI_CALLBACKS["on_log"]
    if cb:
        cb(orig, corr)

def _notify_toggle(enabled):
    cb = GUI_CALLBACKS["on_toggle"]
    if cb:
        cb(enabled)

# ─────────────────────────────────────────────────────
# EXPLICIT TYPO FIXES
# Highest priority. Only actual mistakes should go here.
# ─────────────────────────────────────────────────────
CORRECTIONS = {
    "teh": "the", "hte": "the", "tge": "the", "thw": "the",
    "smth": "something", 
    "wdym": "what do you mean","idk":"I don't know","lol":"laughing out loud","brb":"be right back","tbh":"to be honest","omg":"oh my god","btw":"by the way","fyi":"for your information","imo":"in my opinion","irl":"in real life","tmi":"too much information","ttyl":"talk to you later","g2g":"got to go","bbl":"be back later","smh":"shaking my head","fomo":"fear of missing out","ikr":"I know right","ngl":"not gonna lie","fr":"for real","wyd":"what are you doing",
    "adn": "and", "nad": "and", "annd": "and",
    "siad": "said", "sayd": "said",
    "taht": "that", "htat": "that", "tath": "that",
    "waht": "what", "whta": "what",
    "form": "from",
    "fo": "of",
    "ot": "to", "tos": "to",
    "ont": "not", "nto": "not",
    "si": "is",
    "ti": "it",
    "becuase": "because", "becasue": "because", "becase": "because",
    "recieve": "receive", "recive": "receive", "reciev": "receive",
    "beleive": "believe", "belive": "believe", "beleif": "belief",
    "acheive": "achieve", "achive": "achieve", "acheieve": "achieve",
    "definately": "definitely", "definatly": "definitely", "definitly": "definitely",
    "wierd": "weird",
    "freind": "friend",
    "thier": "their", "theri": "their",
    "youre": "you're", "your'e": "you're",
    "dont": "don't", "doesnt": "doesn't", "didnt": "didn't",
    "wont": "won't", "cant": "can't", "couldnt": "couldn't",
    "wouldnt": "wouldn't", "shouldnt": "shouldn't",
    "im": "i'm", "id": "i'd", "ill": "i'll", "ive": "i've",
    "seperate": "separate", "separete": "separate",
    "ocurrance": "occurrence", "occurence": "occurrence", "occurance": "occurrence",
    "recomend": "recommend", "reccomend": "recommend", "recommed": "recommend",
    "accomodate": "accommodate", "acommodate": "accommodate",
    "neccessary": "necessary", "neccesary": "necessary", "necesary": "necessary",
    "adress": "address", "addres": "address",
    "begining": "beginning", "begginning": "beginning",
    "comming": "coming", "comin": "coming",
    "buisness": "business", "bussiness": "business", "busines": "business",
    "calender": "calendar", "calander": "calendar",
    "collegue": "colleague", "colleage": "colleague",
    "concious": "conscious", "consious": "conscious",
    "enviroment": "environment", "enviornment": "environment",
    "existance": "existence", "existince": "existence",
    "expierence": "experience", "experiance": "experience",
    "foriegn": "foreign", "foregn": "foreign",
    "goverment": "government", "governement": "government",
    "grammer": "grammar",
    "garantee": "guarantee", "guarentee": "guarantee",
    "harrass": "harass", "harras": "harass",
    "independant": "independent", "independet": "independent",
    "intresting": "interesting", "intersting": "interesting",
    "knowlege": "knowledge", "knowledege": "knowledge",
    "lisense": "license", "liscense": "license",
    "maintainance": "maintenance", "maintenence": "maintenance",
    "millenium": "millennium", "milenium": "millennium",
    "mispell": "misspell", "mispelled": "misspelled",
    "neice": "niece",
    "occured": "occurred", "ocurred": "occurred",
    "paralell": "parallel", "parellel": "parallel",
    "persue": "pursue", "persude": "pursue",
    "posession": "possession", "possesion": "possession",
    "priviledge": "privilege", "privlege": "privilege",
    "publically": "publicly",
    "relevent": "relevant", "relevnt": "relevant",
    "rythm": "rhythm", "rythym": "rhythm",
    "sieze": "seize",
    "succesful": "successful", "successfull": "successful",
    "suprise": "surprise", "surprize": "surprise",
    "tendancy": "tendency",
    "untill": "until", "untl": "until",
    "vaccum": "vacuum", "vacume": "vacuum",
    "visable": "visible", "visibel": "visible",
    "welcom": "welcome",
    "writting": "writing", "writen": "written",
    "wich": "which", "whic": "which",
    "woudl": "would", "wuold": "would",
    "coud": "could", "cuold": "could",
    "shoud": "should", "shoudl": "should",
    "alot": "a lot",
    "alright": "all right",
    "noone": "no one",
    "everytime": "every time",
    "alittle": "a little",
    "algoritm": "algorithm", "algorythm": "algorithm",
    "databse": "database", "datbase": "database",
    "fucntion": "function", "funciton": "function",
    "clsas": "class", "calss": "class",
    "varialbe": "variable", "varaible": "variable",
    "paramter": "parameter", "paramater": "parameter",
    "libary": "library", "libraray": "library",
    "progamming": "programming", "programing": "programming",
    "developement": "development", "developmet": "development",
    "implemntation": "implementation", "implemenation": "implementation",
    "infomation": "information", "informaton": "information",
    "applicaiton": "application", "applcation": "application",
    "inteface": "interface", "interfce": "interface",
    "lanaguage": "language", "langauge": "language",
    "probelm": "problem", "problm": "problem",
    "soluton": "solution", "soultion": "solution",
    "structue": "structure", "strcuture": "structure",
    "sytem": "system", "systm": "system",
    "technolgy": "technology", "techology": "technology",

    "youve": "you've",
    "youll": "you'll",
    "theyre": "they're",
    "theyve": "they've",
    "thats": "that's",
    "theres": "there's",
    "heres": "here's",
    "whats": "what's",
    "lets": "let's",

    "isnt": "isn't",
    "arent": "aren't",
    "wasnt": "wasn't",
    "werent": "weren't",
    "hasnt": "hasn't",
    "havent": "haven't",
    "hadnt": "hadn't",
}


# ─────────────────────────────────────────────────────
# BASE WORDS / VOCABULARY SEEDS
# ─────────────────────────────────────────────────────
BASE_WORDS = """
a able about above accept accepted remake remakes remade mistake remaking hardcode hardcodes hardcoded hardcoding retard accepting accepts across act acted acting action actions active actual actually add added adding addition additional address addresses admit admits admitted after again against age ages ago agree agreed agrees air all allow allowed allowing allows almost alone along already also although always am among amount an and another answer answers any anybody anyone anything app apps apply applied applies applying approach area areas around arrive as ask asked asking asks at attack attempt available avoid away back bad bag bags ball bank base basic basically basis be bear beat beautiful became because become becomes becoming been before began begin beginning begins behind being believe believed believes best better between beyond big bill bird bit black blue board body book books both box boy break bring brother brought build building built business but buy by call called calling calls came can cannot car care carry case cases cause caused center central certain certainly change changed changes changing check checked child children choose chose city class classes clean clear clearly close closed code codes coding cold collection college color come comes coming comment comments common company complete completed completely computer computers concern condition consider considered continue control convert cool copy core correct corrected correction corrections could country course create created current cut cuts day days debug delete depth design detail detailed develop developed developer developers developing development did didn't difference different difficult direct direction do does doesn't doing done door down draw drive drop during each earlier early ease easy edit effect effort either else end ended energy engineer enough enter entire environment especially even evening event ever every everybody everyone everything example examples except execute expected experience explain explicit extra face fact facts fail fair fall far fast feature features feel feet few field file files fill final finally find fine finish first five fix fixed fixing flow follow food foot for force form forms found four free friend friends from front full function functions future game gave general generate generated get gets getting give given gives go goes going gone good got great group grow had half hand happen happened happens happening hard has hasn't have haven't having he head hear help her here high him his hold home hot hour hours house how however human humans idea ideas if important in include included includes hardcode remade including input inside instead into is isn't issue it its itself just keep key keys kind knew know known language large last late later least leave left less let level life light like likely line lines list lists little live local long look looked looking looks lot love low machine made main make makes making man many map matter may maybe me mean means meant measure meet member members memory men message might mind minute minutes miss mistake mistakes mode model modern moment month more most move moved much multi must my name near necessarily need needed needs never new next nice night no none normal not note nothing now number numbers of off offer often old on once one ones only onto open option options or order original other others our out over own part parts past path people per perhaps person place plan point possible power present probably problem problems process product program programs project projects proper properly provide put python question quick quickly quite raise ran rather reach read real reason receive recent recognize record reduce refer related release remember remove removed result return returned returns right run running runs said same save saw say saying says school script scripts second section see seem seemed seems seen select send sentence separate series serious set several shall she short should shouldn't show side similar simple simply since single size small so software some someone something sometimes soon sorry sort sound source space special specific specifically spell spelling start started state stay step still stop store stored story string strong structure study such support sure switch system take taken talk task team technical tell than thank that the their them then there these they thing things think thinking this those though thought three through time to today together told too took tool top total toward try trying turn two type typed types typing under understand until up update updated use used useful user using valid value values variable variables very version via view want wanted wants was wasn't way we week well went were weren't what when where whether which while who whole why will with within without word words work worked working works world would write writing written wrong year years yes yet you young your you're
"""

SYSTEM_DICT_PATHS = [
    "/usr/share/dict/words",
    "/usr/dict/words",
]

ALPHABET = "abcdefghijklmnopqrstuvwxyz"


# ─────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────
controller = Controller()
_word_buffer = []
_correction_log = []
_log_lock = threading.Lock()
_CTRL_DOWN = False
_SHIFT_DOWN = False
_suppress_typed_keys = False
_suppress_lock = threading.Lock()
_backspace_down = False
_apply_lock = threading.Lock()

# ── Undo state ──
# Remembers the most recent correction so a quick backspace double-tap reverts it.
_last_correction = None   # dict: {"original": str, "corrected": str, "had_space": bool}
_last_correction_lock = threading.Lock()
_last_backspace_time = 0.0

BOUNDARY_KEYS = {Key.space, Key.enter, Key.tab}
PUNCT_CHARS = set(".!?,;:")
RESET_KEYS = {Key.left, Key.right, Key.up, Key.down, Key.home, Key.end, Key.esc}

WORDS = Counter()        # frequency table — used for ranking candidates
TRUSTED_WORDS: set = set()  # existence gate — a word must be here to be a valid correction target
TOTAL_WORDS = 0

# ── Bigram context (Feature: N-gram awareness) ──
_prev_words = deque(maxlen=3)  # rolling buffer of recent flushed words
BIGRAMS = Counter()            # bigram frequency table
TOTAL_BIGRAMS = 0

# ── Auto-capitalization (Feature: Smart capitalization) ──
SENTENCE_END_CHARS = set(".!?")
_sentence_end_pending = False
_capitalize_next = False

# ── Confusable words for context-aware retroactive correction ──
CONFUSABLES = {
    "to": ["too", "two"],
    "too": ["to", "two"],
    "two": ["to", "too"],
    "their": ["they're", "there"],
    "they're": ["their", "there"],
    "there": ["their", "they're"],
    "then": ["than"],
    "than": ["then"],
    "your": ["you're"],
    "you're": ["your"],
    "its": ["it's"],
    "it's": ["its"],
    "affect": ["effect"],
    "effect": ["affect"],
    "were": ["we're", "where"],
    "we're": ["were", "where"],
    "where": ["were", "we're"]
}

print("V4 LOADED")


# ─────────────────────────────────────────────────────
# VOCAB / CORPUS BUILDING
# ─────────────────────────────────────────────────────
def tokenize(text: str):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def add_words_from_iterable(words_iterable, weight=1):
    for w in words_iterable:
        w = w.strip().lower()
        if 2 <= len(w) <= 30 and re.fullmatch(r"[a-z]+(?:'[a-z]+)?", w):
            WORDS[w] += weight


def build_vocabulary():
    global TOTAL_WORDS

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # ── 1. TRUSTED_WORDS: the existence gate ──────────────────────────────────
    # A word must be in TRUSTED_WORDS to be a valid correction target.
    # We seed it from BASE_WORDS, CORRECTIONS targets, and TRUSTED_WORDS.txt.
    trusted_path = os.path.join(base_dir, "TRUSTED_WORDS.txt")
    if os.path.isfile(trusted_path):
        try:
            with open(trusted_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    w = line.strip().lower()
                    if 2 <= len(w) <= 30 and re.fullmatch(r"[a-z]+(?:'[a-z]+)?", w):
                        TRUSTED_WORDS.add(w)
            # Attempt to load custom dict
            load_custom_dict()

            print(f"[INFO] Loaded trusted word list: {trusted_path} ({len(TRUSTED_WORDS):,} words)")
        except Exception as e:
            print(f"[WARN] Could not load TRUSTED_WORDS.txt: {e}")
    else:
        print("[WARN] TRUSTED_WORDS.txt not found — falling back to WORDS for existence check")

    # Always trust BASE_WORDS and correction targets
    for w in BASE_WORDS.split():
        w = w.strip().lower()
        if w:
            TRUSTED_WORDS.add(w)
    for v in CORRECTIONS.values():
        v = v.strip().lower()
        # multi-word corrections (e.g. "a lot") — trust each token
        for tok in v.split():
            TRUSTED_WORDS.add(tok)

    # ── 2. WORDS (frequency table): used only for ranking candidates ──────────
    # Seed with BASE_WORDS and correction targets at high weight.
    add_words_from_iterable(BASE_WORDS.split(), weight=20)
    add_words_from_iterable(CORRECTIONS.values(), weight=50)

    # wordlist.txt — frequency source ONLY.
    # Words are listed roughly in frequency order (most common first).
    # We assign a decaying weight so rank-1 words get more weight than rank-10000.
    extra_wordlist = os.path.join(base_dir, "wordlist.txt")
    if os.path.isfile(extra_wordlist):
        try:
            with open(extra_wordlist, "r", encoding="utf-8", errors="ignore") as f:
                lines = [l.strip().lower() for l in f if l.strip()]
            total = max(len(lines), 1)
            for rank, raw in enumerate(lines):
                w = raw.strip().lower()
                if 2 <= len(w) <= 30 and re.fullmatch(r"[a-z]+(?:'[a-z]+)?", w):
                    # Weight decays from ~200 (rank 0) down to ~1 (rank total-1)
                    weight = max(1, int(200 * (1 - rank / total)))
                    WORDS[w] += weight
            print(f"[INFO] Loaded frequency list: {extra_wordlist} ({len(lines):,} entries)")
        except Exception as e:
            print(f"[WARN] Could not load wordlist.txt: {e}")

    # corpus.txt — additional real-world frequency signal
    corpus_path = os.path.join(base_dir, "corpus.txt")
    corpus_tokens = []
    if os.path.isfile(corpus_path):
        try:
            with open(corpus_path, "r", encoding="utf-8", errors="ignore") as f:
                corpus_text = f.read()
            corpus_tokens = tokenize(corpus_text)
            add_words_from_iterable(corpus_tokens, weight=5)
            print(f"[INFO] Loaded corpus frequencies: {corpus_path}")
        except Exception as e:
            print(f"[WARN] Could not load corpus.txt: {e}")

    for path in SYSTEM_DICT_PATHS:
        if os.path.isfile(path) and os.path.getsize(path) < 10_000_000:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    add_words_from_iterable((line.strip() for line in f), weight=3)
                print(f"[INFO] Loaded system dictionary: {path}")
                break
            except Exception:
                pass

    TOTAL_WORDS = sum(WORDS.values())

    # ── 3. BIGRAMS: context-aware ranking ──────────────────────────────
    bigrams_path = os.path.join(base_dir, "Bigram.txt")
    if os.path.isfile(bigrams_path):
        try:
            with open(bigrams_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) == 2:
                        pair, weight = parts[0], int(parts[1])
                        BIGRAMS[pair] += weight
            print(f"[INFO] Loaded bigrams from {bigrams_path}")
        except Exception as e:
            print(f"[WARN] Could not load Bigram.txt: {e}")

    # Extract bigrams from corpus.txt tokens
    if len(corpus_tokens) >= 2:
        for i in range(len(corpus_tokens) - 1):
            pair = f"{corpus_tokens[i]} {corpus_tokens[i+1]}"
            BIGRAMS[pair] += 3
        print(f"[INFO] Extracted {len(BIGRAMS):,} unique bigrams")

    TOTAL_BIGRAMS = sum(BIGRAMS.values()) or 1


build_vocabulary()


# ─────────────────────────────────────────────────────
# SPELL CORRECTION CORE
# ─────────────────────────────────────────────────────
def P(word: str) -> float:
    if TOTAL_WORDS == 0:
        return 0.0
    return WORDS[word] / TOTAL_WORDS


def bigram_boost(prev_word: str, candidate: str) -> float:
    """Return a context-aware probability boost for candidate given prev_word.

    The boost is scaled to be comparable to unigram P() values so it acts
    as a meaningful tiebreaker without dominating the frequency ranking.
    """
    if not prev_word or TOTAL_BIGRAMS == 0:
        return 0.0
    pair = f"{prev_word} {candidate}"
    count = BIGRAMS.get(pair, 0)
    if count == 0:
        return 0.0
    return (count / TOTAL_BIGRAMS) * 0.5


def known(candidates):
    """Return candidates that are both trusted (exist) AND have a frequency score."""
    if TRUSTED_WORDS:
        # Prefer: word must be in the trusted existence set.
        # Fall back to WORDS alone if TRUSTED_WORDS wasn't loaded.
        return {w for w in candidates if w in TRUSTED_WORDS and w in WORDS}
    return {w for w in candidates if w in WORDS}


def edits1(word: str):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in ALPHABET]
    inserts = [L + c + R for L, R in splits for c in ALPHABET]
    return set(deletes + transposes + replaces + inserts)


def edits2_known(word: str):
    out = set()
    for e1 in edits1(word):
        for e2 in edits1(e1):
            # Must pass the same existence gate as known()
            if (TRUSTED_WORDS and e2 in TRUSTED_WORDS and e2 in WORDS) or \
               (not TRUSTED_WORDS and e2 in WORDS):
                out.add(e2)
    return out


def preserve_case(original: str, corrected: str) -> str:
    if not corrected:
        return corrected
    if original.isupper():
        return corrected.upper()
    if len(original) > 1 and original[0].isupper() and original[1:].islower():
        return corrected[0].upper() + corrected[1:]
    return corrected


def is_word_like(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]+(?:'[A-Za-z]+)?", s))


def looks_like_simple_inflection(original: str, candidate: str) -> bool:
    if original == candidate:
        return True

    suffixes = ["s", "es", "ed", "d", "ing", "er", "ers", "est", "ly"]
    for suf in suffixes:
        if original.endswith(suf):
            stem = original[:-len(suf)]
            if stem and candidate == stem:
                return True

    if original.endswith("ed") and len(original) >= 4:
        stem = original[:-2]
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            if candidate == stem[:-1]:
                return True

    if original.endswith("ing") and len(original) >= 5:
        stem = original[:-3]
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            if candidate == stem[:-1]:
                return True

    return False


def edit_distance_bucket(original: str, candidate: str) -> int:
    if candidate in known(edits1(original)):
        return 1
    return 2


def candidate_score(original: str, candidate: str):
    dist = edit_distance_bucket(original, candidate)
    same_first = 1 if candidate and original and candidate[0] == original[0] else 0
    same_last = 1 if candidate and original and candidate[-1] == original[-1] else 0

    # Lower distance is better.
    # Frequency only matters after distance.
    return (
        -dist,
        same_first + same_last,
        P(candidate),
        -abs(len(candidate) - len(original)),
    )


def choose_best_candidate(original: str, candidates):
    filtered = []

    for cand in candidates:
        if cand == original:
            continue

        if looks_like_simple_inflection(original, cand):
            continue

        if abs(len(cand) - len(original)) > 2:
            continue

        filtered.append(cand)

    if not filtered:
        return None

    filtered.sort(key=lambda c: candidate_score(original, c), reverse=True)

    best = filtered[0]
    second = filtered[1] if len(filtered) > 1 else None
    return best, second


def correction(word: str, prev_word: str = None) -> str | None:
    global GUI_UNKNOWN_TOKENS
    lower = word.lower()

    # Basic guards
    if len(lower) < 2:
        return None
    if not is_word_like(word):
        return None

    # 1) Explicit typo map always wins
    if lower in CORRECTIONS:
        return preserve_case(word, CORRECTIONS[lower])

    # 2) Known / trusted word? keep it (do not correct)
    if is_valid(lower):
        return None

    # 3) Don't guess on very short words
    if len(lower) <= 3:
        return None

    # 4) Generate candidates (edit distance 1, optionally 2)
    cands1 = known(edits1(lower))
    if cands1:
        candidates = cands1
        ed = 1
    else:
        candidates = edits2_known(lower)
        ed = 2

    if not candidates:
        GUI_UNKNOWN_TOKENS += 1
        record_daily_stat("unknown")
        log_unknown(lower)
        return None

    # 5) Remove the original if somehow present
    candidates.discard(lower)
    if not candidates:
        return None

    # 6) Pick the most probable candidate, with bigram context boost
    def _score(c):
        boost = bigram_boost(prev_word, c) if ENABLE_BIGRAMS else 0.0
        return P(c) + boost
    best = max(candidates, key=_score)

    # 7) Guardrails — deliberately relaxed so real typos get fixed

    # Start letter must match (hard rule: avoids wild substitutions)
    if lower[0] != best[0]:
        return None

    # Avoid stripping valid inflections  (e.g. "words" → "word", "allowed" → "allow")
    # But ONLY block this when the correction shortens the word — not when it
    # changes it substantially (e.g. "chiken" → "chicken" is fine).
    if looks_like_simple_inflection(lower, best) and len(best) <= len(lower):
        return None

    # For edit-distance-2 corrections, require the candidate to be meaningfully
    # more probable than the second-best (avoids random guesses on long typos).
    # For edit-distance-1, trust the frequency ranking directly — no confidence
    # threshold needed because the candidate space is small and well-constrained.
    if ed == 2 and len(candidates) > 1:
        sorted_cands = sorted(candidates, key=_score, reverse=True)
        second = sorted_cands[1]
        # Only block if the best isn't clearly more probable (3× threshold)
        if P(best) < 3.0 * P(second):
            return None

    return preserve_case(word, best)



# ─────────────────────────────────────────────────────
# LOGGING / APPLY
# ─────────────────────────────────────────────────────
def _log(original, corrected):
    global GUI_CORRECTIONS_APPLIED
    
    with _log_lock:
        ts = time.strftime("%H:%M:%S")
        _correction_log.append((ts, original, corrected))
        if len(_correction_log) > 200:
            _correction_log.pop(0)

    GUI_CORRECTIONS_APPLIED += 1
    record_daily_stat("corrected")
    _notify_log(original, corrected)
    _notify_stats()

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    print(f"  [{ts}]  {YELLOW}{original}{RESET}  →  {GREEN}{corrected}{RESET}")


def _apply_correction(original: str, corrected: str, boundary_was_space: bool, retro_original: str = None, retro_corrected: str = None):
    global _suppress_typed_keys, _word_buffer, _last_correction

    with _apply_lock:
        with _suppress_lock:
            _suppress_typed_keys = True

        try:
            delete_count = len(original) + (1 if boundary_was_space else 0)
            if retro_original and retro_corrected:
                delete_count += 1 + len(retro_original)

            for _ in range(delete_count):
                controller.press(Key.backspace)
                controller.release(Key.backspace)
                time.sleep(0.004)

            if retro_original and retro_corrected:
                controller.type(retro_corrected + " ")

            controller.type(corrected)

            if boundary_was_space:
                controller.press(Key.space)
                controller.release(Key.space)

            _word_buffer.clear()
            _log(original, corrected)
            if retro_original and retro_corrected:
                _log(retro_original, retro_corrected)

            # Save undo info so a quick backspace double-tap can revert
            with _last_correction_lock:
                _last_correction = {
                    "original": original,
                    "corrected": corrected,
                    "had_space": boundary_was_space,
                }

        finally:
            time.sleep(0.02)
            with _suppress_lock:
                _suppress_typed_keys = False


def _apply_undo():
    """Revert the most recent autocorrection, restoring the original typed text.

    IMPORTANT: pynput does NOT suppress key events — by the time this runs,
    both backspace keypresses have already been processed by the OS, which
    means 2 characters have already been deleted from the screen.  We must
    subtract those 2 from our own delete count so we don't eat into the
    text that preceded the corrected word.
    """
    global _suppress_typed_keys, _word_buffer, _last_correction

    with _last_correction_lock:
        info = _last_correction
        _last_correction = None  # one-shot: clear immediately

    if info is None:
        return

    corrected = info["corrected"]
    original = info["original"]
    had_space = info["had_space"]

    # Small delay to let the OS finish processing the 2 physical backspaces
    time.sleep(0.05)

    with _apply_lock:
        with _suppress_lock:
            _suppress_typed_keys = True

        try:
            # Total chars the corrected word occupied on screen
            full_len = len(corrected) + (1 if had_space else 0)

            # The OS already deleted 2 chars (one per backspace tap),
            # so we only need to remove the remainder.
            remaining = max(0, full_len - 2)

            for _ in range(remaining):
                controller.press(Key.backspace)
                controller.release(Key.backspace)
                time.sleep(0.004)

            # Restore the original typed text
            controller.type(original)

            if had_space:
                controller.press(Key.space)
                controller.release(Key.space)

            _word_buffer.clear()

            # Log the undo
            ts = time.strftime("%H:%M:%S")
            CYAN = "\033[96m"
            RESET_C = "\033[0m"
            print(f"  [{ts}]  {CYAN}UNDO{RESET_C}  {corrected}  →  {original}")

        finally:
            time.sleep(0.02)
            with _suppress_lock:
                _suppress_typed_keys = False


def _flush_buffer(boundary_was_space: bool):
    global _word_buffer, _capitalize_next
    global GUI_WORDS_SCANNED, GUI_TOTAL_PROCESSING_TIME

    if not _word_buffer:
        return

    word = "".join(_word_buffer)
    _word_buffer = []

    stripped = word.rstrip("".join(PUNCT_CHARS))
    suffix = word[len(stripped):]

    # print(f"FLUSH: raw={word!r}, stripped={stripped!r}, suffix={suffix!r}, space={boundary_was_space}")

    if not stripped:
        return

    if " " in stripped:
        return

    GUI_WORDS_SCANNED += 1
    record_daily_stat("scanned")
    t0 = time.perf_counter()

    # Get previous word for bigram context
    prev = _prev_words[-1] if _prev_words else None

    # --- 1. Retroactive confusable correction ---
    retro_original = None
    retro_corrected = None
    
    if ENABLE_BIGRAMS and prev and prev.lower() in CONFUSABLES:
        best_retro = prev.lower()
        pair_key = f"{best_retro} {stripped.lower()}"
        best_retro_count = BIGRAMS.get(pair_key, 0)
        
        for cand in CONFUSABLES[best_retro]:
            cand_pair = f"{cand} {stripped.lower()}"
            cand_count = BIGRAMS.get(cand_pair, 0)
            # Threshold: must have a solid count (>= 5) and be significantly more common (> 2x)
            if cand_count >= 5 and cand_count > best_retro_count * 2:
                best_retro = cand
                best_retro_count = cand_count
                
        if best_retro != prev.lower():
            retro_original = prev
            retro_corrected = preserve_case(prev, best_retro)
            # Update history so future words see the corrected context
            _prev_words[-1] = retro_corrected.lower()
            prev = retro_corrected.lower()

    # --- 2. Current word spelling correction ---
    corrected = correction(stripped, prev_word=prev)
    final_word = corrected if (corrected and corrected != stripped) else stripped

    # --- 3. Current word confusable correction ---
    if ENABLE_BIGRAMS and prev and is_valid(stripped.lower()) and stripped.lower() in CONFUSABLES:
        best_current = stripped.lower()
        pair_key = f"{prev} {best_current}"
        best_current_count = BIGRAMS.get(pair_key, 0)
        
        for cand in CONFUSABLES[best_current]:
            cand_pair = f"{prev} {cand}"
            cand_count = BIGRAMS.get(cand_pair, 0)
            if cand_count >= 5 and cand_count > best_current_count * 2:
                best_current = cand
                best_current_count = cand_count
                
        if best_current != stripped.lower():
            final_word = preserve_case(stripped, best_current)

    # Auto-capitalize after sentence boundary (.!? followed by space/enter)
    if ENABLE_CAPITALIZATION and _capitalize_next and final_word and final_word[0].islower():
        final_word = final_word[0].upper() + final_word[1:]
    _capitalize_next = False  # always consume the flag after processing a word

    # Track this word for future bigram context
    _prev_words.append(final_word.lower())

    # Apply if anything changed (spelling correction, retroactive, capitalization)
    if final_word != stripped or retro_corrected:
        full_correction = final_word + suffix
        t = threading.Thread(
            target=_apply_correction,
            args=(word, full_correction, boundary_was_space, retro_original, retro_corrected),
            daemon=True,
        )
        t.start()
        
    processing_time = (time.perf_counter() - t0)
    GUI_TOTAL_PROCESSING_TIME += processing_time
    record_daily_stat("time_ms", processing_time * 1000)
    _notify_stats()


# ─────────────────────────────────────────────────────
# KEYBOARD EVENTS
# ─────────────────────────────────────────────────────
def is_valid(word: str) -> bool:
    """Return True if the word should be left alone (it's a real, known word)."""
    if TRUSTED_WORDS:
        return word in TRUSTED_WORDS
    # Fallback if TRUSTED_WORDS.txt wasn't loaded
    return word in WORDS
def on_press(key):
    global _CTRL_DOWN, _SHIFT_DOWN, _backspace_down
    global _capitalize_next, _last_backspace_time
    global MASTER_ENABLE

    with _suppress_lock:
        if _suppress_typed_keys:
            return

    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        _CTRL_DOWN = True
    if key in (Key.shift, Key.shift_l, Key.shift_r):
        _SHIFT_DOWN = True

    try:
        if _CTRL_DOWN and _SHIFT_DOWN and hasattr(key, "char") and key.char in ("a", "A"):
            MASTER_ENABLE = not MASTER_ENABLE
            status = "\033[92mENABLED\033[0m" if MASTER_ENABLE else "\033[91mDISABLED\033[0m"
            print(f"\n  ── AutoCorrect {status} ──\n")
            _word_buffer.clear()
            _notify_toggle(MASTER_ENABLE)
            return
    except Exception:
        pass

    if not MASTER_ENABLE:
        _word_buffer.clear()
        return

    global _last_correction
    global _sentence_end_pending, _capitalize_next

    with _suppress_lock:
        if _suppress_typed_keys:
            return

    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        _CTRL_DOWN = True
    if key in (Key.shift, Key.shift_l, Key.shift_r):
        _SHIFT_DOWN = True

    try:
        if _CTRL_DOWN and _SHIFT_DOWN and hasattr(key, "char") and key.char in ("a", "A"):
            with _enabled_lock:
                _enabled = not _enabled
            status = "\033[92mENABLED\033[0m" if _enabled else "\033[91mDISABLED\033[0m"
            print(f"\n  ── AutoCorrect {status} ──\n")
            _word_buffer.clear()
            return
    except Exception:
        pass



    try:
        if key in BOUNDARY_KEYS:
            _flush_buffer(boundary_was_space=(key == Key.space))

            # Sentence boundary: if we saw .!? before this space/enter, capitalize next word
            if _sentence_end_pending:
                _capitalize_next = True
                _sentence_end_pending = False

            # Enter always starts a new sentence (new paragraph)
            if key == Key.enter:
                _capitalize_next = True

        elif key == Key.backspace:
            if _backspace_down:
                return

            _backspace_down = True

            # ── Double-tap backspace → undo last correction ──
            now = time.monotonic()
            gap = now - _last_backspace_time
            _last_backspace_time = now

            with _last_correction_lock:
                has_undo = _last_correction is not None

            if gap <= UNDO_WINDOW and has_undo:
                # Spawn undo on a thread (same pattern as corrections)
                t = threading.Thread(target=_apply_undo, daemon=True)
                t.start()
                return   # swallow this backspace — undo handles everything

            if _word_buffer:
                _word_buffer.pop()

        elif key in RESET_KEYS:
            _word_buffer.clear()
            _prev_words.clear()
            _sentence_end_pending = False
            _capitalize_next = False
            # Any navigation clears undo availability
            with _last_correction_lock:
                _last_correction = None

        elif hasattr(key, "char") and key.char is not None:
            ch = key.char

            if ch in PUNCT_CHARS:
                _flush_buffer(boundary_was_space=False)
                # Track sentence-ending punctuation for auto-capitalization
                if ch in SENTENCE_END_CHARS:
                    _sentence_end_pending = True
                else:
                    _sentence_end_pending = False
            elif ch.isprintable():
                _word_buffer.append(ch)

            # Any typing clears undo availability
            with _last_correction_lock:
                _last_correction = None

    except Exception:
        pass


def on_release(key):
    global _CTRL_DOWN, _SHIFT_DOWN, _backspace_down

    if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
        _CTRL_DOWN = False
    if key in (Key.shift, Key.shift_l, Key.shift_r):
        _SHIFT_DOWN = False
    if key == Key.backspace:
        _backspace_down = False


# ─────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────
BANNER = """
\033[96m╔══════════════════════════════════════════════════════╗
║        AutoCorrect Daemon v4.0 (Context-Aware)       ║
║    System-wide spell correction across all apps      ║
╚══════════════════════════════════════════════════════╝\033[0m

  \033[92m●  Running\033[0m  —  corrections will appear below as they happen
  \033[93mCtrl + Shift + A\033[0m  to toggle on / off
  \033[91mCtrl + C\033[0m          to quit

  Explicit corrections: \033[96m{dict_count}\033[0m
  Vocabulary words:     \033[96m{vocab_count}\033[0m
  Weighted tokens:      \033[96m{token_count}\033[0m

  Algorithm:
    - exact typo map first
    - known word? keep it
    - known edit-distance 1 candidates
    - known edit-distance 2 candidates (only for longer words)
    - bigram context ranking
    - confusable retroactive fixes

  Optional files in same folder:
    - wordlist.txt       (one word per line)
    - corpus.txt         (text used for frequency ranking)
    - Bigram.txt         (bigram occurrences for context)

  ────────────────────────────────────────────────────
  TIME      TYPED          →  CORRECTED
  ────────────────────────────────────────────────────
"""

def start_in_background():
    """Starts the listener in a background daemon thread (for GUI integration)."""
    if not WORDS:
        build_vocabulary()
    
    def run_listener():
        with Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
            
    t = threading.Thread(target=run_listener, daemon=True)
    t.start()


def main():
    try:
        import gui
        gui.launch()
    except Exception as e:
        # Fallback to terminal mode if GUI fails or PySide6 is missing
        print(f"[SYSTEM] GUI Launch failed: {e}")
        print("[SYSTEM] Falling back to Terminal mode...")
        
        print(BANNER.format(
            dict_count=len(CORRECTIONS),
            vocab_count=len(WORDS),
            token_count=TOTAL_WORDS
        ))

        if sys.platform == "darwin":
            print("  \033[93m[macOS]\033[0m If keys aren't intercepted, grant Accessibility access:")
            print("         System Settings → Privacy & Security → Accessibility → add Terminal\n")
        elif sys.platform.startswith("linux"):
            if hasattr(os, "geteuid") and os.geteuid() != 0:
                print("  \033[93m[Linux]\033[0m If keys aren't intercepted, try running with sudo\n")

        with Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()


if __name__ == "__main__":
    main()
