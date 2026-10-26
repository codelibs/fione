# fione-sdk

Python client for Fione. It talks to the Fione API with an API token, so you
can use it from a notebook or a script.

## Install

```sh
pip install ./sdk
```

## Configure

The client reads two environment variables (or take `url=` and `token=` arguments):

| Variable | What it is |
|---|---|
| `FIONE_URL` | The address of your Fione server, for example `http://localhost:8080`. |
| `FIONE_TOKEN` | An API token (create one on the Account page). |

## Example

```python
import pandas as pd
from fione_sdk import Client

fione = Client()
project = fione.create_project("demo")
dataset = fione.upload(project["id"], pd.read_csv("train.csv"), "train")
print(fione.profile(project["id"], dataset["id"]))
frame = fione.read(project["id"], dataset["id"])
```

Errors raise `fione_sdk.FioneError`, which carries the HTTP `status`, the API's error `code`
and a `message`.
