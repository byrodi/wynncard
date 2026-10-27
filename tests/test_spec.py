import json
import unittest

from test_card import INFO, LISTING
from wynncard import Identification, Item, Requirements, Shiny, from_dict, from_market, render_image, rolls, to_dict


class SpecTest(unittest.TestCase):
    ITEMS = (
        from_market(LISTING, INFO, [{"profile": "Main", "score": 94.6}]),
        Item("Test Ring", tier="rare", kind="accessory", type="ring", health=300, restriction="quest_item",
             requirements=Requirements(level=50, quest="A Very Long Quest Name", agility=20),
             identifications=[Identification("Custom Stat", 5, "%", roll=50.0),
                              Identification.from_api("walkSpeed", -10, roll=12.0)],
             overall_roll=31.0, rerolls=2, shiny=Shiny("Mobs Killed", 1234)),
    )

    def test_round_trip_through_json_draws_the_same_card(self):
        for item in self.ITEMS:
            again = from_dict(json.loads(json.dumps(to_dict(item))))
            self.assertEqual(render_image(again, scale=2).tobytes(), render_image(item, scale=2).tobytes(), item.name)
            self.assertEqual(to_dict(again), to_dict(item))

    def test_defaults_are_left_out(self):
        self.assertEqual(to_dict(Item("Plain")), {"name": "Plain"})
        stats = to_dict(self.ITEMS[1])["identifications"]
        self.assertEqual(stats, [{"stat": "Custom Stat", "value": 5, "roll": 50.0, "unit": "%"},
                                 {"stat": "MISC_WALK_SPEED", "value": -10, "roll": 12.0}])

    def test_api_names_and_overrides(self):
        item = from_dict({"name": "x", "identifications": [
            {"stat": "manaRegen", "value": 12}, {"stat": "Shiny Power", "value": 3, "unit": " tier", "inverted": True}]})
        known, custom = item.identifications
        self.assertEqual((known.key, known.name, known.unit, known.roll), ("MISC_MANA_REGEN", "Mana Regen", "/5s", None))
        self.assertEqual((custom.name, custom.unit, custom.inverted), ("Shiny Power", " tier", True))

    def test_bad_input_names_the_key(self):
        for data, message in (
                ({}, "name must be a string"),
                ({"name": ""}, "name must not be empty"),
                ({"name": "x", "colour": "red"}, "unknown item key: colour"),
                ({"name": "x", "tier": 5}, "tier must be a string"),
                ({"name": "x", "health": True}, "health must be a whole number"),
                ({"name": "x", "damage": {"fire": [1]}}, "damage.fire must be a [low, high] pair"),
                ({"name": "x", "requirements": {"level": "98"}}, "requirements.level must be a whole number"),
                ({"name": "x", "identifications": [{"stat": "manaRegen"}]}, "identification value must be a number"),
                ({"name": "x", "shiny": {"name": "Kills"}}, "shiny.value must be a whole number")):
            with self.assertRaises(ValueError, msg=data) as caught:
                from_dict(data)
            self.assertEqual(str(caught.exception), message)


class RollsTest(unittest.TestCase):
    def test_positive_base_rolls_30_to_130_percent(self):
        self.assertEqual(rolls.values(30), list(range(9, 40)))  # the API's min 9 and max 39 for manaRegen 30
        self.assertEqual(rolls.values(300)[:3], [90, 93, 96])  # a big base skips values

    def test_halves_round_like_wynntils(self):
        self.assertEqual(rolls.values(5), [2, 3, 4, 5, 6, 7])  # 1.5 and 6.5 round away from zero
        self.assertEqual(rolls.values(-5, inverted=True), [-1, -2, -3, -4, -5, -6])  # spell costs round towards it

    def test_negative_base_rolls_70_to_130_percent(self):
        self.assertEqual(rolls.values(-10), [-13, -12, -11, -10, -9, -8, -7])  # less negative is better
        self.assertEqual(rolls.percentage(-7, -10), 100)
        self.assertEqual(rolls.percentage(-13, -10), 0)

    def test_spell_cost_reduction_is_best_at_its_largest(self):
        self.assertEqual(rolls.values(-2, inverted=True), [-1, -2, -3])  # the API's min -1 and max -3
        self.assertEqual(rolls.percentage(-14, -11, inverted=True), 100)
        self.assertEqual(rolls.percentage(-3, -11, inverted=True), 0)
        self.assertEqual(rolls.values(5, inverted=True), [7, 6, 5, 4])  # a cost increase is best at its smallest

    def test_a_single_possible_value_has_no_percentage(self):
        self.assertEqual(rolls.values(1), [1])
        self.assertIsNone(rolls.percentage(1, 1))


if __name__ == "__main__":
    unittest.main()
