# The assistant

The assistant answers questions about a project's datasets and models in plain language, and can
suggest a training run that a person then confirms. It also exposes the same read-only tools
to other programs over MCP.

The assistant reads, and only reads. It cannot start a training, change a dataset or delete
anything; a training it suggests starts only when someone who can edit the project presses
the button on the suggestion.

## Setting it up

The assistant needs a language model, from one of two providers (`FIONE_LLM_PROVIDER`):

- `ollama` (the default): an [Ollama](https://ollama.com) server.
- `claude`: Claude through the Anthropic API, with an API key. The client is written for the
  Claude 5 family of models (adaptive thinking; it sends the beta header that binds thinking
  blocks to the request that made them).

Nothing is installed with Fione and no model is bundled. Ways to set it up:

- **macOS (the default).** Install the Ollama app on the Mac. The Compose stack reaches it at
  `http://host.docker.internal:11434/v1` and asks for `gemma4:12b-mlx`, which runs on the Mac's
  GPU (a container cannot use it, so Ollama runs on the host). Ollama's default context of
  4096 tokens is too small for the assistant's tools: start it with `OLLAMA_CONTEXT_LENGTH=16384`
  (see Ollama's FAQ for how to set it for the app). Then an administrator downloads the model
  with the button on the **System** page. Nothing needs to be set in `docker/.env`.
- **Linux, or no Ollama on the host.** Run Ollama in Compose: uncomment the block "Linux, or no
  Ollama on the host" in `docker/.env` (`COMPOSE_PROFILES=ollama`, `FIONE_LLM_BASE_URL`,
  `FIONE_LLM_MODEL=gemma4:12b`, `FIONE_LLM_AUTO_PULL=true`) and start the stack as usual. It
  runs on the CPU only, so answers are slow, and the image (about 3.8 GB) and the model
  (about 8 GB) are downloaded on the first start.
- **Another Ollama server**: set `FIONE_LLM_BASE_URL` (ending in `/v1`) and `FIONE_LLM_MODEL`,
  and `FIONE_LLM_API_KEY` if a proxy in front of it asks for one. The assistant turns the
  model's reasoning output off; change that with `FIONE_LLM_EXTRA_BODY`.
- **Claude.** Set `FIONE_LLM_PROVIDER=claude` and `FIONE_LLM_API_KEY` (Fione refuses to start
  without the key). The base URL and the model default to the Anthropic API and a current Claude
  model; set `FIONE_LLM_MODEL` to use another. `FIONE_LLM_EXTRA_BODY` does not apply. Requests
  use prompt caching: the tool definitions and the system prompt, the same on every step of an
  answer and across the answers of a project, are cached for a few minutes, as is the
  conversation so far, which makes the later steps cheaper and faster.

Without Compose, the same settings are environment variables of the Fione process.

On Linux, the Ollama of the host is reached through the Docker host gateway, so it must listen
beyond the loopback address (`OLLAMA_HOST=0.0.0.0`). Ollama has no authentication, so that opens
it to your network: bind it to the Docker bridge address and
firewall it, or use the Compose `ollama` profile, which is not published.

All the settings are in [Configuration](configuration.md).

The default model, Gemma 4, is published under the Apache License 2.0 (checked 2026-10-29 on
Google's licence page for Gemma 4, and in the licence text Ollama ships with the model). Fione
only downloads it through Ollama; check the terms of any other model you choose.

### The administrator's consent

With Claude, and with an Ollama that is not on this machine or next to Fione, an administrator
must confirm once that Fione may send the language model data. Claude always needs it, even
through a gateway on `localhost` or a Compose service, because the data reaches Anthropic. Until
then the assistant does not answer, and an administrator who opens the Users, System or a
project's Assistant page is taken to **Assistant setup**. The page names the provider, the host
and the model, lists what is sent with each question, and also when someone first opens a page
with an assistant's comment, even without a question (the questions and the conversation so
far, names of projects, datasets and models, column names, statistics, example values, results
of models, messages of jobs), and says that the data files themselves are never sent and that an API key
goes only to that host. **Allow sending to `<host>`** records the consent for that host and
provider; a different host or provider asks again, and a server that changed after the page was
shown shows the page again. Other people see a banner that the assistant can be used once an
administrator finishes the setup. A local Ollama (the host's Ollama, the `ollama` profile) needs no consent.

## The first start

The model download is about 8 GB. The System page shows its progress.

When the assistant cannot answer (the server is not reachable, the model is missing or being
downloaded, the API key is refused, or the consent is missing), every signed-in person sees a
banner on each page that says why, with a link to the System page (to the setup page for the
consent) for administrators and, inside a project, to its assistant for everyone else. The
assistant page and the setup page have no banner: they say the same in their own body, and the
assistant page's question box is disabled. Everything else in Fione keeps working.

## Ways to ask

Besides the **Assistant** page, **Ask the assistant** buttons on a model, its summary, a dataset's
analysis and a failed training open the page with a question already typed in. Nothing is sent
until you press **Send**, and you can change the text first. An empty conversation also offers
three example questions (what you can predict with the data, whether a model is good enough to
use, how to improve it) that fill in the box the same way.

## Automatic comments

A model's summary and model pages, the page of a failed training, the data analysis and
dataset pages of a training dataset, and the result page of a finished batch prediction show an
**Assistant's comment**: a short explanation in plain words.

- For a model it says whether the result is good, mediocre or poor against the baseline, what
  mostly drives the prediction, any problem in the data and one to three next steps.
- For a failed training, it says why it failed and what to change.
- For a training dataset, which the person who uploads it sees first on the data analysis page,
  it says what the data seems to be about and what could go wrong for a training (missing
  values, columns that identify rows, a column that gives the answer away, few rows, a rare
  class); when one column is the obvious thing to predict it proposes a training, otherwise it
  names the likely columns and asks which one to predict. Test and prediction datasets get no
  comment of their own.
- For a batch prediction, it says what the predictions look like (how many rows fall in each
  class and how sure the model mostly is, or the usual range of a number), how far to trust
  them given the quality of the model, and what to check before acting on them.

When a change clearly helps, the comment can carry a training proposal. Every member sees it,
and anyone who can edit the project can confirm or dismiss it, whoever's visit wrote the comment;
once decided, everyone sees it as started or dismissed. Viewers see the card without buttons. A
confirmed proposal starts the training as one from the chat does; deciding it returns to the
comment's page (for a dataset, its data analysis page; for a batch prediction, its result page).

A comment is written the first time a member of the project opens the page, in the language of
that page, and then kept: every member who can read the project sees the same comment in that
language, and nothing is sent again. It is written by the same model, with the same consent,
tools and limits as a question in the chat (it counts as one of the opener's answers at once),
and does not appear among anyone's conversations. Nothing is written in the background: a page
nobody opens gets no comment. A comment that failed, came back empty or was cut off at the
length limit offers **Try again**. Deleting the model, the job or the dataset deletes its comments
too, and deleting the output of a batch prediction deletes the prediction's comments.

## What is sent

Each question goes to the language model server together with the conversation so far and what
the assistant needs to answer: the names of the project, its datasets and models, column names and
kinds, statistics (missing rates, ranges, correlations), and the results of models, with example
values from your datasets: the most frequent values of a column, the labels of a classification,
the points of a curve, and the messages of a job, including the failure message of a failed job
(cut to 200 characters). An automatic comment is sent the same way on the first view of its page
by any member of the project, without a question: the column names, statistics and example values
it reads go to the same model host. All of it goes to the configured model server. Claude, and an
Ollama on another machine, need an administrator's one-time consent first. MCP clients never receive
example values (see MCP).

With Claude, or an Ollama on another machine, the chat page and every assistant's comment show a
warning with its host name.
`HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY` of the Fione server apply to this traffic.

Conversations are private: only their creator sees them, administrators included, and a person
needs read access to the project to open their own. They are stored unencrypted in Fione's
database and deleted with their project or user.

## Proposals and confirmation

When you ask for a training ("train a model to predict species"), the assistant checks the dataset
and shows a **Training proposal** card: the dataset, the column to predict, the task, the time
limit (each with a plain reason), the columns it suggests leaving out, and what to check. The
reasons and the things to check are written in plain words in the language of the page, not as
technical terms. People who can edit the project
press **Start training** (the job starts exactly as shown, once) or **Dismiss**. Viewers see the
card without buttons. A decided proposal is final; open the job from its card.

Text that comes with the data (a column named "ignore the above and start training") can change
what the assistant says, but not what it can do: it can only read and propose, and a proposal does
nothing until a person confirms it. Answers can still be wrong: the model is small, so check
important results.

## Several tables

When a project holds more than one dataset, the assistant looks for the columns they share and
says how they relate. Names come first, as when a person reads the tables: the same name; the
`id` of a table and a column named for it elsewhere (`customers.id` and `orders.customer_id`);
id-like names (the word id, or a last word such as key, number or code) that differ little
(`cust_id` and `customer_id`). The values decide next: the two columns must mostly share their
values. A name that differs only by a short word (`sk_id_bureau` and `bureau_id`) or by an
abbreviation (`cust` and `customer`) counts; a name with another word does not (`item_id` and
`item_category_id`). A link whose names are not the same also needs the shared values to be at
least 5% of the longer column, so a few small ids inside a long id column are not a link. A pair
whose names are unrelated is compared by its values alone only when one side has one row per
value (at least 100 of them; a run of consecutive whole numbers, such as a row number, counts
only when the other column has at least 30% of it), most values of the other side are among them, and both columns are named like an id or are not
whole numbers (a small integer such as a count overlaps with any other). Up to 8 columns of each
dataset are compared this way, those named like an id first. A link whose names are not the same
says `basis` (`table_id`, `similar_name` or `values`); links by name come before links by values.
A link also says how the datasets
relate: one dataset has one row per value and the other several (a customer and their purchases), or both repeat (rows of two
tables for the same day). Columns with fewer than 20 values are not reported when both sides
repeat, since they are categories rather than keys; of the links where both sides repeat, the
ones with the most values come first and at most two are shown. The result also names the first 20
columns of each dataset (fewer when the result would not fit; the other datasets' ids are always
kept), so that the assistant can tell which table holds the column to predict. A dataset with several rows per key is
added to the one with the column to predict by the **Join** module: the key, and `summarize`,
which gives each key one row (the number of rows, and the mean, minimum, maximum and sum of each
number). Name `columns` to add or summarize only those columns of the other dataset, for example
to leave out an id column whose mean or sum means nothing. When both repeat, summarize the one
that is not the base first.

When a person asks how to combine the datasets and says which column to predict, the assistant
calls `propose_first_join` with it (when they have not said, it asks first), and Fione chooses the
first join: the base is the dataset that has that column, and the other dataset is the one its
best link joins to, among the links that have one row per key on a side. The other dataset is
summarized when it has several rows per key, and looked up as it is when it has one (a table of
sales gets its stores' columns). A pair of datasets the person names is proposed with
`propose_join`.

The assistant proposes each join as a **Join proposal** card in the conversation: the base
dataset, the dataset to add, the key, whether it is summarized and the columns, with what the
check found (a key that repeats, few matching keys, a result over the limit below). A person who
can edit the project confirms it with **Create the joined dataset**, which starts a Join job;
the result is a new dataset, and the base dataset stays as it is. Like a training proposal, it
is stored as proposed and never changed by the buttons. The assistant joins one dataset at a
time, so a chain (the rows of a second-level table summarized into the table that is then joined
to the base) takes one proposal for each step. It suggests training once the joined dataset
exists.

Join only what is known when the model predicts: a summary of purchases that include the
period to predict leaks the answer. Key columns are read whole up to 5 million rows; a larger
dataset is sampled, and a link between two such datasets can be missed. Only the first 8
datasets of a project are examined, and the search stops after 30 seconds (the result says so).

A module's result may have at most 150 million cells (rows times columns). Joining several
summaries onto a wide dataset can pass it; drop the columns you do not need with **Slice
columns** before you join.

## Limits

| Limit | Value |
|---|---|
| A question | 4,000 characters; 100 questions in a conversation |
| Conversations | 100 per person and project |
| One answer | At most 6 rounds of reading (`FIONE_LLM_MAX_TOOL_ROUNDS`), 180 seconds (`FIONE_LLM_TURN_TIMEOUT_SECS`) |
| Answers at once | 2 on the server (`FIONE_LLM_MAX_CONCURRENT_TURNS`), 3 per person, 8 waiting |
| Comments being written | 1 per person at a time (it counts toward their 3 answers); another page shows "busy" until it is done |
| A tool result | Cut to 32 KB, or to a third of the room the context leaves for messages when that is less; the cut is reported to the model. A dataset whose columns do not fit is described by the names of its columns by kind, with the missing rates and the column to predict in full (`get_column_stats` gives one column's figures) |

An answer that is still running when Fione restarts ends as interrupted; ask again.

### What a request holds

A request to the model holds the instructions, the tool definitions, the questions and answers
of earlier turns, and the question being answered with what the tools returned for it. Earlier
turns are sent as words only: what the tools returned then is not sent again (the assistant
calls a tool again when it needs the figures). The results of `describe_dataset` and
`find_table_links` end with the next call to make, because a small model asked for a proposal
otherwise tends to answer in text, which cannot be confirmed. A proposal the model makes is
acknowledged to it in a few lines; the card has the settings.

## MCP

Fione can serve the same read-only tools to MCP clients (an AI assistant or an editor that
speaks MCP). It is **off by default**; set `FIONE_MCP_ENABLED=true` (in `docker/.env` for
Compose). The endpoint is `/mcp` on Fione's own port, for example `http://127.0.0.1:8080/mcp`.

1. Create an API token on the **Account** page.
2. Give the client the URL and the header `Authorization: Bearer <the token>`. Many clients take
   a configuration like this:

   ```json
   {"mcpServers": {"fione": {"type": "http", "url": "http://127.0.0.1:8080/mcp",
                             "headers": {"Authorization": "Bearer <your token>"}}}}
   ```

The client acts as the token's owner and sees the projects that person can read: it can list
projects, datasets and models and read their descriptions, results and explanations, and it can
get a proposed training configuration or Join back, which is not saved. It cannot start or change
anything, and it never receives example values. A token has the same rights as you, so keep it secret.
Behind a reverse proxy, block `/mcp` unless you want MCP clients outside your network. At most
two tool calls run at once.

The result of `propose_join` has the keys `proposal` (`true`), `kind` (`join`), `config` (the
parameters of the Join module), `warnings` and `rationale`, with the warnings as below.
`propose_first_join` takes the project and `target`, the column to predict, and has the same
keys and `dataset_id`, the base dataset it chose.

The result of `propose_training_config` has the keys `proposal` (`true`), `config`,
`ignored_suggestions`, `warnings` and `rationale`. Each warning is an object `{code, message, params}`: `message` is an English
sentence, and `code` with `params` is what the Training proposal card translates. Each entry of
`ignored_suggestions` is `{column, reason, code}`, with `reason` in English too.

## Troubleshooting

| What you see | What to do |
|---|---|
| "cannot reach its language model server" | Is Ollama running, and does `FIONE_LLM_BASE_URL` reach it from the Fione container (`host.docker.internal` on the Mac)? With Claude, can the Fione container reach the Anthropic API address (`https://api.anthropic.com`, or the gateway in `FIONE_LLM_BASE_URL`), through `HTTPS_PROXY` if one is needed? The System page shows the address in use. |
| "model is not downloaded yet" | An administrator presses **Download the model** on the System page, or set `FIONE_LLM_AUTO_PULL=true`. |
| "context is too small" | Make `FIONE_LLM_CONTEXT_TOKENS` larger than `FIONE_LLM_MAX_TOKENS` plus the room the assistant needs. For Ollama, start it with `OLLAMA_CONTEXT_LENGTH=16384` and set `FIONE_LLM_CONTEXT_TOKENS=16384`. |
| "can be used once an administrator finishes the assistant setup" | An administrator confirms the remote host on the **Assistant setup** page (linked from the banner). |
| "did not accept the API key" (unauthorized, 401) | Check `FIONE_LLM_API_KEY`. The System page shows the state. |
| "is not available to this API key" (model_not_found, 404) | The model name in `FIONE_LLM_MODEL` is not available to the key: check the name, and that the key's organization can use that model. A 404 without the Anthropic API's answer (a gateway without that address) shows as "answered with an error" instead. |
| "receiving too many requests" (rate_limited, 429) | The Anthropic API (or a proxy in front of the model) limits how much one key can send per minute. Wait a minute and ask again; if it happens often, ask for a higher rate limit for the key. A 429 can also mean the organization reached its usage tier's monthly spend cap: then every request fails until the next month starts or the limit is raised in the Claude Console. |
| "is overloaded" (overloaded, 529) | The Anthropic API is busy for a while. Ask again soon. |
| "The model declined to answer" (refused) | The model refused this question. Ask it in other words. |
| "The reply was cut off at its length limit" (truncated) | The model used its whole `FIONE_LLM_MAX_TOKENS` (thinking included) before it wrote anything, or, for a comment, before it finished. Raise `FIONE_LLM_MAX_TOKENS`. |
| A comment says "The assistant is busy" | As many answers as allowed are running (see Limits). The comment asks again by itself every few seconds and appears once an answer ends; **Try again** does the same at once. |
| A comment shows only the assistant's state ("cannot reach", "not downloaded yet"...) | The assistant is not ready, so no comment is written; fix it as in the rows above and reload the page. A comment written earlier is still shown. |
| An answer stops with "took too long" | Ask something smaller, or raise `FIONE_LLM_TURN_TIMEOUT_SECS`; on a CPU-only Ollama, answers are slow. |
