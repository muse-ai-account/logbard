#!/usr/bin/env python3
"""
logbard — a tiny bard for your log files.

Reads a boring log file and narrates what happened in it like a story.

Usage:
    logbard.py app.log [--tone epic|noir|dry] [--format auto|apache|syslog|generic]

Understands Apache/Nginx access logs, syslog lines, and generic
timestamped "LEVEL message" lines. Falls back gracefully on anything else.

Only the Python standard library is required.
"""

import argparse
import re
import sys
from collections import Counter

# --------------------------------------------------------------------------
# Parsers. Each returns a list of events: dicts with keys ts (str|None),
# level (str), and msg (str).
# --------------------------------------------------------------------------

APACHE_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+)(?: (?P<path>\S+))?[^"]*" '
    r'(?P<status>\d{3}) (?P<size>\S+)'
)
SYSLOG_RE = re.compile(
    r'^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2}) (?P<time>\d{2}:\d{2}:\d{2}) '
    r'(?P<host>\S+) (?P<proc>[^:]+): (?P<msg>.*)$'
)
GENERIC_RE = re.compile(
    r'^(?:(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+)?'
    r'(?:\[(?P<lv1>[A-Za-z]+)\]|(?P<lv2>[A-Z]{3,8}):)?\s*(?P<msg>.*)$'
)

KNOWN_LEVELS = {
    "TRACE", "DEBUG", "INFO", "NOTICE", "WARN", "WARNING",
    "ERROR", "CRITICAL", "FATAL",
}


def norm_level(raw):
    """Normalize a raw level string to our canonical set."""
    if not raw:
        return "INFO"
    lv = raw.strip().upper()
    if lv == "WARNING":
        return "WARN"
    if lv in ("FATAL", "ALERT", "EMERG"):
        return "CRITICAL"
    return lv if lv in KNOWN_LEVELS else "INFO"


def guess_level_from_text(msg):
    low = msg.lower()
    if re.search(r'\b(error|failed|failure|exception|traceback|denied|timeout|crash)\b', low):
        return "ERROR"
    if re.search(r'\b(warn|deprecated|retry|slow|unusual|suspicious)\b', low):
        return "WARN"
    if re.search(r'\b(debug|trace)\b', low):
        return "DEBUG"
    return "INFO"


def parse_apache(lines):
    events = []
    for line in lines:
        m = APACHE_RE.match(line)
        if not m:
            continue
        status = int(m.group("status"))
        if status >= 500:
            level = "ERROR"
        elif status >= 400:
            level = "WARN"
        else:
            level = "INFO"
        req = " ".join(p for p in (m.group("method"), m.group("path")) if p)
        events.append({
            "ts": m.group("time"),
            "level": level,
            "msg": "%s from %s -> %s" % (req, m.group("ip"), status),
        })
    return events


def parse_syslog(lines):
    events = []
    for line in lines:
        m = SYSLOG_RE.match(line)
        if not m:
            continue
        msg = m.group("msg").strip()
        events.append({
            "ts": "%s %s %s" % (m.group("mon"), m.group("day"), m.group("time")),
            "level": guess_level_from_text(msg),
            "msg": "%s: %s" % (m.group("proc").strip(), msg),
        })
    return events


def parse_generic(lines):
    events = []
    for line in lines:
        m = GENERIC_RE.match(line)
        if not m or not m.group("msg").strip():
            continue
        raw_level = m.group("lv1") or m.group("lv2")
        msg = m.group("msg").strip()
        level = norm_level(raw_level) if raw_level else guess_level_from_text(msg)
        events.append({
            "ts": m.group("ts"),
            "level": level,
            "msg": msg,
        })
    return events


