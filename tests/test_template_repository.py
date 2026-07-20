from paper_format_corrector.infra.template_repository import TemplateRepository


def test_repository_seeds_and_saves_personal_template(tmp_path):
    repository = TemplateRepository(tmp_path / "templates.db")
    assert repository.list_templates()

    saved = repository.save_personal_template("朋友论文", "高校毕业论文", {"format_rules": {"body_text": {"font_size": 12}}})
    loaded = repository.get(saved.slug)
    assert loaded is not None
    assert loaded.source == "personal"
    assert loaded.config["format_rules"]["body_text"]["font_size"] == 12
