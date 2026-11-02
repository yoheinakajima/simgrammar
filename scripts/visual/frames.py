"""Grammar of **Frame.** lines in media/episodes, media/shorts, media/mega, and media/intro (ADR-0006).

A Frame line sits under a Picture line and names one frame template and its arguments:

    **Frame.** chain nodes=factory,pollution-spread,land-value,house:Zone growth signs=+,-,+ verbs=writes,lowers,raises from=simcity-1989

Arguments are key=value pairs separated by spaces; a value with spaces is quoted ("..."). Lists are comma-separated,
rows of a list are separated by |, and an item may carry a label after a colon (house:Zone growth). A Picture may
carry several Frame lines; every one after the first has at="<phrase>", the narration words at which it takes over.
scripts/visual/check.py validates Frame lines (E040); scripts/video/framedata.py resolves them for the renderer.

The templates and their variants:

    anatomy   game=<id> [parts=core|all|firsts|<ids>] [dates]   a game and its parts; firsts: the parts it was first to use
              hub=<id> spokes=<items> [weights=illustrative]     objects around a subject (smart objects)
              blank [dates]                                      an empty anatomy for the viewer's own game
    chain     nodes=<rows> [signs] [verbs] [loops] [fan]         a causal chain; fan: the first node feeds all the others
    compare   a= b= a_items= b_items=                            two drawn columns
              games=<id>,<id> [show=family|shared|own]           two games: their families, shared parts, or own core parts
    count     kind=bars|tiles|roles|venn|set|units|figures|tally|piles|spread|stat|ranked|packages|totals|icons (see TEMPLATES)
              bars with=<games|...>: the games named under each bar, one row of game ids per mechanic, each using it
              totals and icons cues=<group:word,...>: the narration word that lights each group (game, mechanic, technique,
              prediction; or an icon kind)
    timeline  ids=<mechanics> | kind=gap|due|due-years|techniques | kind=games ids=<games>   games: the catalog by release year
    site      page=<path> [scroll=<px>]                          a screenshot of the project's own site as this build renders it
    formula   result= terms= [from=] [rule=]                     terms may be numbers with a unit label (250:points) and ( ) groups
    scale     field=<mechanic>.<field> | ids= fields=            one rubric scale, or rulers placing several mechanics
    record    mechanic= | bet= | technique= | run= | game= | bets= | script= find= | lines= (a blank or rules card)
    moment    panels=<icons:caption|...>                         a strip drawn from the narration
    toysim    sim=heat|chunks|flow|life|sand|wfc from=           a toy simulation of the rule a record states
    mockup    kind=ui|terminal|doc|standin                       always labelled mock-up, re-enactment, or stand-in
"""
from __future__ import annotations

import re

LABEL = "**Frame.**"
KV = re.compile(r'([a-z_]+)=("([^"]*)"|\S+)')
NUMBER = re.compile(r"^[0-9][0-9,]*(?:\.[0-9]+)?%?$")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

