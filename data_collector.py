"""
数据采集模块
负责从 Notion 收集数据库和页面数据
"""

import os
from typing import List, Dict, Optional
from notion_api_client import NotionClient


class DataCollector:
    """数据采集器"""
    
    def __init__(self, notion_client: NotionClient):
        """
        初始化数据采集器
        
        Args:
            notion_client: Notion API 客户端实例
        """
        self.notion_client = notion_client
    
    def collect_database_data(
        self, 
        database_ids: Optional[List[str]] = None
    ) -> Dict[str, List[Dict]]:
        """
        收集指定数据库的数据
        
        Args:
            database_ids: 数据库ID列表，如果为None则收集所有可访问的数据库
            
        Returns:
            字典，key为数据库ID，value为该数据库的页面列表
        """
        database_pages = {}
        
        if database_ids:
            # 收集指定数据库
            for db_id in database_ids:
                try:
                    pages = self.notion_client.get_database_pages(db_id)
                    database_pages[db_id] = pages
                except Exception as e:
                    print(f"警告：无法访问数据库 {db_id}: {e}")
        else:
            # 收集所有数据库
            databases = self.notion_client.get_all_databases()
            for db in databases:
                db_id = db.get('id')
                data_source_id = db.get('data_source_id')
                try:
                    pages = self.notion_client.get_database_pages(db_id, data_source_id)
                    database_pages[db_id] = pages
                except Exception as e:
                    print(f"警告：无法访问数据库 {db_id}: {e}")
        
        return database_pages
    
    def collect_all_pages(self) -> List[Dict]:
        """
        收集所有可访问的页面
        
        Returns:
            页面列表
        """
        return self.notion_client.get_all_pages()
    
    def get_database_info(self, database_id: str) -> Dict:
        """
        获取数据库信息
        
        Args:
            database_id: 数据库ID
            
        Returns:
            数据库信息字典
        """
        try:
            # 使用 request 方法获取数据库信息
            database = self.notion_client.client.request(
                method="get",
                path=f"databases/{database_id}"
            )
            return {
                'id': database.get('id'),
                'title': self._get_database_title(database),
                'created_time': database.get('created_time'),
                'last_edited_time': database.get('last_edited_time')
            }
        except Exception as e:
            return {
                'id': database_id,
                'title': f"Unknown ({database_id[:8]}...)",
                'error': str(e)
            }
    
    def _get_database_title(self, database: Dict) -> str:
        """
        获取数据库标题
        
        Args:
            database: 数据库对象
            
        Returns:
            数据库标题
        """
        title_array = database.get('title', [])
        if title_array:
            return ''.join([item.get('plain_text', '') for item in title_array])
        return "Untitled Database"

