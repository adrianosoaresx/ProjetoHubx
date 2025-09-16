from django.template import Context, Template


def render_template(snippet: str) -> str:
    template = Template("{% load lucide_icons %}" + snippet)
    return template.render(Context()).strip()


def test_lucide_whatsapp_icon_renders_official_svg():
    svg = render_template("{% lucide 'whatsapp' %}")

    assert svg.startswith("<svg")
    assert 'aria-hidden="true"' in svg
    assert 'width="24"' in svg
    assert 'height="24"' in svg
    assert 'fill="currentColor"' in svg
    assert 'viewBox="0 0 24 24"' in svg
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert (
        '<path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967' in svg
    )


def test_lucide_whatsapp_accepts_accessibility_and_attrs():
    svg = render_template("{% lucide 'whatsapp' label='WhatsApp' class='icon' %}")

    assert 'aria-label="WhatsApp"' in svg
    assert 'aria-hidden' not in svg
    assert 'class="icon"' in svg
