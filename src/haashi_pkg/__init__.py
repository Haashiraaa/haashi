

# haashi_pkg/__init__.py



"""haashi_pkg - Data analysis, visualization, and utility toolkit."""

import warnings

warnings.warn(
    "haashi_pkg is deprecated and will no longer be updated. "
    "It has been renamed to 'haashi' (pip install haashi), though note "
    "data_engine and plot_engine were removed in that rewrite. "
    "See https://github.com/Haashiraaa/haashi#migration",
    DeprecationWarning,
    stacklevel=2,
)


from . import utility
from . import data_engine
from . import plot_engine
from . import benchmark



__version__ = "1.8.1"

__all__ = [
    'utility',
    'data_engine',
    'plot_engine',
    'benchmark'
]
