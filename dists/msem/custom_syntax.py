from shared.types.card import Card, CardFace

produces_exclusions = {'Burning Sulfur', 'Pay Up', 'Xoqal, World Eater', 'The High Prairies Burn'}


class MSEMCardFace(CardFace):
    def process_produces(self) -> None:
        if self.name in produces_exclusions:
            self.produces = []
            self.produces_len = 0
            return

        super().process_produces()


class MSEMCard(Card):
    # faces: list[MSEMCardFace]
    # fixed_faces: list[MSEMCardFace]
    # This doesn't work within MyPy for reasons I don't understand
    pass
