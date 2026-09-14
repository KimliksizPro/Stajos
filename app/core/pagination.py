from flask import request

__all__ = ["get_pagination_params", "paginate_query"]


def get_pagination_params(default_per_page=20, max_per_page=100):
    """Parse and sanitize pagination query params.

    Returns (page, per_page) with silent fallback to defaults on ValueError
    to keep personal-use behavior simple. Spec 5.1 meta requires only
    {page, per_page, total}.
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", default_per_page))
    except ValueError:
        page, per_page = 1, default_per_page
    page = max(1, page)
    per_page = min(max(1, per_page), max_per_page)
    return page, per_page


def paginate_query(query, page, per_page):
    """Paginate a SQLAlchemy query per spec 5.1.

    Returns (items, meta) where meta is {page, per_page, total}.
    """
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination.items, {"page": page, "per_page": per_page, "total": pagination.total}
