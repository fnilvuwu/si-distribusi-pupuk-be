"""
Database-agnostic date utility functions.

This module provides helper functions for date calculations that work
identically across SQLite and PostgreSQL without database-specific SQL.
"""

from datetime import date, datetime, timedelta
from typing import Tuple

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback if dateutil not installed yet
    relativedelta = None


def get_day_boundaries(target_date: date) -> Tuple[datetime, datetime]:
    """
    Get start and end datetime boundaries for a specific day.
    
    Args:
        target_date: The date to get boundaries for
        
    Returns:
        Tuple of (start_datetime, end_datetime) where end is exclusive
        
    Example:
        >>> start, end = get_day_boundaries(date(2026, 2, 6))
        >>> # start = datetime(2026, 2, 6, 0, 0, 0)
        >>> # end = datetime(2026, 2, 7, 0, 0, 0)
    """
    start = datetime.combine(target_date, datetime.min.time())
    end = start + timedelta(days=1)
    return start, end


def get_month_boundaries(year: int, month: int) -> Tuple[date, date]:
    """
    Get start and end date boundaries for a specific month.
    
    Args:
        year: Year (e.g., 2026)
        month: Month (1-12)
        
    Returns:
        Tuple of (start_date, end_date) where end is exclusive
        
    Example:
        >>> start, end = get_month_boundaries(2026, 2)
        >>> # start = date(2026, 2, 1)
        >>> # end = date(2026, 3, 1)
    """
    start = date(year, month, 1)
    
    if relativedelta:
        # Use dateutil for accurate month arithmetic
        end = start + relativedelta(months=1)
    else:
        # Fallback implementation
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)
    
    return start, end


def get_year_boundaries(year: int) -> Tuple[date, date]:
    """
    Get start and end date boundaries for a specific year.
    
    Args:
        year: Year (e.g., 2026)
        
    Returns:
        Tuple of (start_date, end_date) where end is exclusive
        
    Example:
        >>> start, end = get_year_boundaries(2026)
        >>> # start = date(2026, 1, 1)
        >>> # end = date(2027, 1, 1)
    """
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    return start, end


def format_date_for_api(dt: datetime | date | None) -> str | None:
    """
    Consistently format dates for API responses.
    
    Args:
        dt: datetime or date object to format, or None
        
    Returns:
        Formatted string or None if input is None
        
    Examples:
        >>> format_date_for_api(datetime(2026, 2, 6, 14, 30, 45))
        '2026-02-06 14:30:45'
        >>> format_date_for_api(date(2026, 2, 6))
        '2026-02-06'
        >>> format_date_for_api(None)
        None
    """
    if dt is None:
        return None
    
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(dt, date):
        return dt.strftime('%Y-%m-%d')
    else:
        # Handle string passthrough
        return str(dt)


def extract_hour_from_datetime(dt: datetime | str | None) -> int | None:
    """
    Extract hour (0-23) from datetime.
    
    Args:
        dt: datetime object or ISO format datetime string
        
    Returns:
        Hour as integer (0-23), or None if input is None
    """
    if dt is None:
        return None
    
    # Handle string input from database drivers
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    return dt.hour


def extract_month_from_date(dt: date | datetime | str | None) -> int | None:
    """
    Extract month (1-12) from date or datetime.
    
    Args:
        dt: date or datetime object, or ISO format date/datetime string
        
    Returns:
        Month as integer (1-12), or None if input is None
    """
    if dt is None:
        return None
    
    # Handle string input from database drivers
    if isinstance(dt, str):
        try:
            # Try parsing as datetime first
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try parsing as date
                dt = date.fromisoformat(dt)
            except (ValueError, AttributeError):
                return None
    
    return dt.month


def extract_date_from_datetime(dt: datetime | str | None) -> date | None:
    """
    Extract date portion from datetime.
    
    Args:
        dt: datetime object or ISO format datetime string
        
    Returns:
        date object, or None if input is None
    """
    if dt is None:
        return None
    
    # Handle string input from database drivers
    if isinstance(dt, str):
        try:
            # Try parsing as datetime
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Already a date string, parse directly
                return date.fromisoformat(dt)
            except (ValueError, AttributeError):
                return None
    
    return dt.date()
