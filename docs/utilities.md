
# Utilities: DateTime, ScreenUtil, Colors

## DateTime

Timezone-aware "now" at a **fixed UTC offset**.

```python
DateTime.get_current_time(utc_offset_hours=0, string_format=True, only_date=True)
```

| Parameter | Description |
|---|---|
| `utc_offset_hours` | -12 to +14. Fractions allowed (`5.5` India, `5.75` Nepal). |
| `string_format` | `True` returns a `str`; `False` returns a timezone-aware `datetime`. |
| `only_date` | For strings: `YYYY-MM-DD` if `True`, else `YYYY-MM-DD HH:MM:SS`. Ignored for datetimes. |

```python
DateTime.get_current_time(1)                          # '2026-10-03'
DateTime.get_current_time(1, only_date=False)         # '2026-10-03 14:05:11'
DateTime.get_current_time(5.5, string_format=False)   # datetime(..., tzinfo=UTC+05:30)
```

Typing: overloads return `str` for `string_format=True` and `datetime` for `string_format=False`, so your type checker knows which you get.

Raises `ValueError` if the offset is outside -12..+14.

> Fixed offset only: no zone names and no daylight-saving handling. Use `zoneinfo` for those.

## ScreenUtil

Static terminal helpers.

### `animate(text="Loading", cycles=2, delay=0.5)`

Prints a dot animation on one line (`Loading.` → `Loading..` → `Loading...`), one dot per `delay` seconds; one cycle is three dots. The cursor stays at the end of the line, so call `print()` afterwards.

```python
ScreenUtil.animate("Processing", cycles=3, delay=0.3)
print()
```

### `format_text(text, width=70) -> str`

Wraps each line to `width` characters via `textwrap`. Blank lines are preserved, so paragraphs stay separated.

```python
print(ScreenUtil.format_text(long_text, width=60))
```

## Colors

ANSI escape codes as class attributes, plus helpers.

| Group | Names |
|---|---|
| Reset | `RESET` |
| Foreground | `BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE` |
| Bright foreground | `BRIGHT_BLACK` … `BRIGHT_WHITE` |
| Background | `BG_BLACK` … `BG_WHITE` |
| Styles | `BOLD DIM ITALIC UNDERLINE BLINK REVERSE HIDDEN STRIKETHROUGH` |

| Helper | Output |
|---|---|
| `Colors.colored(text, color, style=None)` | any color, optional style |
| `Colors.debug(text)` | dim cyan |
| `Colors.info(text)` | bold blue |
| `Colors.warning(text)` | bold yellow |
| `Colors.error(text)` | bold red |
| `Colors.success(text)` | bold green |
| `Colors.header(text)` | bold underlined cyan |

```python
print(Colors.success("Build passed"))
print(Colors.colored("custom", Colors.MAGENTA, Colors.BOLD))
print(f"{Colors.CYAN}raw codes{Colors.RESET}")
```

> `Colors` **always** emits ANSI codes. Only [`Logger`](logger.md#color-rules) detects terminals and honors `NO_COLOR`. If you print colors to files or pipes yourself, check `sys.stdout.isatty()` first.
