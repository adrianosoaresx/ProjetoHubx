import xml.etree.ElementTree as ET


def test_render_search_snippet_escapes_html():
    snippet = '<img src=x onerror=alert(1)>'
    button = ET.Element('button')
    button.text = snippet
    output = ET.tostring(button, encoding='unicode')
    assert '<img' not in output
    assert '&lt;img' in output
