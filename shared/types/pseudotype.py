from typing import Any, TypeVar

T = TypeVar('T', bound='PseudoType')


class PseudoType:
    _processed: bool = False

    def preprocess(self) -> None:
        if not self._processed:
            self._processed = True
            self.process()

    def save(self) -> dict:
        self.preprocess()
        return self.virtual_save()

    def virtual_save(self) -> dict:
        dct = dict(vars(self))
        dct.pop('_processed', None)
        return dct

    def load(self: T, data: dict) -> T:
        self.pre_load(data)
        self.post_load()
        return self

    def pre_load(self, data: dict) -> None:
        for k, v in data.items():
            if k != '_id':
                setattr(self, k, v)

    def post_load(self) -> None:
        pass

    def process(self) -> None:
        pass

    def get(self, u: str, v: Any) -> Any:
        if hasattr(self, u):
            return getattr(self, u)
        return v
