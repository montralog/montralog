# People, teams and company sign-in

Version 0.5.0-rc1 adds People & access for administrators.

## Roles and membership

Administrator: manage machine tokens, data connections, notification setup, alert rules, identity-provider settings and workspace access.
Viewer: read the organization telemetry and manage their own profile, sessions and personal dashboards.

Teams and groups are organizational membership lists. They do not confer privileges, own shared dashboards or restrict telemetry access. No nested groups, automatic directory/group sync, SCIM, custom roles or per-resource authorization are implemented. Assign roles individually. You cannot demote the final administrator. Role changes apply on the next server request.

Create local accounts using the existing operator CLI. Administrators can then assign roles, create teams/groups and manage membership. Removing a membership does not revoke workspace access. Disabling a login provider revokes sessions for accounts created by that provider.

## Configure all three providers

Open People & access and the Company sign-in section. Register a confidential web application in each provider. Use authorization code flow, RS256 ID tokens and client-secret POST authentication. Configure the exact callback displayed in Montralog; there are no wildcard callbacks. Use HTTPS for remote deployment and set MONTRALOG_COOKIE_SECURE=true in its environment before enabling remote login. Loopback HTTP is available for local evaluation.

- Microsoft Entra ID: use a single-tenant web application and issuer https://login.microsoftonline.com/TENANT-UUID/v2.0. Enter application client ID and secret value, not the secret's identifier. Restrict application assignments in your tenant. This implementation supports the commercial Microsoft cloud.
- Google Workspace: configure a web OAuth client, the callback and an exact hosted Workspace domain. Google issuer is fixed. Montralog verifies the hd claim and verified-email flag; a Gmail account or a different Workspace domain is rejected. Configure consent-screen audience and test users as appropriate.
- Okta: create an OIDC web application, restrict assignments, set client authentication to client_secret_post and use your exact organization issuer or authorization-server issuer, such as https://your-org.okta.com/oauth2/default. Supported domains: okta.com, oktapreview.com and okta-emea.com. Custom domains and other cloud regions are not included.

Test discovery checks metadata and endpoint validation. Save & enable exposes a company sign-in link. It does not prove the client registration works. Test a real sign-in and sign-out using a separate browser before relying on it. Keep a local administrator account for recovery.

New external identities become distinct viewer accounts. Identity keys include provider, exact issuer and subject. Accounts never merge by email, and external group/admin claims never grant privileges. An administrator must assign any elevated role. Existing users retain their previously assigned local role.

The flow uses PKCE S256, random nonce, ten-minute single-use server-side state and an HttpOnly browser-binding cookie. JWT verification permits RS256 only and checks issuer, audience, expiry, issue time, subject, nonce and authorized party. Provider requests use HTTPS, supported hosts, no redirects, bounded responses and timeouts. Secrets are never returned by the settings API. They are stored in the protected application database, without separate application-level encryption.

Local sign-out ends the Montralog session. It does not terminate the upstream provider session. Directory suspension is not automatically synchronized; Montralog sessions can remain valid for up to twelve hours. Disabling the provider revokes its local sessions. Automated deprovisioning, group-to-role mapping and identity lifecycle management remain outstanding production work.

## Security and audit data

Company sign-in does not ingest Microsoft 365, Google Workspace or Okta audit events. Vendor polling connectors are not implemented in this version. Existing log/OpenTelemetry ingestion can accept events transformed by your own collector. Keep ingestion credentials separate from sign-in secrets.

## References

- Microsoft identity protocols: https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols
- Google OpenID Connect: https://developers.google.com/identity/openid-connect/openid-connect
- Okta OpenID Connect: https://developer.okta.com/docs/concepts/oauth-openid/
- JOSE token validation: https://jose.authlib.org/en/guide/jwt/
