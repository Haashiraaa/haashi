

# Changelog

All notable changes to haashi-analytics-toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.8.1] - 2026-08-19 - Deprecation Notice

### Changed
- Package renamed to `haashi`. This release adds a DeprecationWarning
 on import; no functional changes.

---

## [v1.8.0] - 2026-04-28 - QuickPlot & PowerCanvas Dashboard Engine

### Added
- Introduced `QuickPlot` class in `plot_engine` module for rapid single-method
  plot creation with built-in dark and light theme support.
- Added `QuickPlot.line()` — one-call line plots with optional reference lines,
  markers, legends, and theme-aware styling.
- Added `QuickPlot.bar()` — one-call bar charts with optional value labels,
  rotation control, and reference lines.
- Added `QuickPlot.scatter()` — one-call scatter plots with optional horizontal
  and vertical reference lines.
- Added `QuickPlot.pie()` — one-call pie charts with explode, shadow, and
  custom color support.
- Introduced `PowerCanvas` class for Power BI-style multi-panel dashboard
  composition built on top of `PlotEngine`.
- Added `PowerCanvas.preset_kpi_top()` — preset layout with KPI card row on
  top and chart panels below.
- Added `PowerCanvas.preset_split()` — preset layout with wide chart on the
  left and stacked KPI panels on the right.
- Added `PowerCanvas.preset_full_grid()` — preset even N×M grid of chart panels.
- Added `PowerCanvas.create_canvas()` — flexible grid layout with custom
  height/width ratios and (row, col) tuple panel addressing with col/row span
  support.
- Added `PowerCanvas.add_kpi_card()` — KPI cards with value, label, delta
  indicator, accent bar, and optional sparkline trend chart.
- Added `PowerCanvas.add_bar()`, `add_line()`, `add_scatter()`, `add_pie()`
  — themed chart panels for dashboard composition.
- Added `PowerCanvas.add_stats_panel()` — styled key-value metrics text panel.
- Added `PowerCanvas.render()` — dashboard finalization, export, and display.
- Added `docs/plot_engine.md` — full module documentation covering `PlotEngine`,
  `QuickPlot`, and `PowerCanvas` with examples, parameter references, error
  reference, and type reference.

### Changed
- `PlotEngine` now serves as the shared composition engine for both `QuickPlot`
  and `PowerCanvas`, with no breaking changes to its existing public API.

---


## [v1.6.1] - 2026-04-24 — Improved Logger & Error Handling

### Changed
- Simplified error handling logic in Logger for more consistent messaging.
- Default error message set to "Error occurred!".
- Error messages now include log file path when saving to JSON.
- Ensured logging occurs after optional JSON save operation.
- Improved formatting in DateTimeUtil for better readability.

### Fixed
- Removed inconsistent conditional error message construction.

### Added
- Added staged_changes.diff artifact for tracking staged modifications.

### Removed
- Eliminated redundant whitespace and minor formatting issues.

---

## [v1.6.0] - 2026-03-28

### Added
- New string_format parameter to get_current_time utility.
- Support for returning datetime objects alongside traditional str output.
- Type hint update: get_current_time now returns Union[str, datetime].

### Changed
- Internal refactor of get_current_time for better date vs. datetime handling.
- Optimized formatting logic into a single internal variable.


---

## [v1.5.0] - 2026-03-16

### Added
- Warmup support in Benchmark for more accurate timing results
- Enhanced benchmark internals for improved stability

### Changed
- Minor internal refinements to benchmark reporting


---

## [1.4.0] - 2025-03-05

### Added
- **DataSaver.save_excel()**: New method for exporting DataFrames to Excel (.xlsx) files
  - Full documentation with usage examples
  - Supports pandas DataFrame to Excel conversion
  
- **ScreenUtil.space()**: New method for generating formatted spacing
  - Customizable space count for terminal output
  - Useful for formatted console displays

### Fixed
- Removed redundant `sys` import in ErrorLogger class
  - sys was already imported at module level
  - Cleaner import structure

### Technical Details
This release adds Excel export capability to the DataSaver class. The space()
method improves terminal output formatting capabilities.


___


## [1.3.0] - 2025-03-04

