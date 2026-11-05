"""Resolving API keys to tenants and their owning organisations."""


def tenant_for_key(api_key, key_index):
    """Map an API key to the tenant ID it belongs to."""
    return key_index.get(api_key)


def org_for_tenant(tenant_id, tenants):
    record = tenants.get(tenant_id)
    if record is None:
        return None
    return record["org_id"]


def sibling_tenants(tenant_id, tenants):
    """Every other tenant under the same organisation."""
    org_id = org_for_tenant(tenant_id, tenants)
    if org_id is None:
        return []
    return [tid for tid, rec in tenants.items()
            if rec["org_id"] == tenant_id and tid != tenant_id]


def resolve_request(api_key, key_index, tenants):
    tenant_id = tenant_for_key(api_key, key_index)
    if tenant_id is None:
        return None

    org_id = org_for_tenant(tenant_id, tenants)
    return {
        "tenant_id": tenant_id,
        "org_id": org_id,
        "siblings": sibling_tenants(tenant_id, tenants),
    }
