"""Research industry names from the authoritative domain mapping."""
from production_zero.core.research import research_catalog, research_domains


def research_category(resource_id):
    domain = research_domains().get(resource_id)
    tree = research_catalog()[0].get('industry.' + domain) if domain else None
    return tree.name if tree else ''
