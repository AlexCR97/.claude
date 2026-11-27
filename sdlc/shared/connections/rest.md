# REST connection

Instructions for a connection of kind `rest`: an HTTP API reached with a base URL and a credential. Everything in [`generic.md`](generic.md) applies; this adds what is particular to HTTP. The policy is [`../connections.md`](../connections.md).

## The profile

A `rest` profile holds `BASE_URL`, the API root (`https://...`, no trailing slash), and the keys of one authentication scheme. The runner passes whatever keys the profile has, and you read only their names, with `connection check`, never a value. The key names say which scheme to use:

| Scheme                      | Keys beside `BASE_URL`                                         | How it is sent                                                         |
| --------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Access token (bearer)       | `ACCESS_TOKEN`                                                 | `Authorization: Bearer $ACCESS_TOKEN`                                  |
| API key                     | `API_KEY`                                                      | The header or query parameter the API names, from `$API_KEY`           |
| Client credentials (OAuth2) | `CLIENT_ID`, `CLIENT_SECRET`, `TOKEN_URL`, optionally `SCOPE`  | Fetch a token first (see below), then send it as a bearer              |
| Basic                       | `BASIC_USER`, `BASIC_PASSWORD`                                 | `curl -u "$BASIC_USER:$BASIC_PASSWORD"`, which keeps it off the URL    |

A profile whose keys fit none of these (a refresh token, a client certificate, signed requests) uses a scheme this file does not cover: ask the user how to authenticate and do not guess. The names avoid `USER` and `USERNAME`, which are already environment variables on Unix and Windows; a profile key of that name would replace the real one inside the command.

## Calling

Pick the tool that is installed and fits the call: `curl`, `python -c` with `urllib.request` or `requests`, `Invoke-RestMethod` under `pwsh`. Wrap it so the child expands the variables, as [`generic.md`](generic.md) says:

```
python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" connection run <profile> -- sh -c 'curl -sS --fail-with-body -H "Authorization: Bearer $ACCESS_TOKEN" "$BASE_URL/v1/items?limit=20"'
```

- **GET and HEAD are the read-only methods.** Anything else is a write and asks first, with the exact request shown: `POST`, `PUT`, `PATCH`, `DELETE`, and a `GET` that the API documents as changing state. The runner cannot tell, so GET-only is yours to hold. The one `POST` that is not a write is the token request below.
- **https only when a credential is sent.** Never send a token over `http://`, and never put it in the URL's query string unless the API allows nothing else, because URLs reach logs.
- **No verbose or trace flags:** not `curl -v`, `--trace`, `--trace-ascii`, `-i` with a header the server echoes, nor `http --verbose`; they print the request headers, which hold the credential.
- **Do not follow redirects blindly.** Leave `-L` off; a redirect to another host can take the `Authorization` header with it (`--location-trusted` does it deliberately). Read the `Location` and decide.
- **A response can echo a secret.** Treat what comes back as data that may hold one; masking covers only the profile's own values, whole.
- **Page deliberately.** Follow the API's cursor or `limit` and `offset`, a bounded number of pages, and say how many you read. `BASE_URL` is masked wherever it appears in the output, so a `next` link comes back as `***/v1/items?page=2`: build the next request from the cursor or page number in it, not by following the link.
- **Output as JSON** where the API offers it, and filter with the tool (`jq`, `python -c`) inside the same wrapped command, so only the fields you need come back.

## Client credentials

The token request is a `POST`, and it is not a write: it mints a short-lived token and changes no data, so it needs no yes. Three conditions hold:

- **It goes only to `$TOKEN_URL`**, as a form with `grant_type=client_credentials` (and the `SCOPE` when the profile has one).
- **The token never leaves the wrapped command.** Keep it in a shell variable and use it in the same command; never print it, write it to a file or hand it to a later command. It is not a value of the profile, so masking will not catch it. Fetch a new one for the next command.
- **The profile's own gate still applies.** A production profile is reached only when the user's message names it, and `--approved` is passed only then.

```
python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" connection run <profile> -- sh -c 'T=$(curl -sS --fail-with-body -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials -d "scope=$SCOPE" "$TOKEN_URL" | python -c "import json,sys; print(json.load(sys.stdin)[\"access_token\"])") && curl -sS --fail-with-body -H "Authorization: Bearer $T" "$BASE_URL/v1/items?limit=20"'
```

Drop the `scope` line when the profile has no `SCOPE`, and send the client credentials in the body where the API asks for that, not as basic authentication.

## When it fails

A `401` or `403` means the credential lacks the right, not that you should look for another one: report it and ask. A `429` means slow down. A `5xx` is the system's; retry once at most and report it. A redirect (`301`, `302`, `307`, `308`) is data: report the `Location`.
