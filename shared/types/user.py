from typing import Any

from shared.helpers.util import clean_name
from shared.types.pseudotype import PseudoType


class UserPrivileges(PseudoType):
    full_admin: bool = False
    deck_admin: bool = False
    deck_mod: bool = False

    def serialize(self) -> dict[str, bool]:
        data = {
            'full_admin': self.full_admin or False,
            'deck_admin': self.full_admin or self.deck_admin or False,
            'deck_mod': self.full_admin or self.deck_admin or self.deck_mod or False
        }
        data['some_admin'] = data['deck_mod']
        return data


class User(PseudoType):
    user_id: str = ''
    login: str = ''
    nickname: str
    privileges: UserPrivileges

    def pre_load(self, data: dict) -> None:
        super().pre_load(data)
        self.privileges = UserPrivileges().load(data['privileges'])

    def virtual_save(self) -> dict:
        dct = super().virtual_save()
        dct['privileges'] = self.privileges.save()
        return dct

    def process(self) -> None:
        if not self.user_id:
            self.user_id = clean_name(self.nickname)

    def serialize(self) -> dict[str, Any]:
        return {'user_id': self.user_id, 'nickname': self.nickname,
                'privileges': self.privileges.serialize() if self.privileges else []}
