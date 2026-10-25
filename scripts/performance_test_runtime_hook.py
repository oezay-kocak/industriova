"""Dedicated local diagnostic channel; never selects a release save directory."""
import os

os.environ['PRODUCTION_ZERO_DEV_MODE'] = '1'
os.environ['PRODUCTION_ZERO_PERFORMANCE_TEST'] = '1'
# An older, explicitly enabled research-only tracer has obsolete UI hooks.
# This build supplies its own recorder; the parent environment is unchanged.
os.environ.pop('PRODUCTION_ZERO_RESEARCH_TRACE', None)
