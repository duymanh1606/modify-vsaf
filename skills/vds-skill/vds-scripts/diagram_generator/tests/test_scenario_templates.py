from vds_diagram_generator.scenario_templates import list_templates_text, load_templates


def test_load_templates_contains_policy_template() -> None:
    templates = load_templates()
    assert "policy-renewal" in templates
    tpl = templates["policy-renewal"]
    assert tpl.match == "renewal"
    assert tpl.sequence_scope == "all"
    assert tpl.controllers and "PolicyController" in tpl.controllers


def test_list_templates_text_mentions_names() -> None:
    listing = list_templates_text()
    assert "policy-renewal" in listing
