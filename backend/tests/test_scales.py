"""Escalas: puntaje según la planilla, correcciones de la revisión y permisos."""

import pytest
from fastapi.testclient import TestClient

from momento_api.scales import ACE3, ADDRESS, SCALES, score, serial7_points
from tests.access_helpers import Scenario, as_user, client, scenario  # noqa: F401


def _all(code: str, pick) -> dict:
    return {item["key"]: pick(item) for section in SCALES[code]["sections"] for item in section["items"]}


def best_choice(item):
    return max(item["options"], key=lambda o: o["points"])["value"]


def worst_choice(item):
    return min(item["options"], key=lambda o: o["points"])["value"]


def test_barthel_maximum_is_100_and_uses_sheet_bands() -> None:
    best = score("barthel", _all("barthel", best_choice))
    assert best["total"] == 100 and best["max"] == 100
    assert best["interpretation"] == "Independiente"
    worst = score("barthel", _all("barthel", worst_choice))
    assert worst["total"] == 0 and worst["interpretation"] == "Dependencia total"
    eating = SCALES["barthel"]["sections"][0]["items"][0]
    assert [o["points"] for o in eating["options"]] == [0, 5, 10]  # corrección: no 15


@pytest.mark.parametrize(("total", "label"), [(24, "Dependencia total"), (25, "Dependencia severa"),
                                               (74, "Dependencia moderada"), (90, "Dependencia media"),
                                               (95, "Dependencia mínima")])
def test_barthel_bands(total: int, label: str) -> None:
    from momento_api.scales import BARTHEL_BANDS
    assert next(text for low, high, text in BARTHEL_BANDS if low <= total <= high) == label


def test_incomplete_scales_are_rejected_but_preview_allows_partial() -> None:
    with pytest.raises(ValueError, match="Faltan respuestas"):
        score("barthel", {"comer": "2"})
    assert score("barthel", {"comer": "2"}, require_complete=False)["total"] == 10


def test_gds_reverse_items() -> None:
    answers = {f"p{n}": "1" for n in range(1, 16)}  # todo "No"
    # "No" suma en las 5 preguntas positivas (1, 5, 7, 11, 13).
    assert score("gds15", answers)["total"] == 5
    assert score("gds15", {f"p{n}": "0" for n in range(1, 16)})["total"] == 10
    assert score("gds15", answers)["max"] == 15


def test_cqc_domains_and_total() -> None:
    result = score("cqc", _all("cqc", best_choice))
    assert result["total"] == 96
    assert len(result["subscores"]) == 6
    assert all(item == {"score": 16, "max": 16} for item in result["subscores"].values())


def test_serial_sevens_score_relative_to_previous_answer() -> None:
    assert serial7_points([93, 86, 79, 72, 65]) == 5
    # Error en la primera; las siguientes restan bien desde la respuesta dada.
    assert serial7_points([92, 85, 78, 71, 64]) == 4
    assert serial7_points([93, None, 79, 72, 65]) == 4


def _ace_full() -> dict:
    answers = {}
    for section in ACE3["sections"]:
        for item in section["items"]:
            if item["type"] == "choice":
                answers[item["key"]] = best_choice(item)
            elif item["type"] == "checks":
                answers[item["key"]] = list(item["items"])
            elif item["type"] == "serial7":
                answers[item["key"]] = [93, 86, 79, 72, 65]
            elif item["type"] == "fluency":
                answers[item["key"]] = {"raw": 20, "score": 7}
            elif item["type"] == "recognition":
                answers[item["key"]] = {}
    return answers


def test_ace3_maximum_is_100_with_domain_maxima() -> None:
    result = score("ace3", _ace_full())
    assert result["total"] == 100
    assert {k: v["max"] for k, v in result["subscores"].items()} == {
        "Atención": 18, "Memoria": 26, "Fluencia": 14, "Lenguaje": 26, "Visoespacial": 16,
    }


def test_ace3_recognition_credits_what_was_recalled() -> None:
    answers = _ace_full()
    answers["address_recall"] = ["Luis", "Reynal", "420"]  # recordó nombre completo y número
    answers["recognition"] = {"calle": "Pablo Goyena", "ciudad": "Rosario", "provincia": "Chaco", "nombre": "Lucas Reynal"}
    result = score("ace3", answers)
    assert sorted(result["credited_by_recall"]) == ["nombre", "numero"]
    # 2 acreditados + ciudad correcta = 3; la respuesta equivocada de "nombre" no resta.
    memory = result["subscores"]["Memoria"]["score"]
    assert memory == 3 + 7 + 4 + 3 + 3


def test_ace3_partial_name_does_not_credit_recognition() -> None:
    answers = _ace_full()
    answers["address_recall"] = ["Luis"]
    answers["recognition"] = {}
    assert score("ace3", answers)["credited_by_recall"] == []


