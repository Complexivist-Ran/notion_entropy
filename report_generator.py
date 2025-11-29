"""
报告生成模块
生成 Markdown 格式的熵增检测报告
"""

from datetime import datetime
from typing import List, Dict, Tuple


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        """初始化报告生成器"""
        pass
    
    def generate_report(
        self,
        database_results: Dict[str, Dict],
        overall_time_decay_entropy: float,
        overall_link_breakage_rate: float,
        threshold_days: int = 30,
        warning_threshold: float = 40.0,
        activity_metrics: Dict = None,
        property_metrics: Dict = None,
        categorization_metrics: Dict = None,
        mention_metrics: Dict = None,
        health_score: Dict = None,
        multi_threshold_decay: Dict = None
    ) -> str:
        """
        生成完整的检测报告
        
        Args:
            database_results: 每个数据库的检测结果
            overall_time_decay_entropy: 整体时间衰减熵
            overall_link_breakage_rate: 整体链接断裂率
            threshold_days: 时间衰减阈值天数
            warning_threshold: 警告阈值百分比
            activity_metrics: 活跃度指标
            property_metrics: 属性完整度指标
            categorization_metrics: 分类覆盖率指标
            mention_metrics: 连接密度指标
            health_score: 健康度评分
            
        Returns:
            Markdown 格式的报告字符串
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 默认值
        activity_metrics = activity_metrics or {}
        property_metrics = property_metrics or {}
        categorization_metrics = categorization_metrics or {}
        mention_metrics = mention_metrics or {}
        health_score = health_score or {'score': 0, 'grade': 'N/A', 'status': '未知'}
        multi_threshold_decay = multi_threshold_decay or {'thresholds': {}}
        
        # 健康度评级图标
        grade_icon = {'A': '🟢', 'B': '🟡', 'C': '🟠', 'D': '🔴'}.get(health_score.get('grade', 'N/A'), '⚪')
        
        report = f"""# Notion 数据熵增检测报告

**检测时间**: {timestamp}

---

## 🏥 知识库健康度总览

| 指标 | 数值 | 评级 |
|------|------|------|
| **综合健康度** | **{health_score.get('score', 0):.1f}分** | {grade_icon} **{health_score.get('grade', 'N/A')} - {health_score.get('status', '未知')}** |
| 页面总数 | {activity_metrics.get('total_pages', 0)} | - |
| 数据库数量 | {len(database_results)} | - |

### 健康度分项

| 维度 | 得分 | 说明 |
|------|------|------|
| 🕐 新鲜度 | {health_score.get('components', {}).get('freshness', 0):.1f} | 100 - 时间衰减熵 |
| 📈 活跃度 | {health_score.get('components', {}).get('activity', 0):.1f} | 基于30天活跃率 |
| 📝 完整度 | {health_score.get('components', {}).get('completeness', 0):.1f} | 属性填写完整程度 |
| 🏷️ 组织度 | {health_score.get('components', {}).get('organization', 0):.1f} | 分类标签覆盖率 |

---

## 📊 详细指标

### 1. 时间衰减熵 (Time Decay Entropy)

不同时间窗口下未更新页面的比例：

| 未更新时间 | 页面数量 | 占比 | 状态 |
|-----------|---------|------|------|"""
        
        # 添加多时间窗口的衰减数据
        thresholds_data = multi_threshold_decay.get('thresholds', {})
        threshold_order = [30, 90, 150, 300]
        
        for t in threshold_order:
            if t in thresholds_data:
                data = thresholds_data[t]
                count = data.get('count', 0)
                rate = data.get('rate', 0)
                if rate > 80:
                    status = "🔴 严重"
                elif rate > 50:
                    status = "🟠 警告"
                elif rate > 30:
                    status = "🟡 注意"
                else:
                    status = "🟢 正常"
                report += f"\n| > {t} 天 | {count} | {rate:.1f}% | {status} |"
        
        report += f"""

*说明：数值表示超过该天数未更新的页面比例*

"""
        
        # 添加警告信息
        if overall_time_decay_entropy > warning_threshold:
            report += f"⚠️ **警告**: 30天时间衰减熵 ({overall_time_decay_entropy:.1f}%) 超过警告阈值 ({warning_threshold}%)！建议及时清理过期内容。\n\n"
        else:
            report += f"✅ 30天时间衰减熵 ({overall_time_decay_entropy:.1f}%) 在正常范围内。\n\n"
        
        if overall_link_breakage_rate < 0:
            report += f"""### 链接断裂率 (Link Breakage Rate)
- **当前值**: 无法计算
- **说明**: 数据库未使用 relation（关联）属性

ℹ️ **提示**: 链接断裂率指标需要数据库配置关联字段才能计算。如果您在 Notion 页面内容中使用 @ 提及其他页面，这种链接方式暂不纳入统计。

"""
        else:
            report += f"""### 链接断裂率 (Link Breakage Rate)
- **当前值**: {overall_link_breakage_rate:.2f}%
- **说明**: 孤立页面（无入链）的比例

"""
            if overall_link_breakage_rate > 30:
                report += f"⚠️ **警告**: 链接断裂率较高，知识网络连接度较低。\n\n"
            else:
                report += f"✅ 链接断裂率在可接受范围内。\n\n"
        
        # 添加活跃度指标
        report += f"""### 2. 活跃度指标 (Activity Metrics)

| 时间范围 | 活跃页面数 | 活跃率 |
|---------|----------|-------|
| 近7天 | {activity_metrics.get('active_7d', 0)} | {activity_metrics.get('activity_rate_7d', 0):.2f}% |
| 近30天 | {activity_metrics.get('active_30d', 0)} | {activity_metrics.get('activity_rate_30d', 0):.2f}% |
| 近90天 | {activity_metrics.get('active_90d', 0)} | {activity_metrics.get('activity_rate_90d', 0):.2f}% |

