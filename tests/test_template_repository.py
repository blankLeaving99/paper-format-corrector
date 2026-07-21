"""Tests for template repository including processing history."""

from paper_format_corrector.adapters.storage.template_repository import TemplateRepository


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


def test_list_categories(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    categories = repo.list_categories()
    assert isinstance(categories, list)
    assert len(categories) >= 1
    for cat in categories:
        assert "category" in cat
        assert "count" in cat
        assert cat["count"] > 0


def test_list_organizations(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    orgs = repo.list_organizations()
    assert isinstance(orgs, list)
    for org in orgs:
        assert "organization" in org
        assert "count" in org


def test_list_tags(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    tags = repo.list_tags()
    assert isinstance(tags, list)
    for tag in tags:
        assert "tag" in tag
        assert "count" in tag


def test_get_template_summary(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    builtin = repo.list_templates(source="bundled")
    if builtin:
        summary = repo.get_template_summary(builtin[0].slug)
        assert summary is not None
        assert "slug" in summary
        assert "name" in summary
        assert "style_summary" in summary
        assert "body_font" in summary["style_summary"]
        assert "heading_count" in summary["style_summary"]


def test_search_templates_by_organization(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    # Search by org name
    results = repo.search_templates("大学")
    # May or may not find results depending on seed data, but should not error
    assert isinstance(results, list)


def test_search_templates_by_tag(tmp_path):
    repo = TemplateRepository(tmp_path / "templates.db")
    results = repo.search_templates("APA")
    assert isinstance(results, list)


def test_template_validation_valid():
    from paper_format_corrector.services.template_validation import TemplateValidationService
    validator = TemplateValidationService()
    config = {
        "format_rules": {
            "font": {"chinese": "宋体", "english": "Times New Roman"},
            "body_text": {"font_size": 12, "line_spacing": 1.5},
            "headings": {
                "heading1": {"font_size": 16, "bold": True, "align": "center"},
                "heading2": {"font_size": 14, "bold": True, "align": "left"},
                "heading3": {"font_size": 12, "bold": True, "align": "left"},
            },
            "tables": {"style": "three_line", "font_size": 10},
            "images": {"max_width": "90%"},
            "margins": {"top": 2.54, "bottom": 2.54, "left": 3.17, "right": 3.17},
        }
    }
    report = validator.validate("test", config)
    assert report.is_valid
    assert report.score > 80


def test_template_validation_missing_required():
    from paper_format_corrector.services.template_validation import TemplateValidationService
    validator = TemplateValidationService()
    config = {"format_rules": {}}
    report = validator.validate("empty", config)
    assert not report.is_valid
    assert report.score < 80
    errors = [i for i in report.issues if i.severity == "error"]
    assert len(errors) >= 3  # Missing font, body_text, headings


def test_template_validation_warnings():
    from paper_format_corrector.services.template_validation import TemplateValidationService
    validator = TemplateValidationService()
    config = {
        "format_rules": {
            "font": {"chinese": "宋体", "english": "Times New Roman"},
            "body_text": {"font_size": 50, "line_spacing": 0.5},  # Out of range
            "headings": {
                "heading1": {"font_size": 14},  # smaller than h2
                "heading2": {"font_size": 16},  # larger than h1
                "heading3": {},
            },
        }
    }
    report = validator.validate("warnings", config)
    warnings = [i for i in report.issues if i.severity == "warning"]
    assert len(warnings) >= 2  # Font size out of range + heading hierarchy


def test_template_validation_to_dict():
    from paper_format_corrector.services.template_validation import TemplateValidationService
    validator = TemplateValidationService()
    config = {"format_rules": {"font": {"chinese": "宋体"}}}
    report = validator.validate("test", config)
    d = report.to_dict()
    assert "slug" in d
    assert "is_valid" in d
    assert "score" in d
    assert "issues" in d
