"""Paging through a workspace member roster by stable member ID."""


def sorted_member_ids(workspace):
    """Member IDs in a stable order, so pages do not shift between calls."""
    return sorted(workspace["members"].keys())


def page_of_members(workspace, page_number, page_size):
    """Return the members on `page_number`, which is 1-indexed."""
    member_ids = sorted_member_ids(workspace)
    if page_number < 1:
        return []

    start = (page_number - 1) * page_size
    end = start + page_size
    return [workspace["members"][mid] for mid in member_ids[start:end]]


def page_count(workspace, page_size):
    total = len(workspace["members"])
    if page_size <= 0:
        return 0
    return (total + page_size - 1) // page_size


def find_page_of(workspace, member_id, page_size):
    """Which 1-indexed page does this member appear on?"""
    member_ids = sorted_member_ids(workspace)
    if member_id not in member_ids:
        return None
    position = member_ids.index(member_id)
    return (position // page_size) + 1
