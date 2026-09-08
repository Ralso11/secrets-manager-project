# The Complete Guide to This Project
### (Written so anyone, even with zero background, can understand it)

This is the eighth project in a portfolio series. It assumes the
basics from earlier guides (Git, GitHub, Terraform, CI/CD, Lambda, API
Gateway) are already familiar. This one is entirely about **secrets** —
sensitive values an application needs, but that must never appear in
code, logs, or version control.

---

## Part 1 — Two different kinds of "secrets," and why they're not the same

By this point in the portfolio, secrets have already been used many
times — but always as **GitHub Secrets**, feeding AWS credentials to a
*pipeline* so it can deploy infrastructure. Those secrets only exist
during a pipeline run.

**This project introduces a different, equally important kind: secrets
a *running application* needs while it's actually operating** — a
database password, a third-party API key, anything the app must read
*after* it's already deployed, not just during deployment. GitHub
Secrets can't help here; the deployed Lambda function has no access to
them at all once it's running in AWS. This is exactly the gap **AWS
Secrets Manager** fills.

## Part 2 — How the demo works

```
GET /secret-check
      |
      v
  Lambda function
      |
      | boto3 call: get_secret_value(SecretId=...)
      v
  AWS Secrets Manager
      |
      | returns the actual secret value
      v
  Lambda uses it, but only returns its LENGTH in the response
```

The point isn't the secret's content — it's proving the *mechanism*
works: the function can securely retrieve something sensitive at
runtime, without that value ever touching code, logs, or an API
response.

## Part 3 — The Lambda code, explained

```python
import boto3
secrets_client = boto3.client("secretsmanager")
SECRET_NAME = os.environ["SECRET_NAME"]

def handler(event, context):
    response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
    secret_value = response["SecretString"]
    return {
        "body": json.dumps({
            "message": "Successfully retrieved a secret...",
            "secret_length": len(secret_value)
        })
    }
```

Two details worth noticing:
- **`SECRET_NAME` comes from an environment variable**, not a
  hardcoded string — same pattern as the DynamoDB table name in an
  earlier project. Terraform sets this at deploy time.
- **The response never includes `secret_value` itself** — only its
  *length*. This is the entire point of the demo: proving access works
  without ever exposing the sensitive content. In a real application,
  the secret would typically be used internally (e.g., to authenticate
  to a database) and never returned to a caller at all.

## Part 4 — The Terraform: two resources for one secret

```hcl
resource "aws_secretsmanager_secret" "app_secret" {
  name = "${var.project_name}-${var.environment}-secret"
}

resource "aws_secretsmanager_secret_version" "app_secret_version" {
  secret_id     = aws_secretsmanager_secret.app_secret.id
  secret_string = var.secret_value
}
```

Why two separate resources for what feels like one thing? Secrets
Manager is built around **versioning** — the "secret" resource is a
stable container (with a fixed name and ARN other resources can
reference), while the "version" resource holds the actual value at a
point in time. When a secret gets rotated (e.g., a password changes),
a new version is created while the container itself — and anything
referencing it — stays the same. This project only ever has one
version, but the split exists because Secrets Manager is designed for
rotation from the ground up.

## Part 5 — The scoped inline policy

```hcl
resource "aws_iam_role_policy" "secrets_access" {
  policy = jsonencode({
    Statement = [{
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.app_secret.arn
    }]
  })
}
```

Same inline-policy pattern used for DynamoDB access in an earlier
project: a custom, one-off policy (since no AWS-managed policy could
know about this specific secret), granting exactly one action
(`GetSecretValue` — read-only, can't modify or delete the secret) on
exactly one resource (this secret's ARN, nothing else). If this
Lambda's role were ever compromised, the damage is capped at reading
this one demo value — nothing else in the AWS account.

## Part 6 — Keeping the demo value itself private

The actual text stored in the secret needed to come from somewhere,
but was deliberately never written into any file in this repository:

```hcl
variable "secret_value" {
  type      = string
  sensitive = true
}
```

`sensitive = true` is a Terraform-native feature: it tells Terraform to
never print this variable's value in `plan` or `apply` output, even in
logs a teammate (or a GitHub Actions viewer) might see.

The real value was stored as a GitHub Secret (`SM_SECRET_VALUE`) and
handed to Terraform through the pipeline:

```yaml
env:
  TF_VAR_secret_value: ${{ secrets.SM_SECRET_VALUE }}
```

This is the same `TF_VAR_` pattern used for the alert email in an
earlier project's monitoring addition — Terraform automatically maps
an environment variable named `TF_VAR_<name>` to the matching
`variable "<name>"` block, so the value flows through without ever
appearing in code or commit history.

## Part 7 — The one real bug: a secret name typo

The first deploy attempt failed immediately with:

```
Error: Credentials could not be loaded, please check your action inputs
```

**The cause was almost embarrassingly simple**: one of the three
required GitHub Secrets had been typed as `SW_AWS_ACCESS_KEY_ID`
instead of `SM_AWS_ACCESS_KEY_ID` — a single-letter typo. Since GitHub
Actions references secrets by exact name
(`${{ secrets.SM_AWS_ACCESS_KEY_ID }}`), a misspelled secret name isn't
treated as an error at save time — it simply doesn't exist from the
pipeline's point of view, so the credential step had nothing to load.

**The lesson**: unlike a typo in code (which often fails loudly and
immediately, sometimes even before running), a typo in a secret's
*name* fails silently until something tries to use it — worth
double-checking secret names carefully when adding them, since GitHub
won't warn you if one doesn't match what your workflow file expects.

## Part 8 — Why this project deployed cleanly otherwise

Aside from the typo, this project's actual infrastructure deployed
successfully on the first real attempt — no missing IAM permissions,
no formatting failures, no architecture surprises. That's a direct
result of carrying forward lessons from every earlier project: the
IAM policy was built by first listing every AWS service the Terraform
code actually touches (Lambda, API Gateway, Secrets Manager, IAM role
management), and the pipeline was built manual-trigger-only from the
very first commit, rather than needing a later fix like several
earlier projects did.

## Part 9 — Command/concept glossary (new items vs previous projects)

| Term | Plain-language meaning |
|---|---|
| Secrets Manager | AWS's managed vault for sensitive values an application reads at runtime |
| Secret version | A snapshot of a secret's value at a point in time — supports rotation without changing the secret's identity |
| `sensitive = true` | A Terraform variable setting that hides its value from plan/apply output |
| `TF_VAR_<name>` | An environment variable naming convention Terraform automatically maps to a matching variable |
| Application-level secret | A secret the running app needs (e.g. a DB password), distinct from pipeline/deployment credentials |

## Part 10 — How to explain this project in an interview

> "I built a small API that demonstrates proper secret handling with
> AWS Secrets Manager — a Lambda function retrieves a secret at
> runtime and proves it can access it, without ever returning the
> value itself in the response. The secret's content never touches my
> codebase or commit history; it flows in through a GitHub Secret and
> a Terraform sensitive variable. I also scoped the Lambda's IAM
> permission to exactly one read-only action on exactly one secret, so
> even a compromised function couldn't read anything else in the
> account. I hit one real bug — a single-letter typo in a GitHub
> Secret's name, which fails silently rather than loudly, which taught
> me to double-check secret names carefully."

That story shows a concrete, working answer to one of the most common
real interview questions in cloud/DevOps roles: how do you actually
handle secrets?

---

*This document, together with the repo's README.md, covers everything
needed to fully understand, explain, and rebuild this project.*
