"""Tests for template repository including processing history."""

from paper_format_corrector.infra.template_repository import TemplateRepository


def test_repository_seeds_and_saves_personal_template(tmp_path):
    repository = TemplateRepository(tmp_path / "templates.db")
    assert repository.list_templates()

    saved = repository.save_personal_template("朋友论文", "高校毕业论文", {"format_rules": {"body_text": {"font_size": 12}}})
    loaded = repository.get(saved.slug)
    assert loaded is not None
    assert loaded.source == "personal"
    assert loaded.config["format_rules"]["body_text"]["font_size"] == 12


def test_template_search(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    repo.save_personal_template("IEEE Test", "国际期刊与会议", {"format_rules": {}})
    results = repo.search_templates("IEEE")
    assert len(results) >= 1
    assert any("IEEE" in r.name for r in results)


def test_template_copy(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    builtin = repo.list_templates(source="bundled")
    if builtin:
        copied = repo.copy_template(builtin[0].slug, "我的副本")
        assert copied.source == "personal"
        assert copied.name == "我的副本"


def test_template_versions(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    saved = repo.save_personal_template("版本测试", "个人模板", {"format_rules": {"body_text": {"font_size": 12}}})
    repo.update_template(saved.slug, {"config": {"format_rules": {"body_text": {"font_size": 14}}}})
    versions = repo.get_versions(saved.slug)
    assert len(versions) >= 2


def test_template_delete_bundled_only_disables(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    builtin = repo.list_templates(source="bundled")
    if builtin:
        slug = builtin[0].slug
        repo.delete_template(slug)
        disabled = repo.get(slug)
        assert disabled is not None
        assert disabled.is_active is False


def test_template_import_export_yaml(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    saved = repo.save_personal_template("导出测试", "个人模板", {"format_rules": {"body_text": {"font_size": 12}}})
    export_path = tmp_path / "export.yaml"
    repo.export_to_yaml(saved.slug, export_path)
    assert export_path.exists()

    imported = repo.import_from_yaml(export_path)
    assert imported.name == "导出测试"


def test_template_import_export_json(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    saved = repo.save_personal_template("JSON导出测试", "个人模板", {"format_rules": {}})
    export_path = tmp_path / "export.json"
    repo.export_to_json(saved.slug, export_path)
    assert export_path.exists()

    imported = repo.import_from_json(export_path)
    assert imported.name == "JSON导出测试"


def test_processing_history_save_and_list(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    record_id = repo.save_processing_history(
        input_file="test.docx",
        output_file="output.docx",
        template_used="ieee",
        quality_score=85.0,
        total_elements=100,
        modified_elements=80,
        processing_time=2.5,
        report={"applied": {"body": 50}},
    )
    assert record_id > 0

    history = repo.list_processing_history()
    assert len(history) >= 1
    assert history[0]["input_file"] == "test.docx"
    assert history[0]["quality_score"] == 85.0


def test_processing_history_get_detail(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    record_id = repo.save_processing_history(
        input_file="detail.docx",
        output_file="detail_out.docx",
        report={"test": True},
    )
    detail = repo.get_processing_history(record_id)
    assert detail is not None
    assert detail["input_file"] == "detail.docx"
    assert detail["report"]["test"] is True


def test_template_enable(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    # Use a bundled template (disable then enable)
    builtin = repo.list_templates(source="bundled")
    if builtin:
        slug = builtin[0].slug
        repo.delete_template(slug)  # Bundled: just disables
        disabled = repo.get(slug)
        assert disabled is not None
        assert disabled.is_active is False
        repo.enable_template(slug)
        enabled = repo.get(slug)
        assert enabled is not None
        assert enabled.is_active is True