"""
        
        # 添加属性完整度
        report += f"""### 3. 属性完整度 (Property Completeness)
- **平均完整度**: {property_metrics.get('avg_completeness', 0):.2f}%
- **完整页面（≥80%）**: {property_metrics.get('fully_complete', 0)} 个
- **部分填写（30-80%）**: {property_metrics.get('partially_complete', 0)} 个
- **基本为空（<30%）**: {property_metrics.get('mostly_empty', 0)} 个

"""
        
        # 添加分类覆盖率
        report += f"""### 4. 分类覆盖率 (Categorization Coverage)
- **已分类页面**: {categorization_metrics.get('categorized_pages', 0)} 个
- **未分类页面**: {categorization_metrics.get('uncategorized_pages', 0)} 个
- **覆盖率**: {categorization_metrics.get('coverage_rate', 0):.2f}%

"""
        
        # 添加连接密度
        report += f"""### 5. 连接密度 (Link Density) - 抽样检测
- **抽样页面数**: {mention_metrics.get('sampled_pages', 0)} 个
- **含链接页面**: {mention_metrics.get('pages_with_mentions', 0)} 个
- **总链接数**: {mention_metrics.get('total_mentions', 0)} 个
- **连接密度**: {mention_metrics.get('mention_density', 0):.2f}%
- **平均链接/页**: {mention_metrics.get('avg_mentions_per_page', 0):.2f}

*注：通过抽样检测页面内容中的 @mention 链接*

"""
        
        report += "---\n\n"
        
        # 添加各数据库的详细结果
        report += "## 📁 数据库详细分析\n\n"
        
        for db_id, result in database_results.items():
            db_info = result.get('database_info', {})
            db_title = db_info.get('title', 'Unknown')
            pages_count = result.get('pages_count', 0)
            link_breakage_rate = result.get('link_breakage_rate', 0)
            isolated_pages = result.get('isolated_pages', [])
            db_decay = result.get('multi_threshold_decay', {})
            
            link_rate_str = "无法计算" if link_breakage_rate < 0 else f"{link_breakage_rate:.2f}%"
            
            # 获取各阈值衰减率
            decay_thresholds = db_decay.get('thresholds', {})
            decay_30 = decay_thresholds.get(30, {}).get('rate', 0)
            decay_90 = decay_thresholds.get(90, {}).get('rate', 0)
            decay_150 = decay_thresholds.get(150, {}).get('rate', 0)
            decay_300 = decay_thresholds.get(300, {}).get('rate', 0)
            
            report += f"""### {db_title}

- **数据库ID**: `{db_id}`
- **页面总数**: {pages_count}
- **链接断裂率**: {link_rate_str}

#### 时间衰减分布

| >30天 | >90天 | >150天 | >300天 |
|-------|-------|--------|--------|
| {decay_30:.1f}% | {decay_90:.1f}% | {decay_150:.1f}% | {decay_300:.1f}% |

"""
            
            # 超过300天的页面列表（最需要关注）
            outdated_300 = decay_thresholds.get(300, {}).get('pages', [])
            if outdated_300:
                report += f"#### ⏰ 长期未更新页面（超过 300 天）\n\n"
                report += "| 页面标题 | 最后编辑时间 | 未更新天数 |\n"
                report += "|---------|------------|----------|\n"
                for page in outdated_300[:15]:  # 最多显示15个
                    title = page.get('title', 'Untitled')
                    last_edited = page.get('last_edited', 'N/A')
                    days_old = page.get('days_old', 0)
                    report += f"| {title} | {last_edited} | {days_old} 天 |\n"
                
                if len(outdated_300) > 15:
                    report += f"\n*（仅显示前15个，共 {len(outdated_300)} 个）*\n"
                report += "\n"
            
            # 孤立页面列表
            if isolated_pages:
                report += f"#### 🔗 孤立页面列表（无入链）\n\n"
                report += "| 页面标题 |\n"
                report += "|---------|\n"
                for page in isolated_pages[:20]:  # 最多显示20个
                    title = page.get('title', 'Untitled')
                    report += f"| {title} |\n"
                
                if len(isolated_pages) > 20:
                    report += f"\n*（仅显示前20个，共 {len(isolated_pages)} 个孤立页面）*\n"
                report += "\n"
            
            report += "---\n\n"
        
        # 添加建议
        report += "## 💡 建议\n\n"
        
        if overall_time_decay_entropy > warning_threshold:
            report += f"- 建议清理超过 {threshold_days} 天未更新的过期内容\n"
            report += "- 考虑归档或删除不再需要的信息\n"
        
        if overall_link_breakage_rate > 30:
            report += "- 建议为孤立页面添加链接关系，增强知识网络连接\n"
            report += "- 检查是否有重要页面被遗漏链接\n"
        elif overall_link_breakage_rate < 0:
            report += "- 数据库未使用 relation（关联）属性，无法计算链接断裂率\n"
            report += "- 如需统计页面间的链接关系，可在数据库中添加 relation 类型的属性\n"
        
        if overall_time_decay_entropy <= warning_threshold and overall_link_breakage_rate <= 30:
            report += "- ✅ 当前数据健康度良好，继续保持！\n"
        
        report += "\n---\n\n"
        report += f"*报告生成时间: {timestamp}*\n"
        
        return report
    
    def save_report(self, report_content: str, output_dir: str = ".") -> str:
        """
        保存报告到文件
        
        Args:
            report_content: 报告内容
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"entropy_report_{timestamp}.md"
        filepath = f"{output_dir}/{filename}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return filepath


