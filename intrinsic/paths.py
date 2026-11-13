"""Project-level paths, so modules do not depend on where they sit in the tree."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
CACHE_DIR = os.path.join(ROOT, '.intrinsic_cache')
RESULTS_DIR = os.path.join(ROOT, 'validation', 'results')