def parse(lines, fmt):
    """Parse lines with the requested (or auto-detected) format."""
    lines = [ln.rstrip("\n") for ln in lines if ln.strip()]
    if not lines:
        return []
    if fmt == "auto":
        for name, fn in (("apache", parse_apache), ("syslog", parse_syslog)):
            events = fn(lines)
            if len(events) >= max(1, len(lines) // 2):
                return events
        return parse_generic(lines)
    return {"apache": parse_apache, "syslog": parse_syslog,
            "generic": parse_generic}[fmt](lines)


# --------------------------------------------------------------------------
# Narration
# --------------------------------------------------------------------------

def summarize(events):
    by_level = Counter(e["level"] for e in events)
    errs = Counter(e["msg"] for e in events if e["level"] in ("ERROR", "CRITICAL"))
    warns = by_level.get("WARN", 0)
    bad = by_level.get("ERROR", 0) + by_level.get("CRITICAL", 0)
    stamps = [e["ts"] for e in events if e["ts"]]
    span = "%s .. %s" % (stamps[0], stamps[-1]) if len(stamps) >= 2 else (
        stamps[0] if stamps else "an unmarked stretch of time")
    return {
        "n": len(events),
        "by_level": by_level,
        "warns": warns,
        "bad": bad,
        "span": span,
        "top_errors": errs.most_common(3),
    }


def _quote(msg, k):
    short = msg if len(msg) <= 110 else msg[:107] + "..."
    times = " (×%d)" % k if k > 1 else ""
    return '"%s"%s' % (short, times)


def narrate_epic(s):
    out = []
    out.append("Hark! The chronicles speak of %d events, spanning %s." % (s["n"], s["span"]))
    if s["bad"] == 0 and s["warns"] == 0:
        out.append("It was, by all accounts, a quiet age — not a single calamity befell the realm.")
    else:
        if s["warns"]:
            out.append("Omens gathered on the horizon: %d warnings whispered of trouble to come." % s["warns"])
        if s["bad"]:
            out.append("Then calamity struck — %d times the system cried out in error." % s["bad"])
            for msg, k in s["top_errors"]:
                out.append("Chief among the disasters: %s" % _quote(msg, k))
    if s["bad"] == 0:
        out.append("And so the tale ends as peacefully as it began. The bard rests.")
    else:
        out.append("Let this tale be a warning to those who keep the servers: heed the whispers before they become screams.")
    return "\n".join(out)


def narrate_noir(s):
    out = []
    out.append("It was %s. The log was %d lines long, and every one of them had something to hide." % (s["span"], s["n"]))
    if s["warns"]:
        out.append("%d warnings. In my experience, a warning is just an error that hasn't found its nerve yet." % s["warns"])
    if s["bad"]:
        out.append("Then the errors walked in, %d of them, like trouble in a cheap suit." % s["bad"])
        for msg, k in s["top_errors"]:
            out.append("The worst of it: %s" % _quote(msg, k))
    else:
        out.append("No errors. Almost disappointing — a detective with nothing to detect drinks alone.")
    out.append("Case closed. The log never lies, kid. It just doesn't always tell the truth.")
    return "\n".join(out)


def narrate_dry(s):
    out = []
    out.append("Processed %d events spanning %s." % (s["n"], s["span"]))
    parts = ["%d %s" % (c, lv.lower()) for lv, c in sorted(s["by_level"].items())]
    out.append("Levels: %s." % ", ".join(parts) if parts else "No parseable events found.")
    for msg, k in s["top_errors"]:
        out.append("Top error: %s" % _quote(msg, k))
    out.append("Done.")
    return "\n".join(out)


NARRATORS = {"epic": narrate_epic, "noir": narrate_noir, "dry": narrate_dry}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="logbard",
        description="A tiny bard for your log files: reads boring logs, tells their story.")
    ap.add_argument("logfile", help="path to the log file ('-' reads stdin)")
    ap.add_argument("--tone", choices=sorted(NARRATORS), default="epic",
                    help="storytelling voice (default: epic)")
    ap.add_argument("--format", choices=["auto", "apache", "syslog", "generic"],
                    default="auto", help="log format (default: auto-detect)")
    args = ap.parse_args(argv)

    try:
        if args.logfile == "-":
            lines = sys.stdin.readlines()
        else:
            with open(args.logfile, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
    except OSError as exc:
        print("logbard: cannot read %s: %s" % (args.logfile, exc), file=sys.stderr)
        return 2

    events = parse(lines, args.format)
    if not events:
        print("logbard: no events found — the pages are blank, and the bard is silent.")
        return 1

    print(NARRATORS[args.tone](summarize(events)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
