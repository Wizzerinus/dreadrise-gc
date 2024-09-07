from unittest import TestCase

from shared.helpers.magic import process_mana_cost, calculate_mana_value, process_mana_cost_dict, add_braces


class TestMana(TestCase):
    def run_all(self):
        self.test_process_mana_cost()

    def test_process_mana_cost(self):
        self.assertEqual(process_mana_cost('{2}{U}{B}'), ['any', 'any', 'blue', 'black'])
        self.assertEqual(process_mana_cost('{W}{R}{G}{G}'), ['white', 'red', 'green', 'green'])
        self.assertEqual(process_mana_cost('{X}{C}{S}{0}'), ['x', 'colorless', 'snow', 'zero'])
        self.assertEqual(process_mana_cost('{W/R}{R/W}{2/U}{B/P}'), ['red/white', 'red/white', '2/blue', 'pblack'])
        self.assertEqual(process_mana_cost('{G/U/P}{G/U/P}'), ['pgreen/blue', 'pgreen/blue'])

    def test_mana_value(self):
        def string_to_mv(u):
            return calculate_mana_value(process_mana_cost_dict(u))

        self.assertEqual(string_to_mv('{2}{U}'), 3)
        self.assertEqual(string_to_mv('{W}{B}{R}{G}'), 4)
        self.assertEqual(string_to_mv('{2/W}{2/B}{2/B}'), 6)
        self.assertEqual(string_to_mv('{0}{0}{100}{C}'), 101)
        self.assertEqual(string_to_mv('{B/P}'), 1)
        self.assertEqual(string_to_mv('{X}{X}'), 0)
        self.assertEqual(string_to_mv('{X}{R}{R}{R}'), 3)
        self.assertEqual(string_to_mv('{G/U/P}'), 1)

    def test_braces(self):
        self.assertEqual(add_braces("2R"), "{2}{R}")
        self.assertEqual(add_braces("12R"), "{12}{R}")
        self.assertEqual(add_braces("R/BG"), "{R/B}{G}")
        self.assertEqual(add_braces("R/BVpR"), "{R/B}{Vp}{R}")
