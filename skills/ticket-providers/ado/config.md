# ado — config

Read by `ticket-init`.

## What `ado/config.json` holds

```json
{
  "organization": "edwire",
  "project": "EW.Educate",
  "token": {
    "accessToken": "eyJ0eXAiOiJKV1Qi…",
    "expiresOn": "2026-09-03 17:48:31.000000",
    "expires_on": 1788479311,
    "subscription": "…",
    "tenant": "…",
    "tokenType": "Bearer"
  }
}
```

| Key | Meaning |
| --- | --- |
| `organization` | The ADO organization **name**, not a URL — `edwire`, not `https://dev.azure.com/edwire`. |
| `project` | The ADO project name. |
| `token` | The entire Azure CLI token response, cached verbatim. |

## Defaults

Both coordinates have defaults, so in the common case the init needs no input at all:

| Value | Default |
| --- | --- |
| Organization | `edwire` |
| Project | `EW.Educate` |

Pass `--org` or `--project` through to the init verb **only** when the user explicitly supplied that value; every omitted flag keeps its default. Never ask for either — say which ones were applied afterwards, so a default is never applied silently.

```
python "{skills}/ticket-common/ticket.py" init --source ado [--org {org}] [--project "{project}"]
```

## How the credential is acquired

**There is no PAT.** The user is never asked for a credential — they only need to stay signed in with `az login`. The init verb runs:

```bash
az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798
```

That resource id is the audience a token must be issued for to be accepted by `dev.azure.com`. The whole JSON response is stored under `token`.

Every later call reuses the cached token while it is still good, and re-runs the Azure CLI to replace it once it is within five minutes of expiring, writing the fresh response back. Tokens live about an hour, so the refresh is routine and needs no user involvement.

**Never run `az account get-access-token` from a driver, and never read `token` out of the config.** Token handling belongs to the provider module.

## How it is validated

Before anything is written, the acquired token is used against:

```
GET https://dev.azure.com/{org}/_apis/projects/{project}?api-version=7.1
```

The failure modes are distinguished, because they call for different fixes:

| Status | Means |
| --- | --- |
| 401 | The token was rejected — `az login` has expired |
| 403 | Access denied to that project in that organization |
| 404 | No such project in that organization — usually a typo in `--project` |

A missing Azure CLI or an expired `az login` surfaces as a clear error rather than a hang. Nothing is written when validation fails.

## Report back

On success, state which organization and project were used, which of them came from a default, and when the token expires. Add that the token refreshes itself on later runs as long as the user stays signed in with `az login`.
