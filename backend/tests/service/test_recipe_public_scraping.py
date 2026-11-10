from types import SimpleNamespace

from recipe_scrapers._exceptions import ElementNotFoundInHtml

from app.service import recipe_public_scraping


class _Scraper:
    def title(self):
        return "Plum cake"

    def total_time(self):
        return 60

    def cook_time(self):
        return 40

    def prep_time(self):
        return 20

    def yields(self):
        raise ElementNotFoundInHtml("yields")

    def description(self):
        return "A cake"

    def instructions(self):
        return "Bake it"

    def image(self):
        return "https://example.com/cake.jpg"

    def language(self):
        return "en"

    def ingredients(self):
        return []


def test_scrape_keeps_recipe_when_optional_field_is_missing(monkeypatch):
    monkeypatch.setattr(recipe_public_scraping, "scrape_html", lambda *a, **k: _Scraper())

    result = recipe_public_scraping.scrapeHTML(
        "https://example.com/cake", "<html></html>", SimpleNamespace(language="en", id=1)
    )

    assert result["recipe"]["name"] == "Plum cake"
    assert result["recipe"]["description"] == "A cake\n\nBake it"


def test_scrape_skips_staples_and_autocreates_items(monkeypatch):
    class CustomScraper(_Scraper):
        def ingredients(self):
            return ["100g Mehl", "1 Prise Salz", "200ml Wasser", "2 Eier"]

    created_items = []

    class FakeItem:
        def __init__(self, name):
            self.name = name
            self.id = 99

        def obj_to_dict(self):
            return {"id": self.id, "name": self.name}

    def fake_parse_ingredients_stream(*args, **kwargs):
        from app.service.ingredient_parsing import IngredientParsingResult

        r1 = IngredientParsingResult("100g Mehl", "Mehl", "100g", False)
        r2 = IngredientParsingResult("1 Prise Salz", "Salz", "1 Prise", True)
        r3 = IngredientParsingResult("200ml Wasser", "Wasser", "200ml", False)
        r4 = IngredientParsingResult("2 Eier", "Eier", "2", False)

        if False:
            yield
        return [r1, r2, r3, r4]

    monkeypatch.setattr(recipe_public_scraping, "scrape_html", lambda *a, **k: CustomScraper())
    monkeypatch.setattr(recipe_public_scraping, "parseIngredientsStream", fake_parse_ingredients_stream)
    monkeypatch.setattr(recipe_public_scraping.Item, "find_name_starts_with", lambda hid, name: None)
    monkeypatch.setattr(
        recipe_public_scraping.Item,
        "create_by_name",
        lambda hid, name: (created_items.append(name), FakeItem(name))[1],
    )

    result = recipe_public_scraping.scrapeHTML(
        "https://example.com/cake", "<html></html>", SimpleNamespace(language="de", id=1)
    )

    assert "1 Prise Salz" not in result["items"]
    assert "200ml Wasser" not in result["items"]
    assert "100g Mehl" in result["items"]
    assert "2 Eier" in result["items"]
    assert created_items == ["Mehl", "Eier"]

