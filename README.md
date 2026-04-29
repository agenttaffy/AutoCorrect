
# AutoCorrect

A lightweight system-wide Python autocorrect script that fixes common misspellings while you type across apps.

## Features

- System-wide keyboard listener using `pynput`
- Explicit typo corrections for common mistakes
- Edit-distance candidate generation, deletion, transposition, replacement, insertion
- Conservative correction rules to reduce bad guesses
- Trusted dictionary layer for deciding what counts as a real word
- Separate frequency layer for ranking candidate corrections
- Toggle on or off with `Ctrl + Shift + A`
- Undo removed for stability

## Why this exists

Large word lists often contain misspellings, junk tokens, and noisy entries. If those lists are treated as the source of truth, the autocorrect system starts accepting incorrect words and stops fixing real errors.

This project uses a two-layer design instead:

- `TRUSTED_WORDS` decides whether a word is valid
- `WORD_FREQS` helps rank possible corrections

That keeps the correction logic much more stable and avoids trusting noisy corpora as if they were clean dictionaries.

## How it works

When you finish typing a word:

1. The script checks the explicit typo dictionary first
2. If the word is in the trusted dictionary, it is left alone
3. If not, the script generates edit-distance candidates
4. Candidates are filtered with conservative guardrails
5. The best candidate is chosen using frequency and quality rules
6. The word is replaced in-place

## Files

Recommended project structure:

```text
AutoCorrect/
├── V4.py
├── README.md
├── trusted_words.txt
├── wordlist_10k.txt
├── obsoletewordlist_10k.txt
├── corpus.txt
└── Dictionary.txt
```

### Suggested file roles

- `V4.py` — main autocorrect script
- `trusted_words.txt` — clean trusted dictionary used for validity
- `wordlist_10k.txt` — optional clean vocabulary expansion
- `obsoletewordlist_10k.txt` — optional extra trusted list
- `corpus.txt` — frequency source used for ranking candidates
- large noisy word lists — frequency only, not validity

## Installation

Install Python, then install the dependency:

```bash
pip install pynput
```

## Run

```bash
python V4.py
```

## Controls

- `Ctrl + Shift + A` — toggle autocorrect on or off
- `Ctrl + C` — quit from the terminal

## Dictionary model

This project separates spelling validity from ranking.

### Trusted dictionary

The trusted dictionary should contain clean words only. This is the authority source for deciding whether a word is valid.

Good examples:
- SCOWL-style word lists
- Hunspell-based dictionaries
- carefully cleaned personal word lists

### Frequency sources

Frequency sources help the script decide which correction is more likely, but they should not automatically make a word valid.

Examples:
- text corpora
- large Google word-frequency lists
- noisy large vocabulary dumps

## Example

If a noisy corpus contains a typo like `definately`, a naive autocorrect system may incorrectly treat it as valid and skip correction.

This project avoids that by using trusted vocabulary for validity and frequency data only for ranking candidates.

## Notes

- This script is designed to be conservative
- Short words are intentionally not corrected aggressively
- Undo was removed because it introduced instability in live typing behavior
- Global keyboard hooks may behave differently across Windows, macOS, and Linux

## Windows notes

If PowerShell says `git` is not recognized, install Git for Windows and reopen the terminal.

If the script launches but does not intercept keys, make sure Python and `pynput` are installed correctly and run the script from a normal terminal.

## Future improvements

- Better trusted dictionary import flow
- Configurable correction thresholds
- Optional personal dictionary
- Better logging and debug mode
- Safer candidate scoring
- Packaging as a background utility

## License


