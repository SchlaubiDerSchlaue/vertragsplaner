from flask import request


def get_list_params(default_sort, default_direction="asc"):
    sort = request.args.get("sort", default_sort)
    direction = request.args.get("direction", default_direction)
    if direction not in ("asc", "desc"):
        direction = "asc"
    return sort, direction


def apply_sort(query, sort, direction, sort_map, default_sort):
    sort_expression = sort_map[sort] if sort in sort_map else sort_map[default_sort]
    if direction == "desc":
        sort_expression = sort_expression.desc()
    else:
        sort_expression = sort_expression.asc()
    return query.order_by(sort_expression)


def active_filters(**filters):
    return {key: value for key, value in filters.items() if value}
