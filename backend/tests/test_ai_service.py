from app.services.ai import extract_document_data


def test_mock_extraction_is_deterministic_for_same_text():
    text = "Invoice #123 from Acme Roasters, total due $2,500."
    data1, confidence1 = extract_document_data(text)
    data2, confidence2 = extract_document_data(text)

    assert data1 == data2
    assert confidence1 == confidence2


def test_mock_extraction_confidence_in_valid_range():
    _, confidence = extract_document_data("Some arbitrary document text for testing purposes.")
    assert 0.0 <= confidence <= 1.0


def test_mock_extraction_varies_by_content():
    data_a, _ = extract_document_data("Completely different content about widgets and gadgets.")
    data_b, _ = extract_document_data("Totally unrelated text discussing zebras and elephants.")
    assert data_a != data_b
