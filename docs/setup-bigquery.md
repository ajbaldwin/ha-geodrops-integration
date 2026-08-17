# Setting up BigQuery access

This service reads GeoDrops sensor data from a **public** BigQuery dataset
(`geodrops-prod.db_public`) using credentials from *your own* GCP project. You are
not given access by GeoDrops directly — you create a project, create a service
account in it, and that service account queries the public dataset the same way
any GCP principal with the right IAM grant could.

> **⚠️ Unverified: exact IAM steps below.**
> The steps in this document — specifically, which IAM role(s) must be granted and
> on which resource (project vs. dataset) — reflect how querying a BigQuery public
> dataset generally works, but they have **not been re-verified end-to-end against
> a fresh GCP project** for this specific dataset. Treat the role names below as a
> starting point, not a confirmed recipe. If a step fails with a permissions error,
> that's the most likely place to look. See [Task 10 brief / spec §10] for
> background — this is a known, tracked documentation gap, not an oversight.

## 1. Create or choose a GCP project

1. Go to the [GCP Console](https://console.cloud.google.com/) and create a new
   project (or reuse an existing one). Note its **project ID** — you'll put this
   in `config.yaml` as `gcp.project_id`.

## 2. Enable the BigQuery API

1. In the console, go to **APIs & Services → Library**, search for "BigQuery
   API", and enable it for your project.
2. This also enables billing-relevant quota for query jobs run under your
   project. Querying the GeoDrops public dataset uses your project's on-demand
   query quota/billing, not GeoDrops'.

## 3. Create a service account

1. **IAM & Admin → Service Accounts → Create Service Account**.
2. Give it a name (e.g. `geodrops-sync`). No console access needed — this is a
   machine identity.
3. Grant it a role on **your own project** that allows running query jobs:
   **BigQuery Job User** (`roles/bigquery.jobUser`) is the standard minimal role
   for "can run queries, billed to this project." Confirmed as the right role for
   running jobs; this part is standard BigQuery practice, not GeoDrops-specific.

## 4. Grant read access to the GeoDrops public dataset

> **⚠️ Unverified.** This is the step flagged above. Public BigQuery datasets are
> normally shared by the dataset owner granting `roles/bigquery.dataViewer` (or
> equivalent) to `allAuthenticatedUsers` or `allUsers` on the dataset itself, in
> which case **no per-project grant is needed at all** — any service account with
> `bigquery.jobUser` on its own project can already query the public dataset
> without an explicit dataset-level grant, because GeoDrops (as dataset owner) has
> already made the grant on their side.
>
> If querying `geodrops-prod.db_public` fails with a permissions error after
> completing steps 1–3, the likely fix is one of:
> - Confirm the dataset is actually shared publicly (check with the GeoDrops forum
>   thread / community for the current state — dataset sharing can change).
> - If GeoDrops requires an explicit allow-list, you may need to request access
>   for your specific service account's email rather than relying on public
>   sharing.
>
> **Verify this against a fresh GCP project before relying on it**, and update
> this doc with the confirmed behavior once checked.

## 5. Download the service-account JSON key

1. On the service account's **Keys** tab, **Add Key → Create new key → JSON**.
2. Save the downloaded file somewhere outside the repo (it's already covered by
   `.gitignore` via the `*.json` pattern, but don't rely on that — keep it out of
   the working tree entirely, or note git status stays clean after saving).

## 6. Point the service at the key

Set the standard GCP environment variable before running (this project reads it
directly and requires it to be set — there is no config.yaml key for this):

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account.json
```

With Docker Compose, place the key at `./service-account.json` in the repo root —
`docker-compose.yml` bind-mounts it to `/secrets/service-account.json` and sets
the env var for you.

## 7. Set `gcp.project_id` in `config.yaml`

```yaml
gcp:
  project_id: your-gcp-project-id
```

This is your project (from step 1), **not** `geodrops-prod` — queries run in your
project's billing/job context against the public dataset in GeoDrops' project.
