"""Helpers shared by the web UI tests: a project with one object of every kind."""

import io
from contextlib import closing
from dataclasses import dataclass

from api_helpers import add_user, connect, iris_frame, login, store_model
from fione.auth.roles import ProjectAccess, Role
from fione.jobs import store
from fione.jobs.store import JobStatus
from fione.projects import service as projects
from fione.projects.ingest import ingest_csv
from fione.projects.service import DatasetType

FAST = {"max_models": 1, "nfolds": 2}  # merged into the wizard's training configs


@dataclass
class World:
    """Project ``p`` (owner ``ed``; ``co`` may edit it, ``vi`` may view it; ``st`` is no
    member) with a train dataset, a test dataset, a model, a queued training job and a
    finished prediction job; project ``q`` of ``ed`` has its own copies of each."""

    client: object
    p: str
    q: str
    ids: dict  # project id -> {"train", "test", "model", "job", "predict_job"}
    mode: str | None = None  # the fione_mode cookie set at each login ("detailed")

    def path(self, template: str, project: str | None = None, objects: str | None = None) -> str:
        """``template`` with ``{p}`` and the object ids filled in (``objects``: whose ids)."""
        project = project or self.p
        return template.format(p=project, **self.ids[objects or project])

    def login(self, username: str | None) -> str | None:
        self.client.cookies.clear()
        if self.mode:
            self.client.cookies.set("fione_mode", self.mode)
        return login(self.client, username) if username else None


def iris_test_csv(frame=None) -> bytes:
    """Iris without the species: what a prediction needs."""
    frame = iris_frame() if frame is None else frame
    return frame.drop(columns=["species"]).to_csv(index=False).encode()


def _objects(client, conn, owner, project_id) -> dict:
    storage = client.app.state.storage
    train = ingest_csv(
        storage,
        conn,
        project_id,
        "iris",
        DatasetType.TRAIN,
        io.BytesIO(iris_frame().to_csv(index=False).encode()),
    )
    test = ingest_csv(
        storage, conn, project_id, "iris_test", DatasetType.TEST, io.BytesIO(iris_test_csv())
    )
    model = store_model(conn, storage, client.app.state.secret, project_id)
    config = {"target": "species", "max_runtime_secs": 60}
    job = store.enqueue(
        conn, "automl", project_id, owner.id, {"dataset_id": train.id, "config": config}
    )
    predicted = ingest_csv(
        storage,
        conn,
        project_id,
        "predict_iris_test",
        DatasetType.PREDICT,
        io.BytesIO(iris_test_csv()),
    )
    payload = {"model_id": model.id, "dataset_id": test.id, "include_columns": None, "name": None}
    done = store.enqueue(conn, "batch_predict", project_id, owner.id, payload)
    store.claim_job(conn, done.id, "token")
    store.finish_job(conn, done.id, JobStatus.DONE, result={"dataset_id": predicted.id})
    return {
        "train": train.id,
        "test": test.id,
        "model": model.id,
        "job": job.id,
        "predict_job": done.id,
    }


def make_world(client) -> World:
    owner = add_user(client, "ed", Role.EDITOR)
    add_user(client, "vi", Role.EDITOR)
    add_user(client, "st", Role.EDITOR)
    add_user(client, "co", Role.EDITOR)
    add_user(client, "admin", Role.ADMIN)
    with closing(connect(client)) as conn:
        p = projects.create_project(conn, owner, "P")
        q = projects.create_project(conn, owner, "Q")
        projects.share_project(conn, owner, p.id, "vi", ProjectAccess.VIEWER)
        projects.share_project(conn, owner, p.id, "co", ProjectAccess.EDITOR)
        ids = {p.id: _objects(client, conn, owner, p.id), q.id: _objects(client, conn, owner, q.id)}
    return World(client, p.id, q.id, ids)
