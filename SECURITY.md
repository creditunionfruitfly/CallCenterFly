# Security policy

CallCenterFly is pre-alpha research software and is not approved to process real calls,
credentials, account information, or payment instructions.

Please report a suspected vulnerability privately through the repository's GitHub
security-advisory interface. Do not include real member data in a report, issue, test, or
reproduction.

## Supported versions

Only the current default branch is supported during pre-alpha development.

## Operational restrictions

- Bind the optional service to loopback unless a separately reviewed environment exists.
- Use synthetic data only.
- Keep credentials in ignored environment configuration.
- Do not enable external account actions.
- Treat every response template as draft until formally approved.
- Keep MaleCNS downloads and mutable experiment state outside Git.
