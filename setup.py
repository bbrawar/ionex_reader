"""
setup.py — ionex_reader
=======================
Legacy setup script kept for compatibility with  pip install .
For new builds, prefer:  python -m build  (uses pyproject.toml if present).
"""

from setuptools import setup, find_packages
from os import path

# ---------------------------------------------------------------------------
# Read long description from README.md (shown on PyPI)
# ---------------------------------------------------------------------------
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# ---------------------------------------------------------------------------
# Read version / author / email from the single source of truth in ionex.py
# so that setup.py never drifts out of sync with the package itself.
# ---------------------------------------------------------------------------
_meta = {}
with open(path.join(here, 'ionex_reader', 'ionex.py'), encoding='utf-8') as f:
    for line in f:
        for key in ('__version__', '__author__', '__email__'):
            if line.startswith(key):
                _meta[key] = line.split('=', 1)[1].strip().strip("'\"")

setup(
    # --- identity ---
    name             = 'ionex_reader',
    version          = _meta['__version__'],
    description      = (
        'Read, process, and visualise IONEX ionospheric TEC maps '
        'as xarray Datasets'
    ),
    long_description             = long_description,
    long_description_content_type= 'text/markdown',

    # --- authorship ---
    author       = _meta['__author__'],
    author_email = _meta['__email__'],

    # --- project URLs ---
    url         = 'https://github.com/bbrawar/ionex_reader',
    project_urls= {
        'Bug Reports': 'https://github.com/bbrawar/ionex_reader/issues',
        'Source'     : 'https://github.com/bbrawar/ionex_reader',
    },

    # --- licence ---
    license = 'MIT',

    # --- classifiers  (https://pypi.org/classifiers/) ---
    classifiers = [
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',

        'Topic :: Scientific/Engineering :: Atmospheric Science',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering :: Physics',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',

        'Operating System :: OS Independent',
    ],

    keywords = (
        'ionex tec ionosphere gnss gps space-weather '
        'xarray cartopy geophysics'
    ),

    # --- packages ---
    packages         = find_packages(exclude=['tests*', 'docs*']),
    python_requires  = '>=3.9',

    # --- runtime dependencies ---
    # Pin only a minimum version; let the user's environment resolve upper bounds.
    install_requires = [
        'numpy>=1.21,<2',
        'xarray>=0.19',
        'matplotlib>=3.4',
        'cartopy>=0.20',
    ],

    # --- optional extras ---
    extras_require = {
        # pip install ionex_reader[geomag]
        'geomag': ['geomag'],
        # pip install ionex_reader[dev]
        'dev': [
            'pytest>=7',
            'pytest-cov',
            'ruff',           # linter
            'build',          # python -m build
            'twine',          # upload to PyPI
        ],
    },

    # --- no non-Python data files needed ---
    include_package_data = False,
)
