from __future__ import annotations

import asyncio
import io
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook
from pypdf import PdfWriter
import pytest
from starlette.datastructures import UploadFile

from caos.config import Settings
from caos.http import create_app
from caos.sources.domain import Vault, ingest_upload
from caos.store import MemoryStore


def test_zero_byte_source_is_rejected_before_source_set_creation(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")
    with TestClient(create_app(settings, MemoryStore())) as client:
        case_id = client.post("/api/cases", json={"name": "Empty source", "issuer": "Issuer", "sector": "Test"}).json()["id"]

        upload = client.post(f"/api/cases/{case_id}/sources", files={"file": ("empty.txt", b"", "text/plain")})

        assert upload.status_code == 422
        assert upload.json()["detail"] == "source is empty"
        assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "NEEDS_SOURCE"


def test_source_ingestion_rolls_back_metadata_when_persistence_fails(tmp_path: Path) -> None:
    class FailingStore(MemoryStore):
        def __init__(self) -> None:
            super().__init__()
            self.fail_persist = False

        def persist(self) -> None:
            if self.fail_persist:
                raise RuntimeError("database unavailable")

    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")

    def upload(store: MemoryStore, case_id: str, name: str = "source.txt") -> dict[str, object]:
        return asyncio.run(ingest_upload(store, Vault(settings), case_id, "analyst", UploadFile(file=io.BytesIO(b"Revenue 100"), filename=name), settings.max_upload_bytes))

    empty_store = FailingStore()
    empty_case_id = empty_store.create_case("Empty source", "Issuer", "Sector", "analyst")["id"]
    empty_store.fail_persist = True
    with pytest.raises(RuntimeError, match="database unavailable"):
        upload(empty_store, empty_case_id)
    assert not empty_store.sources and empty_case_id not in empty_store.source_sets and not empty_store.source_set_history

    store = FailingStore()
    case_id = store.create_case("Source", "Issuer", "Sector", "analyst")["id"]
    store.sources["src_original"] = {"id": "src_original", "case_id": case_id, "sha256": "original", "withdrawn": False}
    store.register_source_set({"id": "set_original", "case_id": case_id, "version": 1, "source_ids": ["src_original"], "created_by": "analyst", "created_at": "2026-08-22T00:00:00+00:00"})
    original_set = store.source_sets[case_id].copy()
    store.fail_persist = True
    with pytest.raises(RuntimeError, match="database unavailable"):
        upload(store, case_id, "failed.txt")
    assert set(store.sources) == {"src_original"} and store.source_sets[case_id] == original_set and set(store.source_set_history) == {"set_original"}
    store.fail_persist = False
    assert upload(store, case_id, "recovered.txt")["source_set"]["version"] == 2


def test_source_ingestion_persists_audit_with_metadata(tmp_path: Path) -> None:
    class SnapshotStore(MemoryStore):
        def __init__(self) -> None:
            super().__init__()
            self.fail_persist = False
            self.persisted_states: list[dict[str, object]] = []

        def persist(self) -> None:
            if self.fail_persist:
                raise RuntimeError("database unavailable")
            self.persisted_states.append({"sources": self.sources.copy(), "source_sets": self.source_sets.copy(), "audit": self.audit.copy()})

    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")
    store = SnapshotStore()
    case_id = store.create_case("Source audit", "Issuer", "Sector", "analyst")["id"]

    source = asyncio.run(ingest_upload(store, Vault(settings), case_id, "analyst", UploadFile(file=io.BytesIO(b"Revenue 100"), filename="source.txt"), settings.max_upload_bytes))

    assert source["id"] in store.persisted_states[-1]["sources"]
    assert store.persisted_states[-1]["audit"][-1]["action"] == "source.ingested"
    prior_audit = store.audit.copy()
    store.fail_persist = True
    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(ingest_upload(store, Vault(settings), case_id, "analyst", UploadFile(file=io.BytesIO(b"EBITDA 50"), filename="failed.txt"), settings.max_upload_bytes))
    assert store.audit == prior_audit


def test_evidence_free_text_csv_and_xlsx_are_rejected_before_source_set_creation(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")
    workbook = Workbook()
    blank_xlsx = io.BytesIO()
    workbook.save(blank_xlsx)
    uploads = [
        ("spaces.txt", b" \n\t\n", "text/plain"),
        ("spaces.csv", b",,\n,,\n", "text/csv"),
        ("quoted-empty.csv", b',"",\n', "text/csv"),
        ("blank.xlsx", blank_xlsx.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ]

    with TestClient(create_app(settings, MemoryStore())) as client:
        for filename, content, media_type in uploads:
            case_id = client.post("/api/cases", json={"name": filename, "issuer": "Issuer", "sector": "Test"}).json()["id"]
            upload = client.post(f"/api/cases/{case_id}/sources", files={"file": (filename, content, media_type)})

            assert upload.status_code == 422
            assert upload.json()["detail"] == "source contains no extractable evidence"
            assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "NEEDS_SOURCE"


def test_evidence_free_json_values_are_rejected_before_source_set_creation(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")
    uploads = [("object.json", b"{}"), ("list.json", b"[]"), ("empty.json", b'""'), ("spaces.json", b'" \\t"'), ("null.json", b"null")]

    with TestClient(create_app(settings, MemoryStore())) as client:
        for filename, content in uploads:
            case_id = client.post("/api/cases", json={"name": filename, "issuer": "Issuer", "sector": "Test"}).json()["id"]
            upload = client.post(f"/api/cases/{case_id}/sources", files={"file": (filename, content, "application/json")})

            assert upload.status_code == 422
            assert upload.json()["detail"] == "source contains no extractable evidence"
            assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "NEEDS_SOURCE"


def test_non_finite_json_values_are_rejected_before_source_set_creation(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")
    uploads = [
        ("nan.json", b'{"amount":NaN}'),
        ("positive.json", b'{"amount":Infinity}'),
        ("negative.json", b'{"amount":-Infinity}'),
        # Not the NaN/Infinity literals: finite-looking tokens that overflow the double
        # range. `parse_constant` never sees these, so they used to land as `inf`.
        ("overflow.json", b'{"amount":1e999}'),
        ("negative-overflow.json", b'{"amount":-1e999}'),
        ("uppercase-overflow.json", b'{"amount":1E400}'),
    ]

    with TestClient(create_app(settings, MemoryStore())) as client:
        for filename, content in uploads:
            case_id = client.post("/api/cases", json={"name": filename, "issuer": "Issuer", "sector": "Test"}).json()["id"]
            upload = client.post(f"/api/cases/{case_id}/sources", files={"file": (filename, content, "application/json")})

            assert upload.status_code == 422
            assert upload.json()["detail"] == "invalid JSON source"
            assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "NEEDS_SOURCE"


def test_duplicate_json_keys_are_rejected_before_source_set_creation(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")
    uploads = [("duplicate.json", b'{"debt":10,"debt":20}'), ("nested.json", b'{"facility":{"debt":10,"debt":20}}')]

    with TestClient(create_app(settings, MemoryStore())) as client:
        for filename, content in uploads:
            case_id = client.post("/api/cases", json={"name": filename, "issuer": "Issuer", "sector": "Test"}).json()["id"]
            upload = client.post(f"/api/cases/{case_id}/sources", files={"file": (filename, content, "application/json")})

            assert upload.status_code == 422
            assert upload.json()["detail"] == "invalid JSON source"
            assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "NEEDS_SOURCE"


def test_non_utf8_text_sources_are_rejected_before_source_set_creation(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")

    with TestClient(create_app(settings, MemoryStore())) as client:
        for filename in ["binary.txt", "binary.md", "binary.csv"]:
            case_id = client.post("/api/cases", json={"name": filename, "issuer": "Issuer", "sector": "Test"}).json()["id"]
            upload = client.post(f"/api/cases/{case_id}/sources", files={"file": (filename, bytes([128]), "text/plain")})

            assert upload.status_code == 422
            assert upload.json()["detail"] == "text source must be UTF-8"
            assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "NEEDS_SOURCE"


def test_invalid_pdf_is_rejected_before_source_set_creation(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")

    with TestClient(create_app(settings, MemoryStore())) as client:
        case_id = client.post("/api/cases", json={"name": "Invalid PDF", "issuer": "Issuer", "sector": "Test"}).json()["id"]
        upload = client.post(f"/api/cases/{case_id}/sources", files={"file": ("not-a-pdf.pdf", b"not a PDF", "application/pdf")})

        assert upload.status_code == 422
        assert upload.json()["detail"] == "invalid PDF source"
        assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "NEEDS_SOURCE"


def test_valid_no_text_pdf_is_accepted(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    source = io.BytesIO()
    writer.write(source)

    with TestClient(create_app(settings, MemoryStore())) as client:
        case_id = client.post("/api/cases", json={"name": "Scanned PDF", "issuer": "Issuer", "sector": "Test"}).json()["id"]
        upload = client.post(f"/api/cases/{case_id}/sources", files={"file": ("scan.pdf", source.getvalue(), "application/pdf")})

        assert upload.status_code == 201
        assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "READY"


def test_non_empty_xlsx_is_accepted(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")
    workbook = Workbook()
    workbook.active["A1"] = "Debt"
    source = io.BytesIO()
    workbook.save(source)

    with TestClient(create_app(settings, MemoryStore())) as client:
        case_id = client.post("/api/cases", json={"name": "Workbook source", "issuer": "Issuer", "sector": "Test"}).json()["id"]
        upload = client.post(f"/api/cases/{case_id}/sources", files={"file": ("debt.xlsx", source.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})

        assert upload.status_code == 201
        assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "READY"


def test_json_scalar_values_are_accepted(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")

    with TestClient(create_app(settings, MemoryStore())) as client:
        for filename, content in [("zero.json", b"0"), ("false.json", b"false"), ("finite.json", b'{"amount":1.25}'), ("large-finite.json", b'{"amount":1e308}')]:
            case_id = client.post("/api/cases", json={"name": filename, "issuer": "Issuer", "sector": "Test"}).json()["id"]
            upload = client.post(f"/api/cases/{case_id}/sources", files={"file": (filename, content, "application/json")})

            assert upload.status_code == 201
            assert client.get(f"/api/cases/{case_id}/pathway-fit").json()["fit"] == "READY"


def test_duplicate_active_source_content_is_rejected_without_creating_a_new_source_set(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "vault", deploy_v_root=Path(__file__).parents[1] / "server" / "caos" / "methodology" / "vendor" / "deploy_v")

    with TestClient(create_app(settings, MemoryStore())) as client:
        case_id = client.post("/api/cases", json={"name": "Duplicate source", "issuer": "Issuer", "sector": "Test"}).json()["id"]
        first = client.post(f"/api/cases/{case_id}/sources", files={"file": ("evidence.txt", b"Debt 100", "text/plain")})
        duplicate = client.post(f"/api/cases/{case_id}/sources", files={"file": ("replacement-name.txt", b"Debt 100", "text/plain")})

        assert first.status_code == 201
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"] == "source content already active"
        detail = client.get(f"/api/cases/{case_id}").json()
        assert detail["source_count"] == 1
        assert detail["source_set"]["version"] == 1

        assert client.post(f"/api/cases/{case_id}/sources/{first.json()['id']}/withdraw").status_code == 200
        reupload = client.post(f"/api/cases/{case_id}/sources", files={"file": ("evidence.txt", b"Debt 100", "text/plain")})

        assert reupload.status_code == 201
        detail = client.get(f"/api/cases/{case_id}").json()
        assert detail["source_count"] == 1
        assert detail["source_set"]["version"] == 3


def test_clamav_config_keeps_container_health_and_app_tcp_interfaces() -> None:
    config = (Path(__file__).parents[1] / "deploy" / "clamd.conf").read_text().splitlines()

    assert "LocalSocket /tmp/clamd.sock" in config
    assert "TCPSocket 3310" in config
