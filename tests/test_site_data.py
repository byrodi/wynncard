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
    def build(self, database: list) -> tuple[Path, int, str]:
        out = Path(self.enterContext(tempfile.TemporaryDirectory()))
        source = out / "source.json"
        source.write_text(json.dumps(database))
        errors = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(errors):
            problems = build_site_data.items(out, str(source))
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
