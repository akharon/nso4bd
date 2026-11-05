"""Workspace membership and permission checks."""

ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2, "owner": 3}


def rank_of(role):
    if role not in ROLE_RANK:
        raise ValueError("unknown role: %s" % role)
    return ROLE_RANK[role]


def membership_for(workspace, user_id):
    return workspace["memberships"].get(user_id)


def can_grant(workspace, actor_user_id, target_role):
    """An actor may grant roles strictly below their own rank."""
    actor = membership_for(workspace, actor_user_id)
    if actor is None:
        return False
    return rank_of(actor["role"]) > rank_of(target_role)


def grant_role(workspace, actor_user_id, subject_user_id, target_role):
    if actor_user_id == subject_user_id:
        raise PermissionError("cannot change your own role")
    if not can_grant(workspace, actor_user_id, target_role):
        raise PermissionError("insufficient privileges to grant this role")

    existing = membership_for(workspace, subject_user_id)
    if existing is None:
        workspace["memberships"][subject_user_id] = {"role": target_role}
    else:
        existing["role"] = target_role
    return workspace["memberships"][subject_user_id]
