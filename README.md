# Secrets Manager Project

**Live API:** https://swda9fklsc.execute-api.eu-central-1.amazonaws.com/secret-check

📖 Want the full, beginner-friendly walkthrough of every step, command,
and decision made in this project? See
[PROJECT_GUIDE.md](./PROJECT_GUIDE.md).

## What is this project, in one sentence?

A small serverless API demonstrating proper secret handling: a Lambda
function reads a secret value from AWS Secrets Manager at runtime,
proving it can access it — without ever exposing the value itself, in
code, in the API response, or in version control.

## Why this project exists

The eighth project in this series, and the first of two focused
specifically on core DevOps practices rather than a new AWS compute
service. Every earlier project used **GitHub Secrets** to pass
credentials to the deployment *pipeline* — this project introduces
**AWS Secrets Manager**, the equivalent tool for secrets a *running
application* needs, like a database password or a third-party API key.
"How do you handle secrets?" is a near-universal interview question,
and this project gives a concrete, working answer.

## How it works

```
GET /secret-check
      -> Lambda calls Secrets Manager's GetSecretValue API
      -> reads the secret at runtime (never hardcoded)
      -> returns confirmation + the secret's LENGTH only,
         never the value itself
```

## Architecture

- **Secrets Manager** — stores the actual secret value, separate from
  the application code entirely.
- **Lambda** — reads the secret via `boto3` at invocation time.
- **IAM inline policy** — grants the Lambda's role exactly one
  permission (`secretsmanager:GetSecretValue`) on exactly one resource
  (this specific secret's ARN) — nothing broader.
- **API Gateway** — exposes the function over HTTP.

## Keeping the demo secret itself out of the repo

The secret's actual value was never written into any `.tf` file. It
was stored as a GitHub Secret (`SM_SECRET_VALUE`) and passed to
Terraform via `TF_VAR_secret_value` in the pipeline — the same pattern
used for the alert email in the monitoring addition to
[lambda-api-project](https://github.com/Ralso11/lambda-api-project).
The `secret_value` Terraform variable is also marked `sensitive = true`,
so Terraform never prints it in plan/apply logs either.

## Problems & fixes — quick reference

| Problem | Why it happened | How it was fixed |
|---|---|---|
| `Credentials could not be loaded` on the AWS login step | A GitHub Secret was misspelled (`SW_AWS_ACCESS_KEY_ID` instead of `SM_AWS_ACCESS_KEY_ID`) | Created the correctly-named secret and removed the misspelled one |

Notably, this project deployed cleanly otherwise on the first real
attempt — a sign that lessons from earlier projects (checking every
AWS service the Terraform code touches before picking IAM policies,
building the pipeline manual-trigger-only from the start) had actually
carried forward.

## Cost notes

Very low cost to leave running: Secrets Manager charges roughly
$0.40/month per secret plus a small per-API-call fee, and Lambda/API
Gateway are effectively free at portfolio-demo traffic levels. No
`destroy.yml` was needed for this reason.

## How to reproduce this project

1. Install Git and Terraform.
2. Create a GitHub repo, clone it locally.
3. Write a Lambda function that calls
   `secrets_client.get_secret_value(SecretId=...)` and returns
   something that proves success without exposing the value itself.
4. Write Terraform: an `aws_secretsmanager_secret` +
   `aws_secretsmanager_secret_version` pair, a Lambda function, an IAM
   role with an inline policy scoped to `GetSecretValue` on that one
   secret's ARN, and an API Gateway route.
5. Mark the secret-value Terraform variable `sensitive = true` and give
   it no default.
6. Store the real secret value as a GitHub Secret, pass it to Terraform
   via `TF_VAR_<variable_name>` in the pipeline.
7. Build the pipeline manual-trigger-only (`workflow_dispatch`) from
   the start.
8. Push, manually trigger `apply`, approve, and test with `curl`.

## What's next (possible future additions)

- [ ] Add automatic secret rotation using a rotation Lambda.
- [ ] Store a structured secret (JSON with multiple fields) instead of
      a single string.
- [ ] Use the secret for something real (e.g. an actual third-party API
      key) instead of a demo value.
