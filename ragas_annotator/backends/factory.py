"""Factory class for creating the backends or mocked backends."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/backends/factory.ipynb.

# %% auto 0
__all__ = ['NotionClientFactory', 'NotionBackendFactory']

# %% ../../nbs/backends/factory.ipynb 2
import typing as t
import os

from notion_client import Client as NotionClient
from .mock_notion import MockNotionClient
from .notion_backend import NotionBackend

# %% ../../nbs/backends/factory.ipynb 3
class NotionClientFactory:
    """Factory for creating Notion client instances."""
    
    @staticmethod
    def create(
        use_mock: bool = False,
        api_key: t.Optional[str] = None,
        initialize_project: bool = False,
        root_page_id: t.Optional[str] = None
    ) -> t.Union[NotionClient, MockNotionClient]:
        """Create a Notion client.
        
        Args:
            use_mock: If True, create a mock client
            api_key: Notion API key (only used for real client)
            initialize_project: If True and using mock, initialize project structure
            root_page_id: Required if initialize_project is True
            
        Returns:
            Union[NotionClient, MockNotionClient]: A real or mock client
        """
        if use_mock:
            client = MockNotionClient()
            
            # Optionally initialize project structure
            if initialize_project and root_page_id:
                # Create root page if it doesn't exist in the mock client
                if root_page_id not in client._pages:
                    # Create root page
                    root_page = {
                        "id": root_page_id,
                        "object": "page",
                        "created_time": client._get_timestamp(),
                        "last_edited_time": client._get_timestamp(),
                        "archived": False,
                        "properties": {
                            "title": {
                                "type": "title", 
                                "title": [{"plain_text": "Root Page", "type": "text", "text": {"content": "Root Page"}}]
                            }
                        }
                    }
                    client.add_page(root_page)
                
                # Create required sub-pages
                for page_name in ["Datasets", "Experiments", "Comparisons"]:
                    # Create page ID
                    page_id = client._create_id()
                    
                    # Create page
                    page = {
                        "id": page_id,
                        "object": "page",
                        "created_time": client._get_timestamp(),
                        "last_edited_time": client._get_timestamp(),
                        "archived": False,
                        "properties": {
                            "title": {
                                "type": "title", 
                                "title": [{"plain_text": page_name, "type": "text", "text": {"content": page_name}}]
                            }
                        },
                        "parent": {"type": "page_id", "page_id": root_page_id}
                    }
                    client.add_page(page)
                    
                    # Add child block to root
                    child_block = {
                        "id": client._create_id(),
                        "object": "block",
                        "type": "child_page",
                        "created_time": client._get_timestamp(),
                        "last_edited_time": client._get_timestamp(),
                        "child_page": {
                            "title": page_name
                        }
                    }
                    
                    client.add_children(root_page_id, [child_block])
            
            return client
        else:
            # For real client, use provided API key or environment variable
            if api_key is None:
                api_key = os.getenv("NOTION_API_KEY")
                
            if api_key is None:
                raise ValueError("api_key must be provided or set as NOTION_API_KEY environment variable")
                
            return NotionClient(auth=api_key)

# %% ../../nbs/backends/factory.ipynb 7
class NotionBackendFactory:
    """Factory for creating NotionBackend instances."""
    
    @staticmethod
    def create(
        root_page_id: str,
        use_mock: bool = False,
        api_key: t.Optional[str] = None,
        initialize_project: bool = False,
        notion_client: t.Optional[t.Union[NotionClient, MockNotionClient]] = None
    ) -> NotionBackend:
        """Create a NotionBackend instance.
        
        Args:
            root_page_id: The ID of the root page
            use_mock: If True, create a backend with a mock client
            api_key: Notion API key (only used for real client)
            initialize_project: If True and using mock, initialize project structure
            notion_client: Optional pre-configured Notion client
            
        Returns:
            NotionBackend: A backend instance with either real or mock client
        """
        # Use provided client or create one
        if notion_client is None:
            notion_client = NotionClientFactory.create(
                use_mock=use_mock,
                api_key=api_key,
                initialize_project=initialize_project,
                root_page_id=root_page_id
            )
        
        # Create and return the backend
        return NotionBackend(
            root_page_id=root_page_id,
            notion_client=notion_client
        )
