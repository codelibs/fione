# MCP

Fione serves tools to MCP clients (an AI tool such as Claude Code or Codex, or an editor that
speaks MCP): read-only tools, and tools that create projects, upload datasets, start jobs and
predict (see below). The client's own language model decides what to call; the tools, the
proposed training configuration and Join included, are Fione's own computations, so MCP needs no
language model in Fione and works with the [assistant](assistant.md) off. The endpoint is `/mcp`
on Fione's own port, for example `http://127.0.0.1:8080/mcp`.

**Behind a reverse proxy, block `/mcp` unless you want MCP clients outside your network.** The
Compose stack publishes Fione on `127.0.0.1` only.

## On and off

MCP is **on by default**, with the tools that change things. Nothing answers without an API token,
which each person creates for themselves, and a token has the same rights as its owner in the
REST API. An administrator switches MCP, or only the tools that change things, off and on again on
the **System** page; the change applies to the next call, outstanding upload URLs included. The
server's settings set the limit: `FIONE_MCP_ENABLED=false` keeps MCP off and
`FIONE_MCP_WRITE_ENABLED=false` keeps the tools that change things off, whatever the System page
says (in `docker/.env` for Compose).

## Connecting a client

1. Create an API token on the **Account** page.
2. Give the client the URL and the header `Authorization: Bearer <the token>`. Many clients take
   a configuration like this:

   ```json
   {"mcpServers": {"fione": {"type": "http", "url": "http://127.0.0.1:8080/mcp",
                             "headers": {"Authorization": "Bearer <your token>"}}}}
   ```

The client acts as the token's owner and sees the projects that person can read: it can list
projects, datasets and models and read their descriptions, results and explanations, and it can
get a proposed training configuration or Join back, which is not saved. With the tools that
change things off, it cannot start or change anything. It never receives example values. A token
has the same rights as you, so keep it secret. At most two tool calls run at once.

## Claude Code

Claude Code takes the same URL and header:

```
claude mcp add --transport http fione http://127.0.0.1:8080/mcp \
  --header "Authorization: Bearer <your token>"
```

Codex reads the token from an environment variable:

```
export FIONE_TOKEN=<your token>
codex mcp add fione --url http://127.0.0.1:8080/mcp --bearer-token-env-var FIONE_TOKEN
```

## Starting jobs from an MCP client

While the tools that change things are on, the client also gets the tools below, as the
token's user. `create_project` needs the role of an editor or an administrator; `upload_dataset`,
`create_upload_url`, `start_training`, `start_batch_predict`, `run_module` and `cancel_job` need
write access to the project (an owner or editor, as for the REST API); the others need only read
access:

| Tool | What it does |
|---|---|
| `create_project` | Creates a project the user owns and returns its `project_id`. |
| `upload_dataset` | Adds a dataset (type `train`, `test` or `predict`) from CSV text (or JSON Lines) sent inline, at most 512 KiB of UTF-8. |
| `create_upload_url` | Returns a one-time URL for a CSV or JSON file of any size up to `FIONE_MAX_UPLOAD_BYTES`. |
| `start_training`, `start_batch_predict`, `run_module` | Queue a job and return its `job_id`. `list_modules` gives each module's parameters. |
| `get_job`, `wait_for_job`, `list_jobs` | Show a job's status and, once finished, its result (`model_id` of a training, `dataset_id` of a batch prediction); the newest 50 jobs. |
| `cancel_job` | Cancels a queued or running job. |
| `predict` | Predicts 1 to 1000 rows now, given as objects. |
| `get_predictions` | Reads the predictions of a finished batch prediction, in pages. |

They delete nothing, and no tool returns example values. Fione cannot ask a person to confirm, so the
client's own approval step is the only one: the tools are marked as changing things so that a
client asks. A token has the rights of its user; for a client that must not start jobs, use the
token of a user who can only read.

**Waiting for a job.** `wait_for_job` waits up to `timeout_secs` (default 10, at most 15) and
returns the job with `done` set to whether it has finished; call it again while `done` is
false. A waiting call holds one of the two MCP slots, which is why the wait is short. A job's
`message` is not sent over MCP: it is `null` and `message_hidden` is `true`; the status and
`get_training_events` tell what happened.

**Uploading a dataset.** `upload_dataset` is for small files. For a larger one, a client that
has a shell calls `create_upload_url` and sends the file with the `example` command it returns,
`curl -T file.csv '<url>'` (an HTTP PUT of the raw CSV; no credentials are needed, so keep the
URL private). The URL is valid for 15 minutes and for one successful upload: a failed upload (a
CSV that does not parse, a file over the limit) does not use it up. It begins with
`FIONE_PUBLIC_URL` when that is set, otherwise with the address of the request; behind a
reverse proxy set `FIONE_PUBLIC_URL`, so that the URL is the public one. The URL carries the
token: Fione's own logs and its access log hide it, but a proxy's access log records it, so
redact paths that start with `/api/v1/uploads/` there.

**Predicting.** `predict` takes `rows`, each an object with a value for every column the model
reads (other keys are ignored), and returns one prediction per row in order: `predict` and, for
classification, `p_<class>` for each class. The rows are not stored. The result must fit in
32 KiB; a larger request is refused with about how many rows fit, and for more rows you
upload a `predict` dataset, run `start_batch_predict` and read the result with
`get_predictions`. `get_predictions` returns the prediction columns only, never the input
values, `limit` rows at a time from `offset`; when the page is cut to fit 32 KiB, `truncated` is true
and the next page starts at `offset` plus the rows returned.

An example with Claude Code, which has a shell:

1. `create_project` with a name.
2. `create_upload_url` for that project (`name`, type `train`), then `curl -T train.csv '<url>'`
   in the shell. The answer describes the dataset.
3. `describe_dataset`, then `propose_training_config` with the `target` column.
4. `start_training` with the proposed `config`, then `wait_for_job` with the returned `job_id`
   until `done` is true; the finished job's result has the `model_id`.
5. `get_leaderboard`, then `predict` with `rows` as objects,
   one value for each column the model reads.

An example with Claude Desktop, which has no shell: the same steps, but in step 2 call
`upload_dataset` with the CSV text in `csv_text` (at most 512 KiB). For more rows than `predict`
takes, call `upload_dataset` with type `predict`, `start_batch_predict`, `wait_for_job`, and then
`get_predictions` with the result `dataset_id`.

The result of `propose_join` has the keys `proposal` (`true`), `kind` (`join`), `config` (the
parameters of the Join module), `warnings` and `rationale`, with the warnings as below.
`propose_first_join` takes the project and `target`, the column to predict, and has the same
keys and `dataset_id`, the base dataset it chose.

The result of `propose_training_config` has the keys `proposal` (`true`), `config`,
`ignored_suggestions`, `warnings` and `rationale`. Each warning is an object `{code, message, params}`: `message` is an English
sentence, and `code` with `params` name the warning in a form any language can be built from. Each entry of
`ignored_suggestions` is `{column, reason, code}`, with `reason` in English too.
