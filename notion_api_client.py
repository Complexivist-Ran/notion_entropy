"""
Notion API 客户端封装模块
提供连接、认证和数据获取的基础功能
"""

import os
from typing import List, Dict, Optional
from notion_client import Client
from dotenv import load_dotenv
import httpx

# 加载环境变量
load_dotenv()


class NotionClient:
    """Notion API 客户端封装类"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化 Notion 客户端
        
        Args:
            token: Notion Integration Token，如果为 None 则从环境变量读取
        """
        self.token = token or os.getenv('NOTION_TOKEN')
        if not self.token:
            raise ValueError("NOTion Token 未设置，请在 .env 文件中设置 NOTION_TOKEN 或传入 token 参数")
        
        # 使用新版本 API (2025-09-03) 以支持 data_source
        self.client = Client(auth=self.token, notion_version="2025-09-03")
    
    def get_all_databases(self) -> List[Dict]:
        """
        获取所有可访问的数据库（通过 data_source）
        
        注意：新版本 API 使用 data_source 而不是 database
        
        Returns:
            数据库列表，每个数据库包含 id, title 等信息
        """
        data_sources = []
        has_more = True
        start_cursor = None
        
        while has_more:
            if start_cursor:
                response = self.client.search(
                    filter={"property": "object", "value": "data_source"},
                    start_cursor=start_cursor
                )
            else:
                response = self.client.search(
                    filter={"property": "object", "value": "data_source"}
                )
            
            data_sources.extend(response.get('results', []))
            has_more = response.get('has_more', False)
            start_cursor = response.get('next_cursor')
        
        # 将 data_source 转换为数据库格式（保持兼容性）
        # 注意：新版本 API 中，data_source 对象可能包含 database_id 信息
        databases = []
        seen_combinations = set()  # (database_id, data_source_id) 组合
        
        for data_source in data_sources:
            data_source_id = data_source.get('id')
            
            # 尝试从 data_source 获取 database_id
            # 根据新 API，data_source 对象应该包含 parent 信息
            parent = data_source.get('parent', {})
            database_id = None
            
            if parent.get('type') == 'database_id':
                database_id = parent.get('database_id')
            elif parent.get('type') == 'database':
                database_id = parent.get('database_id') or parent.get('id')
            
            # 如果仍然没有 database_id，尝试通过查询获取
            if not database_id:
                # 对于这种情况，我们暂时使用 data_source_id
                # 后续在查询时会通过 GET database 来获取真正的 database_id
                database_id = data_source_id
            
            # 避免重复（一个数据库可能有多个 data_source）
            key = (database_id, data_source_id)
            if key not in seen_combinations:
                seen_combinations.add(key)
                # 构建数据库对象，包含 data_source_id 信息
                db_obj = {
                    'id': database_id,
                    'data_source_id': data_source_id,
                    'title': data_source.get('title', []),
                    'properties': data_source.get('properties', {}),
                    'object': 'database'
                }
                databases.append(db_obj)
        
        return databases
    
    def get_database_pages(self, database_id: str, data_source_id: Optional[str] = None) -> List[Dict]:
        """
        获取指定数据库的所有页面
        
        Args:
            database_id: 数据库 ID
            data_source_id: 数据源 ID（可选，如果不提供则从数据库获取）
            
        Returns:
            页面列表
        """
        # 如果没有提供 data_source_id，先获取数据库信息以获取 data_source_id
        if not data_source_id:
            try:
                # 使用 request 方法获取数据库信息
                db_info = self.client.request(
                    method="get",
                    path=f"databases/{database_id}"
                )
                data_sources = db_info.get('data_sources', [])
                if data_sources:
                    # 使用第一个 data_source
                    data_source_id = data_sources[0].get('id')
                else:
                    # 如果没有 data_source，尝试使用旧版 API
                    data_source_id = None
            except Exception as e:
                # 如果获取失败，尝试使用旧版 API
                print(f"警告：无法获取数据库 {database_id} 的 data_source 信息: {e}")
                data_source_id = None
        
        pages = []
        has_more = True
        start_cursor = None
        
        # 优先使用新版本 API (data_source)
        if data_source_id:
            try:
                # 使用直接 HTTP 请求调用新版本 API
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Notion-Version": "2025-09-03",
                    "Content-Type": "application/json"
                }
                
                while has_more:
                    body = {}
                    if start_cursor:
                        body['start_cursor'] = start_cursor
                    
                    url = f"https://api.notion.com/v1/data-sources/{data_source_id}/query"
                    with httpx.Client() as http_client:
                        resp = http_client.post(url, headers=headers, json=body if body else {})
                        resp.raise_for_status()
                        response = resp.json()
                    
                    pages.extend(response.get('results', []))
                    has_more = response.get('has_more', False)
                    start_cursor = response.get('next_cursor')
            except Exception as e:
                # 如果新 API 失败，回退到旧版 API
                print(f"警告：使用 data_source API 失败，回退到 database API: {e}")
                data_source_id = None
        
        # 回退到旧版 API（兼容性）- 使用直接 HTTP 请求
        if not data_source_id:
            try:
                headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Notion-Version": "2022-06-28",  # 使用旧版 API 版本
                    "Content-Type": "application/json"
                }
                
                while has_more:
                    body = {}
                    if start_cursor:
                        body['start_cursor'] = start_cursor
                    
                    url = f"https://api.notion.com/v1/databases/{database_id}/query"
                    with httpx.Client() as http_client:
                        resp = http_client.post(url, headers=headers, json=body if body else {})
                        resp.raise_for_status()
                        response = resp.json()
                    
                    pages.extend(response.get('results', []))
                    has_more = response.get('has_more', False)
                    start_cursor = response.get('next_cursor')
            except Exception as e:
                raise Exception(f"无法查询数据库 {database_id}: {e}")
        
        return pages
    
    def get_all_pages(self) -> List[Dict]:
        """
        获取所有可访问的页面（包括数据库中的页面和独立页面）
        
        Returns:
            页面列表
        """
        pages = []
        has_more = True
        start_cursor = None
        
        while has_more:
            if start_cursor:
                response = self.client.search(
                    filter={"property": "object", "value": "page"},
                    start_cursor=start_cursor
                )
            else:
                response = self.client.search(
                    filter={"property": "object", "value": "page"}
                )
            
            pages.extend(response.get('results', []))
            has_more = response.get('has_more', False)
            start_cursor = response.get('next_cursor')
        
        return pages
    
    def get_page(self, page_id: str) -> Dict:
        """
        获取指定页面的详细信息
        
        Args:
            page_id: 页面 ID
            
        Returns:
            页面详细信息
        """
        return self.client.pages.retrieve(page_id=page_id)

