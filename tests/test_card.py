import unittest

from wynncard import render_card
from wynncard.game import build, scale_color


def stat(api, key, value, unit, pct, display=None):
    stat_type = {"apiName": api, "displayName": display or api, "key": key, "unit": unit}
    return {"apiName": api, "displayName": display or api, "rollPercentage": pct,
            "statActualValue": {"value": value, "statType": stat_type}}


ITEM = {
    "name": "Spring", "rarity": "Mythic", "type": "WAND", "overall_roll": 91.2, "reroll_count": 3,
    "stat_rolls": [
        stat("4thSpellCost", "SPELL_FOURTH_SPELL_COST_PERCENT", 11, "PERCENT", 88.9, "4th Spell Cost"),
        stat("manaRegen", "MISC_MANA_REGEN", 22, "PER_5_S", 100.0, "Mana Regen"),
        stat("rawIntelligence", "SKILL_INTELLIGENCE", 26, "RAW", "NaN", "Intelligence"),
    ],
}
INFO = {
    "type": "weapon", "subType": "wand", "tier": "mythic", "emblem": "diamond_5", "attackSpeed": "normal",
    "averageDps": 510, "powderSlots": 4, "elements": ["water"],
    "requirements": {"level": 97, "classRequirement": "mage", "intelligence": 105},
    "base": {"baseWaterDamage": {"min": 220, "max": 280}},
    "majorIds": {"Cherry Bombs": "<span>Meteor splits into three.</span>"},
}


class BuildTest(unittest.TestCase):
    def flat(self, item=ITEM, info=INFO, scales=()):
        runs = []
        for line in build(item, info, list(scales)):
            runs += line[1] if line[0] != "aligned" else line[1] + line[2]
        return "".join(value for value, _, _ in runs)

    def test_tooltip_order_and_spell_cost_sign(self):
        body = self.flat()
        self.assertLess(body.index("Intelligence"), body.index("Mana Regen"))
        self.assertLess(body.index("Mana Regen"), body.index("Ice Snake Cost"))
        self.assertIn("-11%", body)  # the API counts the reduction up, the tooltip shows a negative cost

    def test_class_and_scales(self):
        body = self.flat(scales=[{"profile": "Main", "score": 94.6}])
        self.assertIn("Mage/Dark Wizard", body)
        self.assertIn("Main Scale", body)
        self.assertIn("[94.6%]", body)

    def test_percentage_colours(self):
        self.assertEqual(scale_color(100.0), "rainbow")
        self.assertEqual(scale_color(20.0), "#ff5555")
        self.assertEqual(scale_color(95.0), "#55ff55")


class RenderTest(unittest.TestCase):
    def test_png(self):
        self.assertTrue(render_card(ITEM, INFO, [{"profile": "Main", "score": 94.6}]).startswith(b"\x89PNG"))

    def test_png_without_item_data(self):
        self.assertTrue(render_card({"name": "Spring", "rarity": "Mythic"}).startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
