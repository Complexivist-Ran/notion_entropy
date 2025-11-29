"""
熵指标计算模块
实现多种数据熵增指标的计算逻辑
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple, Optional
import random
import httpx
from notion_api_client import NotionClient


class EntropyCalculator:
    """熵指标计算器"""
    
    def __init__(self, notion_client: NotionClient):
        """
        初始化计算器
        
        Args:
            notion_client: Notion API 客户端实例
        """
        self.notion_client = notion_client
    
    def calculate_time_decay_entropy(
        self, 
        pages: List[Dict], 
        threshold_days: int = 30
    ) -> Tuple[float, List[Dict]]:
        """
        计算时间衰减熵（单一阈值）
        
        Args:
            pages: 页面列表
            threshold_days: 阈值天数（超过此天数未更新视为过期）
            
        Returns:
            (熵值百分比, 过期页面列表)
        """
        if not pages:
            return 0.0, []
        
        now = datetime.now(timezone.utc)
        outdated_pages = []
        
        for page in pages:
            last_edited = page.get('last_edited_time')
            if not last_edited:
                continue
            
            # 解析时间字符串
            if isinstance(last_edited, str):
                last_edited_dt = datetime.fromisoformat(last_edited.replace('Z', '+00:00'))
            else:
                last_edited_dt = last_edited
            
            # 计算天数差
            days_diff = (now - last_edited_dt).days
            
            if days_diff > threshold_days:
                outdated_pages.append({
                    'page_id': page.get('id'),
                    'title': self._get_page_title(page),
                    'last_edited': last_edited_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'days_old': days_diff
                })
        
        entropy = (len(outdated_pages) / len(pages)) * 100 if pages else 0.0
        
        return entropy, outdated_pages
    
    def calculate_multi_threshold_decay(
        self, 
        pages: List[Dict],
        thresholds: List[int] = None
    ) -> Dict:
        """
        计算多时间窗口的衰减指标
        
        Args:
            pages: 页面列表
            thresholds: 阈值天数列表，默认 [30, 90, 150, 300]
            
        Returns:
            包含各阈值衰减率的字典
        """
        if thresholds is None:
            thresholds = [30, 90, 150, 300]
        
        if not pages:
            return {
                'total_pages': 0,
                'thresholds': {t: {'count': 0, 'rate': 0.0, 'pages': []} for t in thresholds}
            }
        
        now = datetime.now(timezone.utc)
        total = len(pages)
        
        # 为每个页面计算未更新天数
        page_ages = []
        for page in pages:
            last_edited = page.get('last_edited_time')
            if not last_edited:
                continue
            
            if isinstance(last_edited, str):
                last_edited_dt = datetime.fromisoformat(last_edited.replace('Z', '+00:00'))
            else:
                last_edited_dt = last_edited
            
            days_diff = (now - last_edited_dt).days
            page_ages.append({
                'page': page,
                'days_old': days_diff,
                'last_edited': last_edited_dt.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # 按天数排序（最旧的在前）
        page_ages.sort(key=lambda x: x['days_old'], reverse=True)
        
        # 计算各阈值的衰减率
        result = {
            'total_pages': total,
            'thresholds': {}
        }
        
        for threshold in thresholds:
            outdated = [p for p in page_ages if p['days_old'] > threshold]
            outdated_pages = [{
                'page_id': p['page'].get('id'),
                'title': self._get_page_title(p['page']),
                'last_edited': p['last_edited'],
                'days_old': p['days_old']
            } for p in outdated[:50]]  # 只保留前50个
            
            result['thresholds'][threshold] = {
                'count': len(outdated),
                'rate': (len(outdated) / total) * 100 if total > 0 else 0.0,
                'pages': outdated_pages
            }
        
        return result
    
    def calculate_link_breakage_rate(
        self, 
        pages: List[Dict]
    ) -> Tuple[float, List[Dict], Dict]:
        """
        计算链接断裂率（孤立页面比例）
        
        注意：Notion API 无法直接检测失效链接（指向已删除页面的链接），
        只能检测孤立页面（无入链的页面）
        
        Args:
            pages: 页面列表
            
        Returns:
            (断裂率百分比, 孤立页面列表, 统计信息)
        """
        if not pages:
            return 0.0, [], {'has_relations': False, 'total_relations': 0}
        
        # 构建页面ID到页面的映射
        page_map = {page.get('id'): page for page in pages}
        
        # 统计每个页面的入链数
        incoming_links = {}
        total_relations = 0
        has_relation_property = False
        
        for page in pages:
            page_id = page.get('id')
            incoming_links[page_id] = 0
            
            # 检查页面中的关系属性（relations）
            properties = page.get('properties', {})
            for prop_name, prop_value in properties.items():
                prop_type = prop_value.get('type')
                
                # 检查关系属性
                if prop_type == 'relation':
                    has_relation_property = True
                    relations = prop_value.get('relation', [])
                    total_relations += len(relations)
                    for relation in relations:
                        target_id = relation.get('id')
                        if target_id in incoming_links:
                            incoming_links[target_id] += 1
        
        # 统计信息
        stats = {
            'has_relations': has_relation_property,
            'total_relations': total_relations
        }
        
        # 如果数据库没有 relation 属性，返回特殊值
        if not has_relation_property:
            # 返回 -1 表示无法计算（数据库没有使用关联功能）
            return -1.0, [], stats
        
        # 找出孤立页面（无入链）
        isolated_pages = []
        for page_id, link_count in incoming_links.items():
            if link_count == 0:
                page = page_map.get(page_id)
                if page:
                    isolated_pages.append({
                        'page_id': page_id,
                        'title': self._get_page_title(page),
                        'incoming_links': 0
                    })
        
        breakage_rate = (len(isolated_pages) / len(pages)) * 100 if pages else 0.0
        
        return breakage_rate, isolated_pages, stats
    
    def _get_page_title(self, page: Dict) -> str:
        """
        获取页面标题
        
        Args:
            page: 页面对象
            
        Returns:
            页面标题，如果无法获取则返回 "Untitled"
        """
        properties = page.get('properties', {})
        
        # 尝试从 properties 中获取标题
        for prop_name, prop_value in properties.items():
            prop_type = prop_value.get('type')
            if prop_type == 'title':
                title_array = prop_value.get('title', [])
                if title_array:
                    return ''.join([item.get('plain_text', '') for item in title_array])
        
        # 如果没有标题属性，尝试从其他属性获取
        # 或者返回页面ID的前8位作为标识
        page_id = page.get('id', '')
        return f"Untitled ({page_id[:8]}...)" if page_id else "Untitled"
    
    def calculate_activity_metrics(
        self, 
        pages: List[Dict]
    ) -> Dict:
        """
        计算活跃度指标
        
        Args:
            pages: 页面列表
            
        Returns:
            活跃度指标字典
        """
        if not pages:
            return {
                'total_pages': 0,
                'active_7d': 0,
                'active_30d': 0,
                'active_90d': 0,
                'activity_rate_7d': 0.0,
                'activity_rate_30d': 0.0,
                'activity_rate_90d': 0.0
            }
        
        now = datetime.now(timezone.utc)
        active_7d = 0
        active_30d = 0
        active_90d = 0
        
        for page in pages:
            last_edited = page.get('last_edited_time')
            if not last_edited:
                continue
            
            if isinstance(last_edited, str):
                last_edited_dt = datetime.fromisoformat(last_edited.replace('Z', '+00:00'))
            else:
                last_edited_dt = last_edited
            
            days_diff = (now - last_edited_dt).days
            
            if days_diff <= 7:
                active_7d += 1
            if days_diff <= 30:
                active_30d += 1
            if days_diff <= 90:
                active_90d += 1
        
        total = len(pages)
        return {
            'total_pages': total,
            'active_7d': active_7d,
            'active_30d': active_30d,
            'active_90d': active_90d,
            'activity_rate_7d': (active_7d / total) * 100 if total > 0 else 0.0,
            'activity_rate_30d': (active_30d / total) * 100 if total > 0 else 0.0,
            'activity_rate_90d': (active_90d / total) * 100 if total > 0 else 0.0
        }
    
    def calculate_property_completeness(
        self, 
        pages: List[Dict]
    ) -> Dict:
        """
        计算属性完整度
        
        Args:
            pages: 页面列表
            
        Returns:
            属性完整度指标字典
        """
        if not pages:
            return {
                'avg_completeness': 0.0,
                'fully_complete': 0,
                'partially_complete': 0,
                'mostly_empty': 0
            }
        
        completeness_scores = []
        fully_complete = 0
        partially_complete = 0
        mostly_empty = 0
        
        for page in pages:
            properties = page.get('properties', {})
            if not properties:
                completeness_scores.append(0)
                mostly_empty += 1
                continue
            
            total_props = 0
            filled_props = 0
            
            for prop_name, prop_value in properties.items():
                prop_type = prop_value.get('type')
                total_props += 1
                
                # 检查属性是否有值
                if self._is_property_filled(prop_value, prop_type):
                    filled_props += 1
            
            if total_props > 0:
                score = (filled_props / total_props) * 100
                completeness_scores.append(score)
                
                if score >= 80:
                    fully_complete += 1
                elif score >= 30:
                    partially_complete += 1
                else:
                    mostly_empty += 1
            else:
                completeness_scores.append(0)
                mostly_empty += 1
        
        avg = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
        
        return {
            'avg_completeness': avg,
            'fully_complete': fully_complete,
            'partially_complete': partially_complete,
            'mostly_empty': mostly_empty
        }
    
    def _is_property_filled(self, prop_value: Dict, prop_type: str) -> bool:
        """判断属性是否有值"""
        if prop_type == 'title':
            return bool(prop_value.get('title', []))
        elif prop_type == 'rich_text':
            return bool(prop_value.get('rich_text', []))
        elif prop_type == 'number':
            return prop_value.get('number') is not None
        elif prop_type == 'select':
            return prop_value.get('select') is not None
        elif prop_type == 'multi_select':
            return bool(prop_value.get('multi_select', []))
        elif prop_type == 'date':
            return prop_value.get('date') is not None
        elif prop_type == 'checkbox':
            return True  # checkbox 总是有值
        elif prop_type == 'url':
            return bool(prop_value.get('url'))
        elif prop_type == 'email':
            return bool(prop_value.get('email'))
        elif prop_type == 'phone_number':
            return bool(prop_value.get('phone_number'))
        elif prop_type == 'relation':
            return bool(prop_value.get('relation', []))
        elif prop_type == 'files':
            return bool(prop_value.get('files', []))
        elif prop_type in ['created_time', 'last_edited_time', 'created_by', 'last_edited_by']:
            return True  # 系统属性总是有值
        elif prop_type == 'formula':
            return True  # 公式总是有值
        elif prop_type == 'rollup':
            return True  # 汇总总是有值
        else:
            return False
    
    def calculate_categorization_coverage(
        self, 
        pages: List[Dict]
    ) -> Dict:
        """
        计算分类覆盖率（有标签/分类的页面占比）
        
        Args:
            pages: 页面列表
            
        Returns:
            分类覆盖率指标字典
        """
        if not pages:
            return {
                'categorized_pages': 0,
                'uncategorized_pages': 0,
                'coverage_rate': 0.0
            }
        
        categorized = 0
        uncategorized_list = []
        
        for page in pages:
            properties = page.get('properties', {})
            has_category = False
            
            for prop_name, prop_value in properties.items():
                prop_type = prop_value.get('type')
                
                # 检查分类相关属性
                if prop_type == 'select' and prop_value.get('select'):
                    has_category = True
                    break
                elif prop_type == 'multi_select' and prop_value.get('multi_select'):
                    has_category = True
                    break
                elif prop_type == 'relation' and prop_value.get('relation'):
                    has_category = True
                    break
            
            if has_category:
                categorized += 1
            else:
                uncategorized_list.append({
                    'page_id': page.get('id'),
                    'title': self._get_page_title(page)
                })
        
        total = len(pages)
        return {
            'categorized_pages': categorized,
            'uncategorized_pages': total - categorized,
            'coverage_rate': (categorized / total) * 100 if total > 0 else 0.0,
            'uncategorized_list': uncategorized_list[:20]  # 只返回前20个
        }
    
    def calculate_mention_density(
        self, 
        pages: List[Dict],
        sample_rate: float = 0.1
    ) -> Dict:
        """
        计算 mention 密度（通过抽样检测页面内容中的链接）
        
        Args:
            pages: 页面列表
            sample_rate: 抽样比例（0-1），默认10%
            
        Returns:
            mention 密度指标字典
        """
        if not pages:
            return {
                'sampled_pages': 0,
                'pages_with_mentions': 0,
                'total_mentions': 0,
                'mention_density': 0.0,
                'avg_mentions_per_page': 0.0
            }
        
        # 抽样
        sample_size = max(1, int(len(pages) * sample_rate))
        sample_size = min(sample_size, 50)  # 最多检查50个页面（控制 API 调用）
        sampled_pages = random.sample(pages, min(sample_size, len(pages)))
        
        pages_with_mentions = 0
        total_mentions = 0
        
        headers = {
            "Authorization": f"Bearer {self.notion_client.token}",
            "Notion-Version": "2022-06-28",
        }
        
        for page in sampled_pages:
            page_id = page.get('id')
            try:
                url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                with httpx.Client(timeout=10.0) as http_client:
                    resp = http_client.get(url, headers=headers)
                    if resp.status_code == 200:
                        blocks = resp.json().get('results', [])
                        mention_count = self._count_mentions_in_blocks(blocks)
                        if mention_count > 0:
                            pages_with_mentions += 1
                            total_mentions += mention_count
            except Exception:
                # 忽略错误，继续处理其他页面
                pass
        
        sampled = len(sampled_pages)
        return {
            'sampled_pages': sampled,
            'pages_with_mentions': pages_with_mentions,
            'total_mentions': total_mentions,
            'mention_density': (pages_with_mentions / sampled) * 100 if sampled > 0 else 0.0,
            'avg_mentions_per_page': total_mentions / sampled if sampled > 0 else 0.0
        }
    
    def _count_mentions_in_blocks(self, blocks: List[Dict]) -> int:
        """统计 blocks 中的 mention 数量"""
        count = 0
        for block in blocks:
            block_type = block.get('type')
            if block_type and block_type in block:
                content = block.get(block_type, {})
                rich_text = content.get('rich_text', [])
                for text_item in rich_text:
                    if text_item.get('type') == 'mention':
                        mention = text_item.get('mention', {})
                        # 只统计页面 mention
                        if mention.get('type') in ['page', 'database']:
                            count += 1
        return count
    
    def calculate_health_score(
        self,
        time_decay_entropy: float,
        activity_rate_30d: float,
        property_completeness: float,
        categorization_coverage: float
    ) -> Dict:
        """
        计算知识库综合健康度评分
        
        Args:
            time_decay_entropy: 时间衰减熵（0-100%）
            activity_rate_30d: 30天活跃率（0-100%）
            property_completeness: 属性完整度（0-100%）
            categorization_coverage: 分类覆盖率（0-100%）
            
        Returns:
            健康度评分字典
        """
        # 权重配置
        weights = {
            'freshness': 0.35,      # 新鲜度（时间衰减熵的反向）
            'activity': 0.30,       # 活跃度
            'completeness': 0.20,   # 完整度
            'organization': 0.15    # 组织度
        }
        
        # 计算各项得分（归一化到 0-100）
        freshness_score = max(0, 100 - time_decay_entropy)
        activity_score = min(100, activity_rate_30d * 2)  # 50% 活跃率 = 100分
        completeness_score = property_completeness
        organization_score = categorization_coverage
        
        # 加权计算
        health_score = (
            freshness_score * weights['freshness'] +
            activity_score * weights['activity'] +
            completeness_score * weights['completeness'] +
            organization_score * weights['organization']
        )
        
        # 评级
        if health_score >= 80:
            grade = 'A'
            status = '健康'
        elif health_score >= 60:
            grade = 'B'
            status = '良好'
        elif health_score >= 40:
            grade = 'C'
            status = '一般'
        else:
            grade = 'D'
            status = '需要整理'
        
        return {
            'score': health_score,
            'grade': grade,
            'status': status,
            'components': {
                'freshness': freshness_score,
                'activity': activity_score,
                'completeness': completeness_score,
                'organization': organization_score
            }
        }

