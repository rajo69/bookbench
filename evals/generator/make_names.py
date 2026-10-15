"""Build the frozen pseudo-surname list used for person payees (run once; output is committed with this script).

Usage (stdlib only, so it runs isolated against untrusted downloads):
    python -I evals/generator/make_names.py <Names_2010Census.zip> <words_alpha.txt> <brands_uk.json> <brands_us.json> <out.json>
    python -I evals/generator/make_names.py --refilter <pseudo_surnames.json>   (apply the deny filter in place)

Composer: seeded random.Random(SEED) joins onset + vowel + middle + suffix (for example "Halvennick"). A candidate is
kept only if (1) it is not a surname in the US Census Bureau 2010 surname file (public domain; aggregate counts of
surnames occurring 100 or more times, no individuals), (2) it is not an English word in the dwyl english-words list
(Unlicense), (3) it shares no word with a brand name, and (4) it is at least edit distance 2 from every name kept so far.

Deny filter (applied after composing, so it never changes which candidates are composed): a name containing an
offensive or unfortunate substring (DENY_SUBSTRINGS), or listed in DENY_EXACT (a real surname the Census file misses),
is dropped. The list keeps its order and the output records the dropped positions; firms.py draws from a pool of the
pre-filter size and replaces a dropped position, so names that survive the filter keep their place in every firm.
The committed list was filtered with `--refilter` because the Census and word-list inputs were not to hand; a full
rebuild applies the same filter and gives the same list.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import sys
import zipfile

SEED = 20261013
TARGET = 400
ONSETS = ["H", "C", "B", "D", "F", "G", "K", "L", "M", "N", "P", "R", "S", "T", "V", "W", "Br", "Cr", "Dr", "Gr",
          "Tr", "Pr", "St", "Th", "Wh", "Bl", "Cl", "Fl", "Gl", "Sl", "Sh", "Ch", "Qu"]
VOWELS = ["a", "e", "i", "o", "u", "ae", "ai", "ea", "oa", "ou", "y"]
MIDDLES = ["lv", "rn", "rr", "nd", "ld", "lm", "rv", "sk", "st", "th", "mb", "nt", "rk", "ll", "nn", "dd", "gg", "ck",
           "lw", "rw", "sw", "tw", "mm", "ff", "v", "z", "m", "n", "l", "r", "t", "d", "g", "b", "p", "s"]
SUFFIXES = ["ennick", "anick", "worth", "imere", "amere", "eby", "isby", "ham", "ingham", "ell", "owell", "erell",
            "ock", "ard", "ington", "ley", "ridge", "stow", "ett", "ine", "ow", "ens", "ick", "ond", "aven"]


DENY_SUBSTRINGS = ("dick", "tard", "breast", "troll", "cock", "cum", "shit", "piss", "fuck", "nazi", "rape", "slut",
                   "whore", "twat", "wank", "tit", "anal", "butt", "porn", "sex", "kill", "dead", "hick")
DENY_EXACT = ("Hickley",)  # a real (rare) English surname


def denied(name: str) -> bool:
    low = name.lower()
    return name in DENY_EXACT or any(d in low for d in DENY_SUBSTRINGS)


def deny_filter(names: list[str]) -> tuple[list[str], dict]:
    """Drop denied names, keeping order; return the kept list and a record of what the filter did."""
    removed = [i for i, n in enumerate(names) if denied(n)]
    kept = [n for n in names if not denied(n)]
    return kept, {
        "substrings": list(DENY_SUBSTRINGS),
        "exact": list(DENY_EXACT),
        "draw_pool_size": len(names),
        "removed": len(removed),
        "removed_positions": removed,
    }


def write_doc(doc: dict, out: str) -> None:
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def refilter(path: str) -> None:
    """Apply the deny filter to an already built list (no-op if it was filtered before)."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if "deny_filter" in doc:
        print("already filtered")
        return
    doc["surnames"], doc["deny_filter"] = deny_filter(doc["surnames"])
    doc["count"] = len(doc["surnames"])
    write_doc(doc, path)
    print(f"removed {doc['deny_filter']['removed']}; {doc['count']} names left")


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def main(census_zip: str, words_path: str, brands_uk: str, brands_us: str, out: str) -> None:
    with zipfile.ZipFile(census_zip) as z:
        raw = z.read("Names_2010Census.csv").decode("utf-8", errors="replace")
    census = {row["name"].strip().lower() for row in csv.DictReader(io.StringIO(raw)) if row.get("name")}
    with open(words_path, encoding="utf-8", errors="replace") as fh:
        words = {w.strip().lower() for w in fh if w.strip()}
    brand_words = set()
    for p in (brands_uk, brands_us):
        with open(p, encoding="utf-8") as fh:
            for b in json.load(fh):
                brand_words.update(w.lower() for w in b["name"].replace("&", " ").split())
    rng = random.Random(SEED)
    kept: list[str] = []
    rejected = {"census": 0, "english_word": 0, "brand_word": 0, "too_close": 0, "length": 0}
    attempts = 0
    while len(kept) < TARGET and attempts < 200000:
        attempts += 1
        cand = rng.choice(ONSETS) + rng.choice(VOWELS) + rng.choice(MIDDLES) + rng.choice(SUFFIXES)
        low = cand.lower()
        if not 6 <= len(cand) <= 11:
            rejected["length"] += 1
        elif low in census:
            rejected["census"] += 1
        elif low in words:
            rejected["english_word"] += 1
        elif low in brand_words:
            rejected["brand_word"] += 1
        elif any(edit_distance(low, k.lower()) < 2 for k in kept):
            rejected["too_close"] += 1
        else:
            kept.append(cand)
    composed = len(kept)
    kept, deny = deny_filter(kept)
    doc = {
        "purpose": "Invented surnames for synthetic person payees (<initial> <surname>). Not real people.",
        "seed": SEED,
        "count": len(kept),
        "attempts": attempts,
        "rejected": rejected,
        "sources": {
            "us_census_2010_surnames": {
                "url": "https://www2.census.gov/topics/genealogy/2010surnames/names.zip",
                "licence": "US government work, public domain",
                "sha256_zip": sha256(census_zip),
                "surnames": len(census),
            },
            "english_words": {
                "url": "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
                "licence": "Unlicense (public domain dedication)",
                "sha256": sha256(words_path),
                "words": len(words),
            },
            "brand_lists": ["sources/brands_uk.json", "sources/brands_us.json"],
        },
        "surnames": kept,
        "deny_filter": deny,
    }
    write_doc(doc, out)
    print(f"kept {len(kept)} of {composed} composed ({attempts} candidates); rejected {rejected}; "
          f"denied {deny['removed']}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--refilter"]:
        refilter(sys.argv[2])
    else:
        main(*sys.argv[1:6])
