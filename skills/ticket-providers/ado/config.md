# ado — config

Read by `ticket-setup`.

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

**No credential is in either file, or anywhere in the tickets home.** The Azure CLI holds the sign-in.

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

## How the credential is held

**There is no PAT, and nothing is cached.** The user is never asked for a credential — they only need to stay signed in with `az login`. Every call this suite makes goes through `az rest --resource 499b84ac-1321-427f-aa17-267ca6975798`, and that resource id is the audience a token must be issued for to be accepted by `dev.azure.com`. `az` attaches and refreshes the token itself.

**Never print or read a token.** Do not run `az account get-access-token`, and do not read one from a file or an environment variable.

## How it is validated

Before anything is written, the init verb reads the project:

```
az rest --resource 499b84ac-1321-427f-aa17-267ca6975798 --method get --url https://dev.azure.com/{org}/_apis/projects/{project} --url-parameters api-version=7.1
```

The failure modes are distinguished, because they call for different fixes:

| Failure      | Means                                                                |
| ------------ | -------------------------------------------------------------------- |
| sign-in      | `az login` has expired — run `az login --scope 499b84ac-1321-427f-aa17-267ca6975798/.default` |
| Forbidden    | Access denied to that project in that organization                   |
| Not Found    | No such project in that organization — usually a typo in `--project` |

A missing Azure CLI or an expired `az login` surfaces as a clear error rather than a hang. Nothing is written when validation fails. `--propose` validates nothing: it only reports the coordinates and where they would be filed.

## Report back

On success, state which organization and project were bound and under which product, and which of them were inherited or came from a default. Add that nothing is stored: later runs work as long as the user stays signed in with `az login`.
