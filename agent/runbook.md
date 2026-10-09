# Runbook: payments-api high error rate

1. If errors started right after a deployment, roll back to the previous version first. Command: `deploy rollback payments-api`.
2. Check the database connection pool in Datadog. If it's above 90%, restart the connection pool.
3. If the error rate is still above 5% after 10 minutes, escalate to the Payments team lead.
4. Post a status update in the #incidents Slack channel every 15 minutes.
