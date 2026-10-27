import unittest

from wynncard import render_image, rolls, wynntils

# Copied from Wynncraft chat as Wynntils shares it: a Weathered with two rerolls and three empty powder slots.
WEATHERED_CODE = "󰀂󰄀󰉗󶕡󷑨󶕲󶕤󰀃󰔀󲌔󰐊󴔨󰐐󱅇󰐟󰐴󰐣󵄺󰐛󰐃󰀅󰋿"
WEATHERED_INFO = {
    "internalName": "Weathered", "type": "weapon", "subType": "dagger", "tier": "mythic", "powderSlots": 3,
    "identifications": {"exploding": {"min": -65, "raw": -50, "max": -35}, "airDamage": {"min": 6, "raw": 20, "max": 26},
                        "manaSteal": {"min": 5, "raw": 16, "max": 21}, "reflection": {"min": 8, "raw": 25, "max": 33},
                        "walkSpeed": {"min": 8, "raw": 25, "max": 33}, "rawAgility": 20},
}


class DecodeTest(unittest.TestCase):
    def test_a_code_from_the_game(self):
        item = wynntils.decode(f"look at this {WEATHERED_CODE} :)")
        self.assertEqual((item["kind"], item["name"], item["rerolls"], item["powder_slots"]), ("gear", "Weathered", 2, 3))
        self.assertEqual({stat["stat"]: stat["value"] for stat in item["identifications"]},
                         {"MISC_MANA_STEAL": 10, "MISC_REFLECTION": 20, "MISC_EXPLODING": -36,
                          "DAMAGE_ANY_AIR_PERCENT": 26, "MISC_WALK_SPEED": 29})

    def test_the_card_takes_bases_and_fixed_stats_from_the_item_data(self):
        item = wynntils.to_item(wynntils.decode(WEATHERED_CODE), WEATHERED_INFO)
        by_key = {stat.key: stat for stat in item.identifications}
        self.assertEqual(by_key["MISC_MANA_STEAL"].roll, rolls.percentage(10, 16))
        self.assertEqual((by_key["SKILL_AGILITY"].value, by_key["SKILL_AGILITY"].roll), (20, None))
        self.assertEqual((item.tier, item.type, item.rerolls), ("mythic", "dagger", 2))
        self.assertAlmostEqual(item.overall_roll, sum(s.roll for s in item.identifications if s.roll is not None) / 5)
        render_image(item, scale=1)

    def test_text_without_a_code(self):
        with self.assertRaisesRegex(ValueError, "no Wynntils item code"):
            wynntils.decode("just chat")

    def test_items_that_are_not_gear(self):
        tome = wynntils._to_text(bytes([wynntils.START, wynntils.VERSION, wynntils.TYPE, 1, wynntils.END]))
        with self.assertRaisesRegex(ValueError, "only gear and crafted gear"):
            wynntils.decode(tome)


class EncodeTest(unittest.TestCase):
    GEAR = {"kind": "gear", "name": "Weathered", "extended": False, "rerolls": 2, "powder_slots": 3,
            "powders": [["fire", 6], ["air", 1], ["earth", 6]], "shiny": {"name": "Mobs Killed", "value": 12345},
            "identifications": [{"stat": "MISC_MANA_STEAL", "value": 10, "base": None, "fixed": False},
                                {"stat": "MISC_EXPLODING", "value": -36, "base": None, "fixed": False}]}

    def test_gear_round_trip(self):
        self.assertEqual(wynntils.decode(wynntils.encode(self.GEAR)), self.GEAR)

    def test_extended_gear_carries_bases_and_fixed_stats(self):
        gear = self.GEAR | {"extended": True, "identifications": [
            {"stat": "SKILL_AGILITY", "value": 30, "base": 30, "fixed": True},
            {"stat": "MISC_MANA_STEAL", "value": 40, "base": 31, "fixed": False},
            {"stat": "SPELL_FIRST_SPELL_COST_RAW", "value": -4, "base": -3, "fixed": False}]}
        self.assertEqual(wynntils.decode(wynntils.encode(gear)), gear)

    def test_the_game_code_comes_back_without_its_roll_meters(self):
        """Wynntils adds the game's roll meter to each stat; the encoder writes none, the rest is the same."""
        decoded = wynntils.decode(WEATHERED_CODE)
        self.assertEqual(wynntils.decode(wynntils.encode(decoded)), decoded)

    def test_crafted_round_trip_with_its_name_after_the_code(self):
        crafted = {"kind": "crafted", "name": "Rodi Blade", "extended": False, "rerolls": 0, "shiny": None,
                   "powder_slots": 2, "powders": [["water", 4]], "type": "spear", "average_dps": 300,
                   "attack_speed": "fast", "damage": {"neutral": [10, 20], "fire": [30, 45]}, "health": 0,
                   "defence": {}, "requirements": {"level": 80, "class_name": "warrior", "strength": 40},
                   "identifications": [{"stat": "MISC_WALK_SPEED", "value": 15, "base": None, "fixed": False}]}
        code = wynntils.encode(crafted)
        self.assertTrue(code.endswith(' "Rodi Blade"'))
        crafted_back = wynntils.decode(code)
        self.assertEqual(crafted_back["name"], "Rodi Blade")
        for key in ("type", "average_dps", "attack_speed", "damage", "requirements", "identifications", "powders"):
            self.assertEqual(crafted_back[key], crafted[key], key)
        item = wynntils.to_item(crafted_back)
        self.assertEqual((item.name, item.kind, item.damage["fire"]), ("Rodi Blade", "weapon", (30, 45)))

    def test_a_name_wynntils_would_hide_stays_out(self):
        code = wynntils.encode({"kind": "crafted", "name": "<b>bad</b>", "type": "ring"})
        self.assertNotIn('"', code)
        self.assertEqual(wynntils.decode(code)["name"], "")

    def test_odd_byte_counts_use_the_area_b_padding(self):
        for data in (bytes([1, 2, 3]), bytes([255, 254, 255, 255, 7])):
            self.assertEqual(wynntils._to_bytes(wynntils._to_text(data)), data)

    def test_stats_without_a_wynntils_key(self):
        with self.assertRaisesRegex(ValueError, "no key for the stat Custom Stat"):
            wynntils.encode(self.GEAR | {"identifications": [{"stat": "Custom Stat", "value": 1}]})


if __name__ == "__main__":
    unittest.main()
