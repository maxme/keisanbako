# Keisanbako Calculator

A desktop calculator (PySide6) with live evaluation, currency and unit conversion, and date arithmetic. Available in English, Spanish, French, Japanese, and Chinese (Simplified and Traditional).

## Features

- **Arithmetic and functions** - `+ - * / **`, `sqrt`, trig, `log`, `exp`, and more
- **Date arithmetic** - `today() + 30 days`, `date(2026, 12, 25) - today()`
- **Currency conversion** - `100 USD in EUR`, `1000 yen to gbp` (rates fetched over the network, with a cache)
- **Unit conversion** - length, area, speed, temperature, weight
- **Live results** - the result updates as you type (debounced)
- **History** - calculations are saved to `~/.keisanbako_history.json`
- **Settings and themes** - dark and light themes, saved to `~/.keisanbako_settings.json`
- **Safe evaluation** - expressions are parsed and evaluated through a whitelist, not with `eval` on raw input

## Installation

Requires Python 3.10 or newer.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

This installs the `keisanbako` command.

## Running

```bash
keisanbako
```

From a source checkout without installing:

```bash
PYTHONPATH=src python -m Keisanbako.calculator
```

Or with the Makefile: `make run`.

## Using the evaluator from Python

```python
from Keisanbako.evaluator import ExpressionEvaluator

evaluator = ExpressionEvaluator()

evaluator.evaluate("100 * 5 + 2").value        # "502"
evaluator.evaluate("sqrt(144)").value          # "12.0"
evaluator.evaluate("today() + 30 days").value  # e.g. "2026-11-29"
```

`evaluate()` returns a `CalculationResult` with `value` and `is_error`.

## Project structure

```
src/Keisanbako/
├── calculator.py        # Entry point (main)
├── ui.py                # PySide6 widgets
├── evaluator.py         # ExpressionEvaluator: safe evaluation
├── parser.py            # Expression parsing and preprocessing
├── converters.py        # Currency and unit conversion, request cache
├── settings.py          # Settings persistence
├── settings_dialog.py   # Settings UI
├── themes.py            # Dark and light styling
├── translations.py      # i18n loader
├── translations/*.json  # Strings per language
├── workers.py           # Background threads
├── network_status.py    # Connectivity checks
└── constants.py         # Window size, timeouts, colors, file paths
tests/                   # pytest suite
scripts/                 # Icon conversion, macOS DMG creation
linux/, windows/         # Desktop integration and installer files
```

## Testing

```bash
pytest
```

The suite has 356 tests. At the time of writing, 332 pass and 24 fail:

- 23 failures in `tests/test_calculator.py` (`TestUnitConversion`): the conversion results do not match the expected values, for example `'50.0'` is returned where `'50'` is expected.
- 1 failure in `tests/test_edge_cases.py` (`test_long_variable_names`).

Some test modules import `requests`, which is not declared in `pyproject.toml` and is not used by the application itself. Install it to run the suite: `pip install requests`.

Use `QT_QPA_PLATFORM=offscreen` to run the GUI tests on a machine without a display.

## Build and packaging

The Makefile wraps the build scripts:

| Target | Purpose |
| --- | --- |
| `make build` | Build for the current platform (Nuitka scripts) |
| `make build-macos` / `build-linux` / `build-windows` | Platform builds |
| `make install-macos` / `install-linux` | Install the build |
| `make dmg` | Create a macOS DMG |
| `make icons` | Convert `assets/keisanbako_icon.svg` to all icon formats |
| `make test` | Run the test suite verbosely |
| `make check` | Format, lint, and type-check |
| `make clean` / `make clean-all` | Remove build outputs (and generated icons) |

Run `make help` for the full list.

## Development

```bash
black src/ tests/          # Format (line length 100)
ruff check src/ tests/     # Lint
mypy src/Keisanbako/       # Type-check
```

Roadmap and past refactoring notes are in [TODO.md](TODO.md). Build notes are in [BUILD_OPTIMIZATION.md](BUILD_OPTIMIZATION.md).

## Known issues

- The 24 failing tests listed above.
- Currency conversion depends on the Frankfurter (`api.frankfurter.app`) and CoinGecko APIs, so it needs network access.
- No `LICENSE` file is included yet. The project metadata declares MIT.

## Contributing

1. Create a feature branch.
2. Add tests for new behaviour.
3. Run `pytest` and make sure no new failures are introduced.
4. Open a pull request.