# key -> kind of value. Kinds: game, games, mechanic, mechanics, elements, family, icon, items, rows, signs, words, loops,
# text, lines, phrase, field, fields, gamemech, from, terms, panels, bet, bets, technique, techniques, run, source, stat,
# date, enum:<a|b>, number, flag, gamerows, page
COMMON = {"at": "phrase", "current": "words"}
TEMPLATES: dict[str, dict] = {
    "anatomy": {"keys": {"game": "game", "parts": "words", "hub": "icon", "spokes": "items", "weights": "enum:illustrative",
                         "from": "gamemech", "blank": "flag", "dates": "flag"},
                "one_of": [("game",), ("hub", "spokes"), ("blank",)]},
    "chain": {"keys": {"nodes": "rows", "signs": "signs", "verbs": "words", "loops": "loops", "from": "game", "strip": "text", "fan": "flag"},
              "required": ("nodes",)},
    "compare": {"keys": {"a": "text", "b": "text", "a_items": "items", "b_items": "items", "from": "gamemech", "games": "games",
                         "show": "enum:family|shared|own"},
                "one_of": [("a", "b", "a_items", "b_items"), ("games",)]},
    "count": {"keys": {"kind": "enum:bars|tiles|roles|venn|set|units|figures|tally|piles|spread|stat|ranked|packages|totals|icons",
                       "ids": "elements", "family": "family", "lit": "enum:affected|none", "rank": "flag", "rank_by": "enum:prevalence|exposure",
                       "a": "text", "b": "text", "a_ids": "techniques", "b_ids": "techniques", "groups": "words", "dates": "flag",
                       "total": "number", "on": "number", "also": "number", "unit": "icon", "labels": "words", "from": "from",
                       "rows": "lines", "cols": "words", "of": "enum:technique|opportunity|record|link", "field": "text",
                       "where": "enum:in-play|shipped", "names": "flag", "id": "mechanic", "stat": "stat", "label": "text", "n": "number",
                       "with": "gamerows", "cues": "words"},
              "required": ("kind",)},
    "timeline": {"keys": {"ids": "mechanics", "kind": "enum:first|gap|due|due-years|techniques|games", "date": "date", "bet": "bet"}},
    "formula": {"keys": {"result": "items", "terms": "terms", "from": "from", "rule": "enum:opportunity_priority"}, "required": ("result", "terms")},
    "scale": {"keys": {"field": "field", "ids": "mechanics", "fields": "fields"}, "one_of": [("field",), ("ids", "fields")]},
    "record": {"keys": {"mechanic": "mechanic", "bet": "bet", "bets": "bets", "technique": "technique", "run": "run", "game": "game",
                        "fields": "words", "stamps": "text", "lines": "lines", "title": "text", "numbered": "flag", "script": "text", "find": "text"},
               "one_of": [("mechanic",), ("bet",), ("bets",), ("technique",), ("run",), ("game",), ("lines",), ("script", "find")]},
    "moment": {"keys": {"panels": "panels", "subject": "icon"}, "required": ("panels",)},
    "toysim": {"keys": {"sim": "enum:heat|chunks|flow|life|sand|wfc", "from": "from", "tick": "number", "rate": "number", "threshold": "number",
                        "levels": "number", "gens": "number"},
               "required": ("sim", "from")},
    "mockup": {"keys": {"kind": "enum:ui|terminal|doc|standin", "title": "text", "lines": "lines", "items": "items", "bet": "bet",
                        "from": "from", "subject": "text", "chart": "enum:fan|timer", "button": "text", "label": "enum:mock-up|re-enactment|stand-in"},
               "required": ("kind",)},
    "site": {"keys": {"page": "page", "scroll": "number"}, "required": ("page",)},
}
# the count kinds and the keys each needs
COUNT_NEEDS = {"bars": ("ids",), "tiles": ("family",), "venn": ("a", "b"), "set": ("ids",), "units": ("total", "on", "from"),
               "figures": ("rows", "cols", "from"), "tally": ("of", "field"), "piles": ("a", "b", "a_ids", "b_ids"), "spread": ("id",),
               "stat": ("stat",), "ranked": ("of",), "packages": ("rows",)}
TIMELINE_NEEDS = {"first": ("ids",), "gap": ("ids",), "due": (), "due-years": (), "techniques": (), "games": ("ids",)}
PAGE = re.compile(r"^/(?:[a-z0-9][a-z0-9-]*/)*$")   # a site path, as the site links it: /, /mechanic/power-grid/


class FrameError(ValueError):
    pass


