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
║        AutoCorrect Daemon v3.1 (Stable, No Undo)    ║
║    System-wide spell correction across all apps     ║
╚══════════════════════════════════════════════════════╝

INSTALL:
    pip install pynput

RUN:
    python autocorrectv3.py

TOGGLE ON/OFF:  Ctrl + Shift + A
QUIT:           Ctrl + C  (in terminal)

OVERVIEW:
- No difflib fuzzy matching
- Uses edit-based candidate generation:
    deletion, transposition, replacement, insertion
- Uses word frequencies to rank corrections
- Strong guardrails to avoid bad fixes like:
    words   -> word
    allowed -> allow
    scripts -> script
- Explicit typo dictionary still has highest priority
- Undo removed for stability

OPTIONAL:
- Put a file named "wordlist_10k.txt" beside this script
  with one word per line to expand the vocabulary.
- Put a file named "corpus.txt" beside this script
  to improve word frequency ranking.
"""

import sys
import time
import threading
import os
import re
from collections import Counter

try:
    from pynput.keyboard import Key, Controller, Listener
except ImportError:
    print("\n[ERROR] pynput is not installed.")
    print("Run:  pip install pynput\n")
    sys.exit(1)


# ─────────────────────────────────────────────────────
# EXPLICIT TYPO FIXES
# Highest priority. Only actual mistakes should go here.
# ─────────────────────────────────────────────────────
CORRECTIONS = {
    "teh": "the", "hte": "the", "tge": "the", "thw": "the",
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
_enabled = True
_enabled_lock = threading.Lock()
_correction_log = []
_log_lock = threading.Lock()
_CTRL_DOWN = False
_SHIFT_DOWN = False
_suppress_typed_keys = False
_suppress_lock = threading.Lock()
_backspace_down = False
_apply_lock = threading.Lock()

BOUNDARY_KEYS = {Key.space, Key.enter, Key.tab}
PUNCT_CHARS = set(".!?,;:")
RESET_KEYS = {Key.left, Key.right, Key.up, Key.down, Key.home, Key.end, Key.esc}

WORDS = Counter()
TOTAL_WORDS = 0
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

    add_words_from_iterable(BASE_WORDS.split(), weight=20)
    add_words_from_iterable(CORRECTIONS.values(), weight=50)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    extra_wordlist = os.path.join(base_dir, "wordlist_10k.txt")
    if os.path.isfile(extra_wordlist):
        try:
            with open(extra_wordlist, "r", encoding="utf-8", errors="ignore") as f:
                add_words_from_iterable((line.strip() for line in f), weight=15)
            print(f"[INFO] Loaded extra word list: {extra_wordlist}")
        except Exception as e:
            print(f"[WARN] Could not load wordlist_10k.txt: {e}")

    corpus_path = os.path.join(base_dir, "corpus.txt")
    if os.path.isfile(corpus_path):
        try:
            with open(corpus_path, "r", encoding="utf-8", errors="ignore") as f:
                corpus_text = f.read()
            add_words_from_iterable(tokenize(corpus_text), weight=1)
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


build_vocabulary()


# ─────────────────────────────────────────────────────
# SPELL CORRECTION CORE
# ─────────────────────────────────────────────────────
def P(word: str) -> float:
    if TOTAL_WORDS == 0:
        return 0.0
    return WORDS[word] / TOTAL_WORDS


def known(candidates):
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
            if e2 in WORDS:
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


def candidate_score(original: str, candidate: str):
    same_first = 1 if candidate and original and candidate[0] == original[0] else 0
    return (
        P(candidate),
        -abs(len(candidate) - len(original)),
        same_first,
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


def correction(word: str) -> str | None:
    lower = word.lower()

    if len(lower) < 2:
        return None

    if not is_word_like(word):
        return None

    if lower in CORRECTIONS:
        return preserve_case(word, CORRECTIONS[lower])

    if lower in WORDS:
        return None

    if len(lower) <= 4:
        return None

    def maybe_pick(candidates):
        result = choose_best_candidate(lower, candidates)
        if not result:
            return None

        best, second = result

        if lower[0] != best[0] or lower[-1] != best[-1]:
            return None

        p_best = P(best)
        p_second = P(second) if second else 0.0

        if second is not None and p_best < (1.5 * p_second):
            return None

        if len(lower) <= 6 and p_best < 1e-5:
            return None

        return best

    cands1 = known(edits1(lower))
    cand = maybe_pick(cands1)
    if cand:
        return preserve_case(word, cand)

    if len(lower) >= 7:
        cands2 = edits2_known(lower)
        cand = maybe_pick(cands2)
        if cand:
            return preserve_case(word, cand)

    return None


# ─────────────────────────────────────────────────────
# LOGGING / APPLY
# ─────────────────────────────────────────────────────
def _log(original, corrected):
    with _log_lock:
        ts = time.strftime("%H:%M:%S")
        _correction_log.append((ts, original, corrected))
        if len(_correction_log) > 200:
            _correction_log.pop(0)

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    print(f"  [{ts}]  {YELLOW}{original}{RESET}  →  {GREEN}{corrected}{RESET}")


def _apply_correction(original: str, corrected: str, boundary_was_space: bool):
    global _suppress_typed_keys, _word_buffer

    with _apply_lock:
        with _suppress_lock:
            _suppress_typed_keys = True

        try:
            delete_count = len(original) + (1 if boundary_was_space else 0)

            for _ in range(delete_count):
                controller.press(Key.backspace)
                controller.release(Key.backspace)
                time.sleep(0.004)

            controller.type(corrected)

            if boundary_was_space:
                controller.press(Key.space)
                controller.release(Key.space)

            _word_buffer.clear()
            _log(original, corrected)

        finally:
            time.sleep(0.02)
            with _suppress_lock:
                _suppress_typed_keys = False


def _flush_buffer(boundary_was_space: bool):
    global _word_buffer

    if not _word_buffer:
        return

    word = "".join(_word_buffer)
    _word_buffer = []

    stripped = word.rstrip("".join(PUNCT_CHARS))
    suffix = word[len(stripped):]

    print(f"FLUSH: raw={word!r}, stripped={stripped!r}, suffix={suffix!r}, space={boundary_was_space}")

    if not stripped:
        return

    if " " in stripped:
        return

    corrected = correction(stripped)
    if corrected and corrected != stripped:
        full_correction = corrected + suffix
        t = threading.Thread(
            target=_apply_correction,
            args=(word, full_correction, boundary_was_space),
            daemon=True,
        )
        t.start()


# ─────────────────────────────────────────────────────
# KEYBOARD EVENTS
# ─────────────────────────────────────────────────────
def on_press(key):
    global _CTRL_DOWN, _SHIFT_DOWN, _enabled, _backspace_down

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

    with _enabled_lock:
        if not _enabled:
            return

    try:
        if key in BOUNDARY_KEYS:
            _flush_buffer(boundary_was_space=(key == Key.space))

        elif key == Key.backspace:
            if _backspace_down:
                return

            _backspace_down = True

            if _word_buffer:
                _word_buffer.pop()

        elif key in RESET_KEYS:
            _word_buffer.clear()

        elif hasattr(key, "char") and key.char is not None:
            ch = key.char

            if ch in PUNCT_CHARS:
                _flush_buffer(boundary_was_space=False)
            elif ch.isprintable():
                _word_buffer.append(ch)

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
║        AutoCorrect Daemon v3.1 (Stable, No Undo)    ║
║    System-wide spell correction across all apps     ║
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

  Guardrails:
    - no difflib/fuzzy matching
    - no singularizing/plural collapsing
    - no aggressive guessing on short words
    - undo disabled for stability

  Optional files in same folder:
    - wordlist_10k.txt   (one word per line)
    - corpus.txt         (text used for frequency ranking)

  ────────────────────────────────────────────────────
  TIME      TYPED          →  CORRECTED
  ────────────────────────────────────────────────────
"""


def main():
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

    try:
        with Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n\n  \033[91mStopped.\033[0m  AutoCorrect Daemon exited.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()