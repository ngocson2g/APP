# apps/dashboard/backend/reader/__init__.py
from .detail_reader import get_rule_detail
from .run_reader import list_runs
from .summary_reader import get_summary, get_timeseries, list_rules

__all__ = ['list_runs', 'get_summary', 'list_rules', 'get_timeseries', 'get_rule_detail']