def test_ace3_writing_and_word_repetition_rules() -> None:
    answers = _ace_full()
    answers["writing"] = ["Hay dos oraciones", "Son sobre el mismo tema", "La gramática es correcta"]
    answers["repeat_words"] = ["Hipopótamo", "Excentricidad", "Ininteligible"]
    answers["irregular_reading"] = ["Jazz", "Jean"]
    language = score("ace3", answers)["subscores"]["Lenguaje"]["score"]
    assert language == 26 - 1 - 1 - 1


def test_ace3_rejects_invalid_values() -> None:
    answers = _ace_full()
    answers["fluency_p"] = {"raw": 30, "score": 9}
    with pytest.raises(ValueError):
        score("ace3", answers)
    with pytest.raises(ValueError):
        score("ace3", {**_ace_full(), "inventado": 1})
    with pytest.raises(ValueError):
        score("ace3", {**_ace_full(), "address_recall": ["Luis", "Buenos Aires"]})
    assert ADDRESS[0] == "Luis"


def _path(s: Scenario) -> str:
    return f"/api/care-units/{s.unit_id}/care-recipients/{s.recipient_id}"


def test_assessment_permissions_and_audit(client: TestClient, scenario: Scenario) -> None:
    payload = {"scale_code": "barthel", "performed_on": "2026-10-01", "answers": _all("barthel", best_choice)}

    as_user(client, "cuidador@test.example")
    assert client.post(f"{_path(scenario)}/assessments", json=payload).status_code == 403
    assert client.get("/api/scales").status_code == 200

    as_user(client, "medica@test.example")
    preview = client.post("/api/scales/barthel/score", json={"answers": {"comer": "1"}})
    assert preview.json()["total"] == 5
    created = client.post(f"{_path(scenario)}/assessments", json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["total_score"] == 100
    assert created.json()["interpretation"] == "Independiente"
    assert client.post(f"{_path(scenario)}/assessments", json={**payload, "performed_on": "2999-01-01"}).status_code == 422
    assert client.post(f"{_path(scenario)}/assessments", json={**payload, "answers": {"comer": "2"}}).status_code == 422
    assert client.delete(f"{_path(scenario)}/assessments/{created.json()['id']}").status_code == 403

    as_user(client, "cuidador@test.example")
    listed = client.get(f"{_path(scenario)}/assessments").json()
    assert [item["scale_code"] for item in listed] == ["barthel"]
    detail = client.get(f"{_path(scenario)}/assessments/{created.json()['id']}").json()
    assert detail["answers"]["comer"] == "2"

    as_user(client, "medicosur@test.example")
    assert client.get(f"{_path(scenario)}/assessments").status_code == 404

    as_user(client, "jefa@test.example")
    assert client.delete(f"{_path(scenario)}/assessments/{created.json()['id']}").status_code == 204
    actions = {(e["action"], e["outcome"]) for e in client.get(f"/api/organizations/{scenario.organization_id}/audit-events").json()}
    assert {("assessment.created", "success"), ("assessment.created", "denied"), ("assessment.viewed", "success"),
            ("assessment.deleted", "success")} <= actions


def test_background_validation_bmi_and_permissions(client: TestClient, scenario: Scenario) -> None:
    path = f"{_path(scenario)}/background"
    as_user(client, "cuidador@test.example")
    assert client.put(path, json={"answers": {"weight": 70}}).status_code == 403

    as_user(client, "medica@test.example")
    saved = client.put(path, json={"answers": {
        "weight": 70, "height": 1.75, "smoking": "si", "smoking__number": 5,
        "drugs": "no", "drugs__detail": "se descarta", "affected_domains": ["memoria", "atencion"],
    }})
    assert saved.status_code == 200, saved.text
    background = saved.json()["background"]
    assert background["bmi"] == 22.9
    assert "drugs__detail" not in background
    assert background["affected_domains"] == ["atencion", "memoria"]
    assert client.put(path, json={"answers": {"systolic": 500}}).status_code == 422
    assert client.put(path, json={"answers": {"vision": "telescopio"}}).status_code == 422
    assert client.put(path, json={"answers": {"inventado": 1}}).status_code == 422


def test_general_data_from_sheet(client: TestClient, scenario: Scenario) -> None:
    as_user(client, "jefa@test.example")
    updated = client.patch(_path(scenario), json={
        "sex": "mujer", "birth_country": "Argentina", "birth_province": "San Juan", "birth_locality": "Rivadavia",
        "education_level": "terciario", "education_title": "Maestra", "occupation": "docente",
        "marital_status": "viudo", "has_children": True, "children_details": "Lucía (58)",
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["education_level"] == "terciario"
    assert client.patch(_path(scenario), json={"sex": "x"}).status_code == 422
    assert client.patch(_path(scenario), json={"occupation": "astronauta"}).status_code == 422
