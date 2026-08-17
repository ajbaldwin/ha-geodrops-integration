# Setting up BigQuery access

This service reads GeoDrops sensor data from a **public** BigQuery dataset
(`geodrops-prod.db_public`) using credentials from *your own* GCP project. GeoDrops
does not grant you access individually — you create a project, create a service
account in it, and that service account queries the public dataset. The query
**runs in and is billed to your project**; the data lives in GeoDrops' project and
is publicly readable.

## How access actually works (the short version)

Two independent things have to be true, and only the first is something you set up:

1. **You must be able to run a query job** — this needs the **BigQuery Job User**
   role (`roles/bigquery.jobUser`) on *your own* project. This is what lets your
   service account create query jobs, billed to your project.
2. **You must be able to read the data** — reading
   `geodrops-prod.db_public.p_sensor_unified` needs a data-read grant *on that
   dataset*. You do **not** create this grant: GeoDrops has shared `db_public`
   publicly, so any authenticated service account already has read access. There is
   no allow-list to join and no approval to wait for.

This is confirmed by the community setup (the GeoDrops HA integration guide):
users create a service account in their own project, grant it BigQuery roles, and
query immediately — no step requests access from GeoDrops.

## 1. Create or choose a GCP project

Go to the [GCP Console](https://console.cloud.google.com/) and create a new project
(or reuse an existing one). Note its **project ID** — you'll put this in
`config.yaml` as `gcp.project_id`. This is the project your queries run in and are
billed to (well within the free tier at this data volume — a few sensors polled a
few times an hour).

## 2. Enable the BigQuery API

In the console, go to **APIs & Services → Library**, search for "BigQuery API", and
enable it for your project. Querying the GeoDrops public dataset uses your
project's on-demand query quota and billing, not GeoDrops'.

## 3. Create a service account and grant it the query role

1. **IAM & Admin → Service Accounts → Create Service Account**.
2. Give it a name (e.g. `geodrops-sync`). No console/user access needed — it's a
   machine identity.
3. Grant it, **on your own project**, the role that allows running query jobs:
   **BigQuery Job User** (`roles/bigquery.jobUser`). This is the one role strictly
   required for this service to work.

> **Note — "BigQuery Data Viewer":** the original community guide also grants
> **BigQuery Data Viewer** (`roles/bigquery.dataViewer`) on your own project. That
> grant is *not* what gives you access to the GeoDrops data — the GeoDrops dataset
> is in a different project and is readable via GeoDrops' own public sharing (see
> below). Data Viewer on *your* project only lets the same service account read
> datasets you own. It's harmless to add and matches the original guide, but Job
> User alone is enough to query the public GeoDrops data.

## 4. Reading the GeoDrops public dataset (nothing to configure)

You do not grant yourself any access to `geodrops-prod`. GeoDrops has published
`db_public` as a public dataset, so a service account that can run query jobs
(step 3) can already read it. The query in this service targets the fully-qualified
table `` `geodrops-prod.db_public.p_sensor_unified` `` while running in *your*
project's job/billing context.

> **If a query ever fails with a permissions/`accessDenied` error** after steps 1–3
> succeed, the cause is almost certainly **on the GeoDrops side**, not yours:
> GeoDrops controls how `db_public` is shared and could change it. Check the
> [GeoDrops forum thread](https://geodrops.discourse.group/t/integrating-geodrops-soil-moisture-sensors-with-home-assistant/280)
> for the current sharing status before assuming your IAM is wrong. Adding roles on
> *your* project cannot fix a read grant that lives on GeoDrops' dataset.

## 5. Download the service-account JSON key

1. On the service account's **Keys** tab, **Add Key → Create new key → JSON**.
2. Save the downloaded file somewhere outside the repo. It is covered by
   `.gitignore` via the `*.json` pattern, but keep it out of the working tree
   entirely rather than relying on that — treat the key as a secret.

## 6. Point the service at the key

Set the standard GCP environment variable before running (this project reads it
directly and requires it to be set — there is no `config.yaml` key for the key
path):

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account.json
```

With Docker Compose, place the key at `./service-account.json` in the repo root —
`docker-compose.yml` bind-mounts it to `/secrets/service-account.json` and sets the
env var for you.

## 7. Set `gcp.project_id` in `config.yaml`

```yaml
gcp:
  project_id: your-gcp-project-id
```

This is your project (from step 1), **not** `geodrops-prod`. Queries run in your
project's job/billing context against the public dataset in GeoDrops' project.
