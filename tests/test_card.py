import unittest

from wynncard import render_card
from wynncard.rows import build, stats


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
    "type": "weapon", "subType": "wand", "attackSpeed": "normal", "averageDps": 510, "powderSlots": 4,
    "elements": ["water"], "requirements": {"level": 97, "classRequirement": "mage", "intelligence": 105},
    "base": {"baseWaterDamage": {"min": 220, "max": 280}},
    "majorIds": {"Cherry Bombs": "<span>Meteor splits into three.</span>"},
}


class RowsTest(unittest.TestCase):
    def test_tooltip_order_and_spell_cost_sign(self):
        rows = stats(ITEM, ("Heal", "Teleport", "Meteor", "Ice Snake"))
        names = [r[1][-1][0] for r in rows if r[0] == "stat"]
        self.assertEqual(names, ["Intelligence", "Mana Regen", "Ice Snake Cost"])
        cost = next(r for r in rows if r[0] == "stat" and r[1][-1][0] == "Ice Snake Cost")
        self.assertEqual(cost[2][0][0], "-11%")  # the API counts the reduction up, the tooltip shows a negative cost

    def test_badge_holds_powder_and_rerolls(self):
        self.assertIn(("badge", 4, 3), build(ITEM, INFO, []))

    def test_single_reroll_is_not_shown(self):
        rows = build(dict(ITEM, reroll_count=1), {}, [])
        self.assertFalse([r for r in rows if r[0] == "badge"])


class RenderTest(unittest.TestCase):
    def test_png(self):
        png = render_card(ITEM, INFO, [{"profile": "Main", "score": 94.6}])
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_png_without_item_data(self):
        self.assertTrue(render_card({"name": "Spring", "rarity": "Mythic"}).startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
