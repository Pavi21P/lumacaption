from threading import Event

import pytest
from PIL import Image

from lumacaption import images
from lumacaption.batch import CaptionResult, run_batch
from lumacaption.engine import CaptionOptions, ModelUnavailableError
from lumacaption.exporting import export_results, spreadsheet_safe


@pytest.fixture
def photo(tmp_path):
    path = tmp_path / "a photo ü.png"
    Image.new("RGB", (48, 24), "red").save(path)
    return path


def test_load_detaches_pixels_and_preserves_original(photo):
    before = photo.read_bytes()
    with images.load_image(photo) as image:
        assert image.mode == "RGB"
        assert image.getpixel((0, 0)) == (255, 0, 0)
    assert photo.read_bytes() == before


def test_transparency_composited_to_white(tmp_path):
    path = tmp_path / "transparent.png"
    Image.new("RGBA", (10, 10), (255, 0, 0, 0)).save(path)
    with images.load_image(path) as image:
        assert image.getpixel((0, 0)) == (255, 255, 255)


def test_exif_orientation(tmp_path):
    path = tmp_path / "rotated.jpg"
    source = Image.new("RGB", (40, 20), "blue")
    exif = Image.Exif()
    exif[274] = 6
    source.save(path, exif=exif)
    with images.load_image(path) as image:
        assert image.size == (20, 40)


def test_grayscale_is_rgb(tmp_path):
    path = tmp_path / "gray.png"
    Image.new("L", (8, 8), 120).save(path)
    with images.load_image(path) as image:
        assert image.mode == "RGB"


def test_corrupt_image_is_readable_error(tmp_path):
    path = tmp_path / "broken.jpg"
    path.write_bytes(b"not a photo")
    with pytest.raises(images.ImageInputError, match="damaged"):
        images.load_image(path)


def test_file_size_limit(photo, monkeypatch):
    monkeypatch.setattr(images, "MAX_FILE_BYTES", 1)
    with pytest.raises(images.ImageInputError, match="40 MB"):
        images.load_image(photo)


def test_pixel_limit(photo, monkeypatch):
    monkeypatch.setattr(images, "MAX_PIXELS", 1)
    with pytest.raises(images.ImageInputError, match="megapixel"):
        images.load_image(photo)


def test_collect_deduplicates_and_ignores_non_images(photo):
    (photo.parent / "notes.txt").write_text("ignored")
    assert images.collect_images([photo, photo.parent]) == [photo.resolve()]


def test_recursive_opt_in(photo):
    sub = photo.parent / "sub"
    sub.mkdir()
    second = sub / "second.PNG"
    Image.new("RGB", (8, 8)).save(second)
    assert len(images.collect_images([photo.parent])) == 1
    assert len(images.collect_images([photo.parent], recursive=True)) == 2


def test_batch_limit(photo, monkeypatch):
    monkeypatch.setattr(images, "MAX_BATCH", 0)
    with pytest.raises(images.ImageInputError, match="at most"):
        images.collect_images([photo])


def test_empty_folder(tmp_path):
    with pytest.raises(images.ImageInputError, match="No supported"):
        images.collect_images([tmp_path])


class FakeEngine:
    def __init__(self):
        self.prepares = 0
        self.calls = 0

    def prepare(self, status=lambda _: None):
        self.prepares += 1

    def caption(self, image, options):
        self.calls += 1
        return "A red square"


def test_batch_continues_after_corrupt_file(photo, tmp_path):
    corrupt = tmp_path / "bad.jpg"
    corrupt.write_bytes(b"bad")
    engine = FakeEngine()
    results = list(run_batch([corrupt, photo], engine, CaptionOptions()))
    assert [item.status for item in results] == ["error", "done"]
    assert engine.prepares == 1
    assert results[1].generated_caption == "A red square"


def test_cancel_before_model_load(photo):
    cancelled = Event()
    cancelled.set()
    engine = FakeEngine()
    assert list(run_batch([photo], engine, CaptionOptions(), cancel=cancelled)) == []
    assert engine.prepares == 0


def test_cancel_between_images(photo):
    cancelled = Event()
    engine = FakeEngine()
    iterator = run_batch([photo, photo], engine, CaptionOptions(), cancel=cancelled)
    assert next(iterator).status == "done"
    cancelled.set()
    assert list(iterator) == []
    assert engine.calls == 1


def test_model_failure_stops_batch(photo):
    class FailingEngine(FakeEngine):
        def prepare(self, status=lambda _: None):
            raise ModelUnavailableError("missing")

    with pytest.raises(ModelUnavailableError):
        list(run_batch([photo, photo], FailingEngine(), CaptionOptions()))


def test_invalid_images_do_not_download_model(tmp_path):
    path = tmp_path / "bad.jpg"
    path.write_bytes(b"bad")
    engine = FakeEngine()
    assert list(run_batch([path], engine, CaptionOptions()))[0].status == "error"
    assert engine.prepares == 0


@pytest.mark.parametrize("value", ["=1+1", "+SUM(A1)", "-1+2", "@SUM(A1)", "  =1", "\ttext"])
def test_csv_formula_escape(value):
    assert spreadsheet_safe(value).startswith("'")


def test_export_json_preserves_edits_and_original(photo, tmp_path):
    import json

    result = CaptionResult(
        str(photo),
        caption="Edited café",
        status="done",
        generated_caption="A red square",
        edited=True,
    )
    path = tmp_path / "out.json"
    export_results([result], path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["schema_version"] == 1
    assert doc["results"][0]["caption"] == "Edited café"
    assert doc["results"][0]["generated_caption"] == "A red square"


def test_csv_excel_bom_and_escape(photo, tmp_path):
    import csv

    result = CaptionResult(str(photo), caption="=1+1", status="done")
    path = tmp_path / "out.csv"
    export_results([result], path)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["caption"] == "'=1+1"
    assert row["filename"] == photo.name


def test_export_existing_file_requires_permission(photo, tmp_path):
    path = tmp_path / "out.json"
    path.write_text("keep")
    with pytest.raises(FileExistsError):
        export_results([CaptionResult(str(photo))], path)
    assert path.read_text() == "keep"
    export_results([CaptionResult(str(photo))], path, overwrite=True)
    assert '"schema_version"' in path.read_text()


def test_export_leaves_no_temp_files(photo, tmp_path):
    export_results([CaptionResult(str(photo))], tmp_path / "out.json")
    assert list(tmp_path.glob(".lumacaption-*")) == []


@pytest.mark.parametrize("options", [{"length": "invalid"}, {"beams": 0}, {"beams": 6}])
def test_options_validation(options):
    with pytest.raises(ValueError):
        CaptionOptions(**options)


def test_cli_rejects_missing_input(capsys):
    from lumacaption.cli import main

    assert main(["missing-image.jpg"]) == 2
    assert "Not a supported image" in capsys.readouterr().err


def test_cli_exports_errors_without_model(tmp_path):
    from lumacaption.cli import main

    corrupt = tmp_path / "bad.jpg"
    corrupt.write_bytes(b"bad")
    assert main([str(corrupt), "--output", str(tmp_path / "errors.json")]) == 1
