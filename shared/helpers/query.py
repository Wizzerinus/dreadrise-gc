def deck_privacy(query: dict, username: str | None, show_unlisted: bool = False, is_admin: bool = False) -> dict:
    if is_admin:
        return query
    privacy_list = ['private']
    if not show_unlisted:
        privacy_list.append('unlisted')
    return {
        '$and': [
            query,
            {
                '$or': [
                    {'author': username},
                    {'privacy': {'$nin': privacy_list}}
                ]
            }
        ]
    }
