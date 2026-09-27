# ado — config

Read by `ticket-init`.

## What an ado binding holds

Two coordinates, each at its own level — which is what makes a namespace an Azure DevOps organization and a product one of its projects:

| Coordinate     | Bound at  | Meaning                                                                                  |
| -------------- | --------- | ---------------------------------------------------------------------------------------- |
| `organization` | namespace | The ADO organization **name**, not a URL — `edwire`, not `https://dev.azure.com/edwire`. |
| `project`      | product   | The ADO project name.                                                                    |

```json
// {namespace}/config.json
{ "sources": { "ado": { "organization": "edwire" } } }

// {namespace}/{product}/config.json
{ "sources": { "ado": { "project": "EW.Educate" } } }
```

One namespace is bound to one organization, and each project to one product. A second project in the same organization is a second product in the same namespace, and its init needs only `--project`: the organization is inherited.

**No credential is in either file.** The Azure CLI token is cached at `.credentials/ado/{organization}.json` in the tickets home, keyed by organization, so one organization's token is never handed to another.

## Defaults

Each coordinate is taken, in order, from:

1. the flag the user gave;
2. what the target product already inherits — its namespace's `organization`;
3. this source's own default:

| Value        | Default      |
| ------------ | ------------ |
| Organization | `edwire`     |
| Project      | `EW.Educate` |

Pass `--org` or `--project` through to the init verb **only** when the user explicitly supplied that value; every omitted flag falls through the list above. Never ask for either — say which ones were inherited or defaulted afterwards, so a default is never applied silently.

```
python "{skills}/ticket-common/ticket.py" init --source ado [--in {namespace}/{product}] [--org {org}] [--project "{project}"] [--propose]
```

Where the binding is filed when `--in` is omitted: the product already bound to exactly these coordinates, else a new product in the namespace already bound to the organization, else names derived from the coordinates — `edwire`, `ew-educate`.

## How the credential is acquired

**There is no PAT.** The user is never asked for a credential — they only need to stay signed in with `az login`. The init verb runs:

```bash
az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798
```

That resource id is the audience a token must be issued for to be accepted by `dev.azure.com`. The whole JSON response is cached under the organization it was validated against.

Every later call reuses the cached token while it is still good, and re-runs the Azure CLI to replace it once it is within five minutes of expiring, writing the fresh response back. Tokens live about an hour, so the refresh is routine and needs no user involvement.

**Never run `az account get-access-token` from a driver, and never read the credential store.** Token handling belongs to the provider module.

## How it is validated

Before anything is written, the acquired token is used against:

```
GET https://dev.azure.com/{org}/_apis/projects/{project}?api-version=7.1
```

The failure modes are distinguished, because they call for different fixes:

| Status | Means                                                                |
| ------ | -------------------------------------------------------------------- |
| 401    | The token was rejected — `az login` has expired                      |
| 403    | Access denied to that project in that organization                   |
| 404    | No such project in that organization — usually a typo in `--project` |

A missing Azure CLI or an expired `az login` surfaces as a clear error rather than a hang. Nothing is written when validation fails. `--propose` validates nothing and acquires nothing: it only reports the coordinates and where they would be filed.

## Report back

On success, state which organization and project were bound and under which product, which of them were inherited or came from a default, and when the token expires. Add that the token refreshes itself on later runs as long as the user stays signed in with `az login`.
