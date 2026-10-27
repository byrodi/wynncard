import importlib.util
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from test_card import INFO

_spec = importlib.util.spec_from_file_location("build_site_data", Path(__file__).parent.parent / "tools" / "build_site_data.py")
build_site_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_site_data)


class SiteDataTest(unittest.TestCase):
    def build(self, database: list, weights: list | None = None) -> tuple[Path, int, str]:
        out = Path(self.enterContext(tempfile.TemporaryDirectory()))
        source, weights_source = out / "source.json", out / "weights.json"
        source.write_text(json.dumps(database))
        weights_source.write_text(json.dumps(weights or []))
        errors = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(errors):
            problems = build_site_data.items(out, str(source), build_site_data.weights(str(weights_source)))
        return out, problems, errors.getvalue()

    def test_presets_carry_the_base_item_and_its_rolls(self):
        spring = INFO | {"displayName": "Spring", "internalName": "Spring"}
        twin = INFO | {"displayName": "Spring", "internalName": "Masterwork Spring"}
        out, problems, _ = self.build([spring, twin, {"type": "ingredient", "displayName": "Dust"}])
        self.assertEqual(problems, 0)
        index = json.loads((out / "data" / "index.json").read_text())
        self.assertEqual(index, [["Spring", "mythic", "wand", 97, "spring"],
                                 ["Spring", "mythic", "wand", 97, "masterwork-spring", "Masterwork Spring"]])
        preset = json.loads((out / "data" / "items" / "spring.json").read_text())
        self.assertEqual(preset["item"]["name"], "Spring")
        self.assertEqual(preset["rolls"]["MISC_MANA_REGEN"][::30], [9, 39])
        self.assertEqual(preset["rolls"]["SPELL_SECOND_SPELL_COST_RAW"], [-1, -2, -3])
        self.assertNotIn("SKILL_INTELLIGENCE", preset["rolls"])  # a plain number never rolls

    def test_wynnpool_weights_come_with_the_preset_under_stat_keys(self):
        spring = INFO | {"displayName": "Spring", "internalName": "Spring"}
        profile = {"item_id": "Spring", "weight_name": "Main", "identifications": {"manaRegen": 0.6, "rawHealth": -0.4}}
        out, _, _ = self.build([spring], [profile])
        preset = json.loads((out / "data" / "items" / "spring.json").read_text())
        self.assertEqual(preset["weights"], [{"name": "Main", "stats": {"MISC_MANA_REGEN": 0.6, "MISC_HEALTH": -0.4}}])

    def test_missing_weights_only_warn(self):
        errors = StringIO()
        with redirect_stderr(errors):
            self.assertEqual(build_site_data.weights("/nonexistent/weights.json"), {})
        self.assertIn("no Wynnpool weights", errors.getvalue())

    def test_a_range_that_disagrees_with_the_api_is_a_problem(self):
        broken = INFO | {"displayName": "Broken", "identifications": {"manaRegen": {"min": 9, "raw": 30, "max": 40}}}
        out, problems, errors = self.build([broken])
        self.assertEqual(problems, 1)
        self.assertIn("manaRegen rolls 9..39, the API says 9..40", errors)
        self.assertEqual(json.loads((out / "data" / "index.json").read_text()), [])

    def test_package_holds_the_library_and_its_assets(self):
        out = Path(self.enterContext(tempfile.TemporaryDirectory()))
        build_site_data.package(out)
        names = zipfile.ZipFile(out / "py" / "wynncard.zip").namelist()
        self.assertIn("wynncard/render.py", names)
        self.assertIn("wynncard/assets/mc/font/language/wynncraft.json", names)
        self.assertFalse(any("__pycache__" in name for name in names))


if __name__ == "__main__":
    unittest.main()
