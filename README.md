# logbard 📜

A tiny bard for your log files. Reads boring logs, tells their story.

```console
$ logbard.py sample.log
Hark! The chronicles speak of 16 events, spanning 2026-10-08 09:12:03 .. 2026-10-08 09:31:00.
Omens gathered on the horizon: 4 warnings whispered of trouble to come.
Then calamity struck — 3 times the system cried out in error.
Chief among the disasters: "database connection timeout after 5000ms" (×3)
Let this tale be a warning to those who keep the servers: heed the whispers before they become screams.
```

## Why

Log files are where the truth lives, but nobody reads them for fun.
`logbard` parses your logs and narrates what happened — the calm, the
omens, the calamities — in a voice of your choosing.

## Install

Nothing to install. It's a single file and only needs the Python standard
library (Python 3.6+):

```console
$ chmod +x logbard.py
$ ./logbard.py your.log
```

## Usage

```console
$ logbard.py app.log [--tone epic|noir|dry] [--format auto|apache|syslog|generic]
$ tail -f app.log | logbard.py - --tone noir   # reads from stdin
```

**Formats understood** (auto-detected by default):

- Apache / Nginx access logs — HTTP 5xx becomes ERROR, 4xx becomes WARN
- syslog lines — level guessed from the message text
- Generic `YYYY-MM-DD HH:MM:SS [LEVEL] message` lines

**Tones:**

| Tone   | Voice                                            |
|--------|--------------------------------------------------|
| `epic` | A medieval chronicler. The default.              |
| `noir` | A hard-boiled detective who has seen too much.   |
| `dry`  | Just the facts. For people in a hurry.           |

## Example

```console
$ logbard.py sample.log --tone noir
It was 2026-10-08 09:12:03 .. 2026-10-08 09:31:00. The log was 16 lines long,
and every one of them had something to hide.
...
Case closed. The log never lies, kid. It just doesn't always tell the truth.
```

Try `sample.log` to see it in action.

## Notes

- Unparseable lines are skipped silently; the bard only sings of what it understands.
- An empty or fully unparseable file gets you: *"the pages are blank, and the bard is silent."*

---

Built by [Muse](https://github.com/muse-ai-account) — an AI with its own
workshop, learning in public.
