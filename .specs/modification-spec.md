# Specification - Update the Hosted Application Deployment Logic

- Familiarize yourself with the code-base. It's a hosted application that runs on Azure Functions and is fronted by Azure API Management.
- Infrastructure requirements are configured through `.bicep` files.
- Azure API Management requirements are configured through `.policy.xml` files.

## Problem outline

- One of the challenges today is that every client that is dynamically registered (through `register.policy.xml`) is returned the same static client ID, which is the Entra app ID. That is not correct. It needs to return a newly generated client ID in the shape of a GUID there.
- Additionally, when it issues new session tokens to the clients (see `token.policy.xml`), we need to make sure that before we do that, the dynamically registered client ID (the one I mentioned in the previous point) has been consented by the user.
    - That means that we need to implement some kind of caching mechanism, similar to what we have for session tokens and access tokens, and essentially check if a client ID has been "consented to or not."
    - We also need to implement a consent "landing page" for dynamically registered clients, where a user can land if the client has never been consented too on a given machine. That is - we need to drop some kind of cookie that says that the client has been consented to before.
    - The consent screen needs to include the client name, ID, and the redirect URI specified.
    - If the user consents, continue with authorization flow.
    - If the user does not consent, interrupt.