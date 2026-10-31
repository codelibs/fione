"""Load the one model a serving container runs, refusing anything that does not fit."""

from dataclasses import dataclass
from pathlib import Path

from fione.engine.artifact import (
    MODEL_FILE,
    Manifest,
    UntrustedArtifactError,
    load_model_unverified_hash_only,
    read_manifest,
)
from fione.engine.model import TrainedModel
from fione.storage import LocalStorage


class ModelLoadError(Exception):
    """The model cannot be served; the message is one line, meant for the operator."""


@dataclass(frozen=True)
class LoadedModel:
    model: TrainedModel
    manifest: Manifest


def load(model_dir: Path, image_tag: str) -> LoadedModel:
    """Load ``manifest.json`` and ``model.joblib`` from ``model_dir`` for the image ``image_tag``.

    Refuses (``ModelLoadError``) a model made for another image tag, since its pickle refers
    to that version's code, and any file that is missing or does not match its sha256.

    Trust: this checks integrity only (sha256), not the manifest's HMAC, because the serving
    image has no secret. The operator is trusted to deploy only artifacts they trained or
    exported themselves; unpickling an attacker's file would run their code.
    """
    where = f"model in {model_dir}"
    if not model_dir.is_dir():  # LocalStorage would create it, and the mount is read-only
        raise ModelLoadError(f"cannot load the {where}: the directory does not exist")
    storage = LocalStorage(model_dir)
    try:
        manifest = read_manifest(storage, "")
        if manifest.image_tag != image_tag:
            raise ModelLoadError(
                f"the {where} was made for image tag {manifest.image_tag!r}, but this image is "
                f"tag {image_tag!r}; run it with the image tagged {manifest.image_tag}"
            )
        if MODEL_FILE not in manifest.files:
            raise UntrustedArtifactError(f"{MODEL_FILE} is not part of the artifact")
        model = load_model_unverified_hash_only(storage, "")
    except UntrustedArtifactError as e:
        raise ModelLoadError(f"cannot load the {where}: {e}") from e
    except ModelLoadError:
        raise
    except Exception as e:  # a pickle that does not load here (library versions, damage)
        raise ModelLoadError(f"cannot load the {where}: {type(e).__name__}: {e}") from e
    return LoadedModel(model, manifest)