def parse(text: str) -> tuple[str, dict[str, str]]:
    """'chain nodes=a,b signs=+' -> ('chain', {'nodes': 'a,b', 'signs': '+'}); raises FrameError on bad syntax."""
    text = text.strip()
    if text.startswith(LABEL):
        text = text[len(LABEL):].strip()
    head, _, rest = text.partition(" ")
    if head not in TEMPLATES:
        raise FrameError(f"unknown frame template '{head}' (one of {', '.join(TEMPLATES)})")
    args: dict[str, str] = {}
    pos = 0
    rest = rest.strip()
    while pos < len(rest):
        if rest[pos] == " ":
            pos += 1
            continue
        m = KV.match(rest, pos)
        if m:
            k = m.group(1)
            if k in args:
                raise FrameError(f"'{k}' is given twice")
            args[k] = m.group(3) if m.group(3) is not None else m.group(2)
            pos = m.end()
            continue
        word = rest[pos:].split(" ", 1)[0]
        if word in TEMPLATES[head]["keys"] and TEMPLATES[head]["keys"][word] == "flag":
            args[word] = "yes"
            pos += len(word)
            continue
        raise FrameError(f"cannot read '{word}' (arguments are key=value, values with spaces in double quotes)")
    spec = TEMPLATES[head]
    allowed = {**spec["keys"], **COMMON}
    for k in args:
        if k not in allowed:
            raise FrameError(f"'{head}' takes no '{k}' (keys: {', '.join(sorted(allowed))})")
    for k in spec.get("required", ()):
        if k not in args:
            raise FrameError(f"'{head}' needs '{k}'")
    if "one_of" in spec and not any(all(k in args for k in group) for group in spec["one_of"]):
        raise FrameError(f"'{head}' needs one of: " + "; ".join(" and ".join(g) for g in spec["one_of"]))
    if head == "count":
        for k in COUNT_NEEDS.get(args["kind"], ()):
            if k not in args:
                raise FrameError(f"count kind={args['kind']} needs '{k}'")
    if head == "timeline":
        kind = args.get("kind", "first")
        for k in TIMELINE_NEEDS[kind]:
            if k not in args:
                raise FrameError(f"timeline kind={kind} needs '{k}'")
        if kind == "due" and not ("date" in args or "bet" in args):
            raise FrameError("timeline kind=due needs 'date' or 'bet'")
    for k, v in args.items():
        kind = allowed[k]
        if kind.startswith("enum:") and v not in kind[5:].split("|"):
            raise FrameError(f"'{k}' is one of {kind[5:].replace('|', ', ')}, not '{v}'")
        if kind == "number" and not NUMBER.match(v):
            raise FrameError(f"'{k}' must be a number, not '{v}'")
        if kind == "date" and not DATE.match(v):
            raise FrameError(f"'{k}' must be a date YYYY-MM-DD, not '{v}'")
        if kind == "page" and not PAGE.match(v):
            raise FrameError(f"'{k}' is a site path that starts and ends with /, not '{v}'")
    return head, args


def items(v: str) -> list[tuple[str, str]]:
    """'a,b:Label' -> [('a', ''), ('b', 'Label')]"""
    out = []
    for part in v.split(","):
        part = part.strip()
        if part:
            i, _, lab = part.partition(":")
            out.append((i.strip(), lab.strip()))
    return out


def rows(v: str) -> list[list[tuple[str, str]]]:
    return [items(r) for r in v.split("|")]


def lines(v: str) -> list[str]:
    """'a line|another line' -> ['a line', 'another line'] (prose lines; commas stay inside a line)"""
    return [x.strip() for x in v.split("|") if x.strip()]


def terms(v: str) -> list[tuple[str, str, str]]:
    """'128,-land-value:Land value,+house:Density' -> [('', '128', ''), ('-', 'land-value', 'Land value'), ('+', 'house', 'Density')]

    An item may open or close a group: '(coins:Wealth,+person:Colonists),×dial:Threat' -> ops '(' and ')' are kept in the
    op string ('(' before, ')' after the item: op '(', label 'Wealth)' is split as op '(' and close ')').
    A number may carry a unit label: '250:points'.
    """
    out = []
    for part in v.split(","):
        part = part.strip()
        op = ""
        if part[:1] in "+-×−" and not NUMBER.match(part) and not re.match(r"^[-−][0-9]", part):
            op, part = part[0].replace("−", "-"), part[1:]
        if part.startswith("("):
            op, part = op + "(", part[1:]
        i, _, lab = part.partition(":")
        i, lab = i.strip(), lab.strip()
        if i.endswith(")"):
            i, op = i[:-1], op + ")"
        if lab.endswith(")"):
            lab, op = lab[:-1].strip(), op + ")"
        out.append((op, i, lab))
    return out


