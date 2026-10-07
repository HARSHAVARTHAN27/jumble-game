import re


def normalize_name(name: str) -> str:
    """Normalize employee name: trim, lowercase, remove repeated spaces."""
    name = name.strip()
    name = name.lower()
    name = re.sub(r'\s+', ' ', name)
    return name


def is_name_duplicate(supabase, normalized_name: str, employee_id: str = None) -> bool:
    """Check if there are duplicate employees with the same normalized name."""
    query = supabase.from_('employees').select('id, name').eq('normalized_name', normalized_name)
    if employee_id:
        query = query.neq('id', employee_id)
    result = query.execute()
    return len(result.data) > 1


def find_employee(supabase, normalized_name: str, employee_code: str = None) -> dict:
    """Find employee by normalized name, optionally filtering by employee code."""
    query = supabase.from_('employees').select('*').eq('normalized_name', normalized_name)
    if employee_code:
        query = query.eq('employee_code', employee_code)
    result = query.execute()
    if not result.data:
        return None
    if len(result.data) > 1 and not employee_code:
        return None  # ambiguous, need employee code
    return result.data[0]