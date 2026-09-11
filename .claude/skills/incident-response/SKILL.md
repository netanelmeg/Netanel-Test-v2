---
name: incident-response
description: On-call incident triage patterns — Azure Status checks, incident correlation, and systematic response procedures.
confidence: medium
domain: incident-response, reliability, infrastructure
---

# Incident Response

## Pattern: Azure Status Check First

During any incident or ICM, **FIRST check Azure Status** to determine if it's a broader Azure infrastructure issue.

## Why

Quickly distinguish "our problem" from "Azure-wide outage." During an incident, the Azure Status page reveals if other services are affected, proving that the incident is not isolated to your system. This reduces blame during incident resolution and redirects focus appropriately.

**Real-world example:** During a production incident, multiple Azure services were degraded simultaneously. Checking Azure Status showed others were also affected, proving it wasn't a fault in the team's deployment or configuration.

## How

1. **Navigate to Azure Status:** https://azure.status.microsoft/en-us/status
2. **Check for Active Incidents:** Look for any ongoing incidents or maintenance in relevant services:
   - Azure Kubernetes Service (AKS)
   - Key Vault
   - Azure Networking (ExpressRoute, Load Balancer, etc.)
   - Azure Storage
   - Azure Container Registry
3. **Verify Timeline:** Check if the incident started around the same time as your ICM
4. **Document Findings:** Note the service(s) affected in your incident post-mortem or incident notes

## Triage Checklist

```markdown
- [ ] Check Azure Status page for active incidents
- [ ] Correlate incident timeline with Azure status timeline
- [ ] Identify affected Azure services relevant to your workload
- [ ] Check if other teams are reporting similar issues
- [ ] Document findings in incident notes
- [ ] If Azure-wide: link Azure incident ID in your ICM
- [ ] If isolated: proceed with standard debugging
```

## Related Skills
- Incident triage procedures
- Post-incident reporting
- Root cause analysis