def panels(v: str) -> list[tuple[list[str], str]]:
    """'raid:A raid at the door|grave+person:One falls' -> [(['raid'], 'A raid at the door'), (['grave', 'person'], 'One falls')]"""
    out = []
    for part in v.split("|"):
        ic, _, cap = part.partition(":")
        out.append(([x.strip() for x in ic.split("+") if x.strip()], cap.strip()))
    return out


def numeric(i: str) -> bool:
    return bool(NUMBER.match(i.lstrip("-")))


def icon_refs(template: str, args: dict[str, str]) -> list[str]:
    """Every id in a Frame that is drawn as an element: an icon, or a dataset id (mechanic, technique) that falls back to
    its category icon or a type tile when it has no icon yet."""
    refs: list[str] = []
    for k, v in args.items():
        kind = {**TEMPLATES[template]["keys"], **COMMON}[k]
        if kind == "icon":
            refs.append(v)
        elif kind == "items":
            refs += [i for i, _ in items(v)]
        elif kind == "rows" or (template == "count" and k == "rows" and args.get("kind") == "packages"):
            refs += [i for r in rows(v) for i, _ in r]
        elif kind == "terms":
            refs += [i for _, i, _ in terms(v) if not numeric(i)]
        elif kind == "panels":
            refs += [i for ics, _ in panels(v) for i in ics]
        elif kind in ("mechanics", "elements") and not (template == "timeline" and args.get("kind") == "games"):
            refs += [i for r in v.split("|") for i, _ in items(r)]
    if template == "anatomy" and "game" in args and args.get("parts", "core") not in ("core", "all", "firsts"):
        refs += [i for i, _ in items(args["parts"])]
    return refs


def constants(template: str, args: dict[str, str]) -> list[str]:
    """Numbers a Frame states; each must appear in the text of the record or source named by `from` (E040)."""
    out = []
    if template == "formula":
        out += [i.lstrip("-") for _, i, _ in terms(args.get("terms", "")) if numeric(i)]
    if template == "toysim":
        out += [args[k] for k in ("tick", "rate", "threshold", "levels", "gens") if k in args]
    if template == "count" and args.get("kind") == "units":
        out += [args[k] for k in ("total", "on", "also") if k in args]
    if template == "count" and args.get("kind") == "figures":
        out += [n for r in lines(args["rows"]) for n in re.findall(r"[0-9][0-9,]*(?:\.[0-9]+)?%?", r)]
        out += [c for c, _ in items(args["cols"]) if NUMBER.match(c)]
    if template == "mockup":
        out += [n for x in lines(args.get("lines", "")) + [args.get("title", "")] for n in re.findall(r"(?<![\w-])[0-9][0-9,]*(?:\.[0-9]+)?%?(?![\w-])", x)]
    return out


WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
         "eleven": "11", "twelve": "12", "sixty": "60", "hundred": "100", "thousand": "1000"}


def has_number(n: str, text: str) -> bool:
    """Is the number n stated in text? Commas, number words up to twelve (and sixty, hundred), and % spelled 'percent' count."""
    norm = re.sub(r"(?<=[0-9]),(?=[0-9]{3})", "", text)
    norm = re.sub(r"\b(" + "|".join(WORDS) + r")\b", lambda m: WORDS[m.group(1).lower()], norm, flags=re.I)
    norm = re.sub(r"([0-9])\s*(?:percent|per cent)", r"\1%", norm)
    n = n.replace(",", "")
    pat = r"(?<![0-9.])" + re.escape(n) + (r"(?![0-9])" if not n.endswith("%") else "")
    return bool(re.search(pat, norm)) or (n.endswith("%") and bool(re.search(r"(?<![0-9.])" + re.escape(n[:-1]) + r"\s*%", norm)))