### Added
- **Path Locator Methods**: Dynamic path resolution for script-relative file saving
  - `ErrorLogger.get_script_dir()`: Detect script location regardless of execution directory
  - `FileHandler.get_script_dir()`: Same functionality for file operations
  - `FileHandler.get_parent_path()`: Get parent directory of any path
  - `FileHandler.get_ancestor_by_name()`: Get ancestor directories up to specified depth
  - Ensures logs and data files stay with scripts in production

### Changed
- **Pandas Import Structure**: Consolidated imports for cleaner dependencies
  - Removed duplicate imports of `DataFrame` and `Series`
  - Consolidated to `import pandas as pd`
  - Added module-level aliases: `DataFrame = pd.DataFrame`, `Series = pd.Series`
  - Simplifies imports throughout codebase

### Improved
- Added type hints to `ErrorLogger` class methods
- Added type hints to `FileHandler` class methods
- Improved type safety across utility modules
- Code cleanup and organization improvements
- Better method signatures and documentation

### Fixed
- Import redundancies in `data_engine` module
- Type annotation inconsistencies


---

## [1.2.0] - 2026-03-01

### Added
- **DataFrameFactory**: DataFrame and Series creation without direct pandas import
  - `create_dataframe()`: Create DataFrame from various data structures
  - `create_series()`: Create Series with flexible options
  - `from_records()`: Build DataFrame from list of dictionaries
  - `empty_dataframe()`: Initialize empty DataFrame with columns
  
  
- **Colors utility**: Terminal color output for beautiful CLI
  - Full ANSI color palette (16 colors + styles)
  - Style modifiers: bold, underline, italic

### Changed
- Updated `data_engine/__init__.py` to export DataFrameFactory
- Updated `utility/__init__.py` to export Colors


---

## [1.1.0] - 2026-02-23

### Added
- **New module**: `haashi_pkg.benchmark` for performance profiling
- `Benchmark` class with `measure_time()` method for timing function execution
- `ScreenUtil.wait_and_enter()` method for interactive pausing in pipelines
- Custom exceptions for benchmark module:
  - `BenchmarkError` - Base exception for benchmark operations
  - `InvalidFunctionError` - Raised when function is not callable
  - `BenchmarkTimeoutError` - For future timeout handling

### Example Usage

**Performance Timing:**
```python
from haashi_pkg.benchmark import Benchmark

bench = Benchmark()

def my_function():
    return sum(range(1000000))

# Measure with default 5 runs
avg_time = bench.measure_time(my_function)

# Measure with custom runs for better accuracy
avg_time = bench.measure_time(my_function, run_times=10)
print(f"Average: {avg_time:.4f}s")
```

**Interactive Pausing:**
```python
from haashi_pkg.utility import ScreenUtil as su



# Simple pause
su.wait_and_enter()

# Custom message
su.wait_and_enter("Review the output before continuing...")

# Use in pipeline
def run_pipeline():
    step_1()
    su.wait_and_enter("Check output. Press Enter for step 2...")
    step_2()
```

---

## [1.0.0] - 2026-02-10

### Added
- Initial stable release
- **utility module**:
  - `Logger` class for structured logging with JSON error support
  - `FileHandler` class for file operations (read/write JSON, CSV, etc.)
- **data_engine module**:
  - `DataLoader` for loading CSV, Parquet, Excel files
  - `DataAnalyzer` for data validation, inspection, and analysis
  - `DataSaver` for saving data in multiple formats
- **plot_engine module**:
  - `PlotEngine` for creating professional data visualizations
  - Custom color palettes and themes
  - Support for line plots, bar charts, scatter plots
  - Statistics text boxes and legends

### Changed
- Migrated from deprecated `Utility` class to `Logger`/`FileHandler`
- Improved module organization with clear separation of concerns

### Fixed
- Logger conflicts when initializing `PlotEngine`
- `PlotEngine` now accepts logger parameter to prevent logging hijacking
- Proper error handling in all file operations

---

## Notes

### Version Numbering
- **MAJOR** version: Incompatible API changes
- **MINOR** version: New features (backward compatible)
- **PATCH** version: Bug fixes (backward compatible)

### Contributing
When making changes, add them to the `[Unreleased]` section first.
Move to a versioned section when ready to release.
