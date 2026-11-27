# REST connection

Instructions for a connection of kind `rest`: an HTTP API reached with a base URL and a credential. Everything in [`generic.md`](generic.md) applies; this adds what is particular to HTTP. The policy is [`../connections.md`](../connections.md).

## The profile

A `rest` profile conventionally holds `BASE_URL` and one credential variable. The runner passes whatever keys the profile has, so read their names with `connection check` and use them; do not assume these.

| Key (by convention) | Holds                                                |
| ------------------- | ---------------------------------------------------- |
| `BASE_URL`          | The API root, `https://...`, no trailing slash       |
| `TOKEN`             | A bearer token, or an API key, or a password         |
| `USER`              | Only for basic authentication, beside `TOKEN`        |

## Calling

Pick the tool that is installed and fits the call: `curl`, `python -c` with `urllib.request` or `requests`, `Invoke-RestMethod` under `pwsh`. Wrap it so the child expands the variables, as [`generic.md`](generic.md) says:

```
python "${CLAUDE_PLUGIN_ROOT}/shared/sdlc.py" connection run <profile> -- sh -c 'curl -sS --fail-with-body -H "Authorization: Bearer $TOKEN" "$BASE_URL/v1/items?limit=20"'
```

- **Bearer:** `Authorization: Bearer $TOKEN`. **API key:** the header or query parameter the API names, from `$TOKEN`. **Basic:** `-u "$USER:$TOKEN"` in `curl`, which keeps it off the URL.
- **GET and HEAD are the read-only methods.** Anything else is a write and asks first, with the exact request shown: `POST`, `PUT`, `PATCH`, `DELETE`, and a `GET` that the API documents as changing state. The runner cannot tell, so GET-only is yours to hold.
- **https only when a credential is sent.** Never send a token over `http://`, and never put it in the URL's query string unless the API allows nothing else, because URLs reach logs.
- **No verbose or trace flags:** not `curl -v`, `--trace`, `--trace-ascii`, `-i` with a header the server echoes, nor `http --verbose`; they print the request headers, which hold the credential.
- **Do not follow redirects blindly.** Leave `-L` off; a redirect to another host can take the `Authorization` header with it (`--location-trusted` does it deliberately). Read the `Location` and decide.
- **A response can echo a secret.** Treat what comes back as data that may hold one; masking covers only the profile's own values, whole.
- **Page deliberately.** Follow the API's cursor or `limit` and `offset`, a bounded number of pages, and say how many you read.
- **Output as JSON** where the API offers it, and filter with the tool (`jq`, `python -c`) inside the same wrapped command, so only the fields you need come back.

## When it fails

A `401` or `403` means the credential lacks the right, not that you should look for another one: report it and ask. A `429` means slow down. A `5xx` is the system's; retry once at most and report it. A redirect (`301`, `302`, `307`, `308`) is data: report the `Location`.
