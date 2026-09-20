import unittest

from wynncard import Identification, Item, Requirements, Scale, from_market, from_wynnpool, render, render_image
from wynncard.tooltip import build, scale_color


def stat(api, key, value, unit, pct, display=None):
    stat_type = {"apiName": api, "displayName": display or api, "key": key, "unit": unit}
    return {"apiName": api, "displayName": display or api, "rollPercentage": pct,
            "statActualValue": {"value": value, "statType": stat_type}}


LISTING = {
    "name": "Spring", "rarity": "Mythic", "type": "WAND", "overall_roll": 91.2, "reroll_count": 3,
    "stat_rolls": [
        stat("4thSpellCost", "SPELL_FOURTH_SPELL_COST_PERCENT", 11, "PERCENT", 88.9, "4th Spell Cost"),
        stat("manaRegen", "MISC_MANA_REGEN", 22, "PER_5_S", 100.0, "Mana Regen"),
        stat("rawIntelligence", "SKILL_INTELLIGENCE", 26, "RAW", "NaN", "Intelligence"),
    ],
}
INFO = {
    "type": "weapon", "subType": "wand", "tier": "mythic", "emblem": "diamond_5", "attackSpeed": "normal",
    "averageDps": 510, "powderSlots": 4, "elements": ["water"], "restriction": "untradable",
    "requirements": {"level": 97, "classRequirement": "mage", "intelligence": 105},
    "base": {"baseWaterDamage": {"min": 220, "max": 280}},
    "identifications": {"manaRegen": {"min": 9, "raw": 30, "max": 39}, "rawIntelligence": 15,
                        "raw2ndSpellCost": {"min": -1, "raw": -2, "max": -3}},
    "majorIds": {"Cherry Bombs": "<span>Meteor splits into three.</span>"},
}


def flat(item, **options) -> str:
    return "".join(value for line in build(item, **options) for value, _, _ in line.runs + line.right)


class SourcesTest(unittest.TestCase):
    def test_wynnpool_base_item(self):
        item = from_wynnpool(INFO)
        self.assertEqual((item.tier, item.kind, item.type, item.restriction), ("mythic", "weapon", "wand", "untradable"))
        self.assertEqual(item.damage, {"water": (220, 280)})
        self.assertEqual(item.requirements.class_name, "mage")
        by_key = {stat.key: stat for stat in item.identifications}
        self.assertEqual((by_key["MISC_MANA_REGEN"].value, by_key["MISC_MANA_REGEN"].unit), (30, "/5s"))
        self.assertTrue(by_key["SPELL_SECOND_SPELL_COST_RAW"].positive)  # -2 cost is good

    def test_market_listing_overrides_rolls(self):
        item = from_market(LISTING, INFO, [{"profile": "Main", "score": 94.6}])
        self.assertEqual((item.overall_roll, item.rerolls, item.scales), (91.2, 3, [Scale("Main", 94.6)]))
        rolls = {stat.key: stat.roll for stat in item.identifications}
        self.assertEqual(rolls, {"SPELL_FOURTH_SPELL_COST_PERCENT": 88.9, "MISC_MANA_REGEN": 100.0,
                                 "SKILL_INTELLIGENCE": None})

    def test_market_listing_alone(self):
        item = from_market({"name": "Spring", "rarity": "Mythic", "type": "WAND"})
        self.assertEqual((item.tier, item.type, item.identifications), ("mythic", "wand", []))


class BuildTest(unittest.TestCase):
    def test_tooltip_order_and_spell_cost_sign(self):
        body = flat(from_market(LISTING, INFO))
        self.assertLess(body.index("Intelligence"), body.index("Mana Regen"))
        self.assertLess(body.index("Mana Regen"), body.index("Ice Snake Cost"))
        self.assertIn("-11%", body)  # the market API counts the reduction up, the tooltip shows a negative cost

    def test_class_and_scales(self):
        body = flat(from_market(LISTING, INFO, [{"profile": "Main", "score": 94.6}]))
        self.assertIn("Mage/Dark Wizard", body)
        self.assertIn("Main Scale", body)
        self.assertIn("[94.6%]", body)

    def test_rolls_off_hides_percentages(self):
        item = from_market(LISTING, INFO)
        self.assertIn("[91.2%]", flat(item))
        self.assertNotIn("%]", flat(item, rolls=False))

    def test_hand_made_item(self):
        item = Item("Test Ring", tier="rare", kind="accessory", type="ring", health=300,
                    requirements=Requirements(level=50, quest="A Very Long Quest Name"),
                    identifications=[Identification("Custom Stat", 5, "%", roll=50.0),
                                     Identification.from_api("walkSpeed", -10, roll=12.0)])
        body = flat(item)
        self.assertIn("+300 Health", body)
        self.assertIn("A Very Lon...", body)
        self.assertIn("-10%", body)
        self.assertLess(body.index("Walk Speed"), body.index("Custom Stat"))  # unknown keys go last

    def test_a_listing_without_base_data_draws_no_empty_dividers(self):
        """A market lot with no Wynnpool item has no damage and no requirements to separate."""
        def dividers(item):
            return sum(1 for line in build(item) if line.runs and line.runs[0][1] == "tooltip/divider")

        self.assertEqual(0, dividers(from_market(LISTING)))
        self.assertEqual(2, dividers(from_market(LISTING, INFO)))
        self.assertEqual(3, dividers(from_market(LISTING, INFO, [{"profile": "Main", "score": 94.6}])))

    def test_flat_colours_snap_to_the_stop_above(self):
        self.assertEqual(scale_color(100.0), "rainbow")
        self.assertEqual(scale_color(19.9), "#ff5555")
        self.assertEqual(scale_color(60.0), "#ffff55")
        self.assertEqual(scale_color(94.9), "#55ff55")
        self.assertEqual(scale_color(95.0), "#55ffff")

    def test_lerp_slides_between_the_mod_stops(self):
        self.assertEqual(scale_color(0.0, lerp=True), "#ff5555")
        self.assertEqual(scale_color(90.0, lerp=True), "#55ff55")
        self.assertNotEqual(scale_color(60.0, lerp=True), scale_color(60.0))

    def test_roll_percentages_truncate(self):
        self.assertIn("[94.6%]", flat(Item("x", scales=[Scale("Main", 94.69)])))


class RenderTest(unittest.TestCase):
    def test_png(self):
        self.assertTrue(render(from_market(LISTING, INFO)).startswith(b"\x89PNG"))

    def test_scale_and_frame(self):
        item = Item("Spring", tier="mythic")
        small, big = render_image(item, scale=1), render_image(item, scale=3)
        self.assertEqual((small.width * 3, small.height * 3), big.size)
        self.assertEqual(render_image(item, scale=1, frame=False).getpixel((0, 0)), (0, 0, 0, 0))
        with self.assertRaises(ValueError):
            render_image(item, scale=0)


if __name__ == "__main__":
    unittest.main()
