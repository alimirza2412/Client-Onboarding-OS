def test_new_form_version_does_not_affect_existing_submission_reference(registered_org):
    """
    Phase 4 critical test: client starts on Form Version 1; admin
    publishes Version 2; the existing onboarding must remain pinned to
    Version 1 (FormSubmission.form_version_id never changes), while new
    lookups of "the latest published version" correctly return Version 2.
    """
    client, _ = registered_org

    r = client.post(
        "/forms",
        json={
            "name": "Versioned Intake",
            "definition": {"fields": [{"key": "q1", "label": "Q1", "type": "text", "required": True}]},
        },
    )
    assert r.status_code == 201
    form = r.json()
    form_id = form["id"]
    v1_id = form["versions"][0]["id"]
    assert form["versions"][0]["version_number"] == 1

    # "Latest published" is v1 for now
    r = client.get(f"/forms/{form_id}/versions/latest")
    assert r.status_code == 200
    assert r.json()["id"] == v1_id

    # Publish v2 with an extra field
    r = client.post(
        f"/forms/{form_id}/versions",
        json={
            "definition": {
                "fields": [
                    {"key": "q1", "label": "Q1", "type": "text", "required": True},
                    {"key": "q2", "label": "Q2 (new)", "type": "text", "required": False},
                ]
            }
        },
    )
    assert r.status_code == 201
    v2 = r.json()
    assert v2["version_number"] == 2
    v2_id = v2["id"]
    assert v2_id != v1_id

    # "Latest published" now correctly returns v2
    r = client.get(f"/forms/{form_id}/versions/latest")
    assert r.status_code == 200
    assert r.json()["id"] == v2_id

    # v1 itself is unchanged and still fetchable/immutable
    r = client.get("/forms")
    versions = next(f for f in r.json() if f["id"] == form_id)["versions"]
    v1_after = next(v for v in versions if v["id"] == v1_id)
    assert v1_after["version_number"] == 1
    assert v1_after["definition"]["fields"][0]["key"] == "q1"
    assert len(v1_after["definition"]["fields"]) == 1
