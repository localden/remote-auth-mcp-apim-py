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

## Deploying the project to Azure

When you run `azd up`, resources declared in the [`infra`](https://github.com/localden/remote-auth-mcp-apim-py/tree/main/infra) directory will be provisioned in your Azure account. You can go through the existing Bicep files to see what infrastructure will be automatically deployed.

![GIF showing the deployment of Azure resources with Azure Developer CLI](./media/deploy-azd.gif)

