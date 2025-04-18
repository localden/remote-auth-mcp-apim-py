# 🤫 Authenticated Remote MCP Server

This sample shows how to deploy an Entra ID-protected MCP server on Azure.

## What it uses

- ⚡ [Azure Functions](https://learn.microsoft.com/azure/azure-functions/functions-overview)
- 🕸️ [Azure API Management](https://learn.microsoft.com/azure/api-management/api-management-key-concepts)
- 💪 [Bicep](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- 🐍 [Python](https://www.python.org/)
- 🚀 [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd?tabs=winget-windows%2Cbrew-mac%2Cscript-linux&pivots=os-windows)

>[!NOTE]
>You will need to use the [Model Context Protocol Inspector](https://modelcontextprotocol.io/docs/tools/inspector) to test the MCP server, as it's the only MCP client that currently support authorization out-of-the-box.

## Getting started

Follow these steps to get started.

1. [Install the Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd).

2. Clone the repository locally:

    ```bash
    git clone https://github.com/localden/remote-auth-mcp-apim-py
    ```

3. Navigate to the repository in your terminal:

    ```bash
    cd remote-auth-mcp-apim-py
    ```

4. Log in to Azure Developer CLI:

    ```bash
    azd auth login
    ```

5. Deploy the project to Azure:

    ```bash
    azd up
    ```

>[!IMPORTANT]
>Deploying this project will incur Azure cost. If you are deploying for testing and experimentation, make sure to delete the created resource group after testing.

## Deploying and testing the project

When you run `azd up`, resources declared in the [`infra`](https://github.com/localden/remote-auth-mcp-apim-py/tree/main/infra) directory will be provisioned in your Azure account. You can go through the existing Bicep files to see what infrastructure will be automatically deployed.

![GIF showing the deployment of Azure resources with Azure Developer CLI](./media/deploy-azd.gif)

Once the deployment completes, you will be see the **endpoint** printed in the terminal:

![Endpoint in the terminal](./media/completed-deploy.png)

For example, in the screenshot above the endpoint is `https://apim-2lzunaz2nu642.azure-api.net/mcp/sse`. Copy it.

>[!NOTE]
>Prior to the next step, make sure that you have [Node.js](https://nodejs.org/en) installed - it's required to run the [Model Context Protocol Inspector](https://modelcontextprotocol.io/docs/tools/inspector).

In your terminal, run:

```bash
npx @modelcontextprotocol/inspector@0.9.0
```

>[!NOTE]
>We're using the `0.9.0` release of the Model Context Protocol Inspector because it's the most stable version when it comes to testing protected MCP servers.

This will give an endpoint where you can see Model Context Protocol Inspector running locally. Open the URL in your browser.

Switch the **Transport Type** to **SSE** and set the **URL** to the endpoint that you got from running the deployment. Click **Connect**.

<!-- GIF -->

You will be prompted to authenticate with the credentials **in the tenant in which you deployed the infrastructure**. The Entra ID applications are dynamically registered at deployment time - one for the server, and another that will be used for [on-behalf-of flow](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow) to acquire [Microsoft Graph](https://learn.microsoft.com/graph/use-the-api) access.

Once you consent, you will be returned back to the Model Context Protocol Inspector landing page. Wait a few seconds until the connection is established - you will see a green **Connected** label on the page.

<!-- IMAGE -->

Once connected, click on **List Tools** and select `get_graph_user_data`. This will enable you to get data about the currently authenticated user from Microsoft Graph. Click **Run Tool**.

<!-- GIF -->

If all goes well, you will see your user data in the response block.

<!-- IMAGE -->