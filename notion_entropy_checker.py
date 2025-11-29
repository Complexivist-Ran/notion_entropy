"""
Notion 数据熵增检测主脚本
定期检测 Notion 工作区中的数据熵增情况，包括时间衰减熵和链接断裂率
"""

import os
import sys
from typing import List, Optional
from dotenv import load_dotenv

# 设置输出编码为 UTF-8（Windows 兼容）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 加载 .env 文件
load_dotenv()

from notion_api_client import NotionClient
from data_collector import DataCollector
from entropy_calculator import EntropyCalculator
from report_generator import ReportGenerator


def format_notion_id(id_str: str) -> str:
    """
    格式化 Notion ID（添加连字符）
    Notion ID 格式：8-4-4-4-12 (32位十六进制)
    
    Args:
        id_str: 原始 ID 字符串（可能没有连字符）
        
    Returns:
        格式化后的 ID（带连字符）
    """
    # 移除所有连字符和空格
    clean_id = id_str.replace('-', '').replace(' ', '')
    
    # 如果不是32位，直接返回（可能是无效ID）
    if len(clean_id) != 32:
        return id_str
    
    # 格式化为 8-4-4-4-12
    return f"{clean_id[0:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:32]}"


def parse_database_ids(env_value: Optional[str]) -> Optional[List[str]]:
    """
    解析环境变量中的数据库ID列表
    
    Args:
        env_value: 环境变量值，多个ID用逗号分隔
        
    Returns:
        数据库ID列表，如果为None或空则返回None
    """
    if not env_value or not env_value.strip():
        return None
    
    ids = [id.strip() for id in env_value.split(',') if id.strip()]
    # 格式化所有 ID（添加连字符）
    formatted_ids = [format_notion_id(id) for id in ids]
    return formatted_ids if formatted_ids else None


def main():
    """主函数"""
    print("=" * 60)
    print("Notion 数据熵增检测工具")
    print("=" * 60)
    print()
    
    # 读取配置
    notion_token = os.getenv('NOTION_TOKEN')
    if not notion_token:
        print("❌ 错误: 未找到 NOTION_TOKEN 环境变量")
        print("请在 .env 文件中设置 NOTION_TOKEN")
        sys.exit(1)
    
    database_ids = parse_database_ids(os.getenv('DATABASE_IDS'))
    threshold_days = int(os.getenv('TIME_DECAY_THRESHOLD_DAYS', '30'))
    warning_threshold = float(os.getenv('TIME_DECAY_WARNING_THRESHOLD', '40.0'))
    
    print(f"配置信息:")
    print(f"  - 时间衰减阈值: {threshold_days} 天")
    print(f"  - 警告阈值: {warning_threshold}%")
    if database_ids:
        print(f"  - 指定数据库数量: {len(database_ids)}")
    else:
        print(f"  - 监控范围: 所有可访问的数据库")
    print()
    
    try:
        # 初始化组件
        print("🔌 正在连接 Notion API...")
        notion_client = NotionClient(token=notion_token)
        data_collector = DataCollector(notion_client)
        entropy_calculator = EntropyCalculator(notion_client)
        report_generator = ReportGenerator()
        print("✅ 连接成功")
        print()
        
        # 收集数据
        print("📊 正在收集数据...")
        database_pages = data_collector.collect_database_data(database_ids)
        
        if not database_pages:
            print("⚠️  警告: 未找到任何数据库或无法访问")
            print()
            print("可能的原因：")
            print("1. 指定的数据库 ID 不正确或未授权给集成")
            print("2. 集成没有访问这些数据库的权限")
            print()
            print("建议：")
            print("- 在 .env 文件中清空 DATABASE_IDS（留空或删除该行）")
            print("- 让脚本自动搜索所有可访问的数据库")
            print("- 或者在 Notion 中将数据库授权给集成")
            sys.exit(0)
        
        print(f"✅ 找到 {len(database_pages)} 个数据库")
        print()
        
        # 计算熵指标
        print("🧮 正在计算熵指标...")
        database_results = {}
        all_pages = []
        
        for db_id, pages in database_pages.items():
            print(f"  处理数据库: {db_id[:8]}... ({len(pages)} 个页面)")
            all_pages.extend(pages)
            
            # 获取数据库信息
            db_info = data_collector.get_database_info(db_id)
            
            # 计算多时间窗口衰减
            multi_decay = entropy_calculator.calculate_multi_threshold_decay(
                pages, thresholds=[30, 90, 150, 300]
            )
            
            # 计算链接断裂率
            link_breakage_rate, isolated_pages, link_stats = entropy_calculator.calculate_link_breakage_rate(
                pages
            )
            
            database_results[db_id] = {
                'database_info': db_info,
                'pages_count': len(pages),
                'multi_threshold_decay': multi_decay,
                'link_breakage_rate': link_breakage_rate,
                'isolated_pages': isolated_pages,
                'link_stats': link_stats
            }
        
        print()
        
        # 计算整体指标
        print("📈 正在计算整体指标...")
        
        # 计算多时间窗口衰减
        print("  计算多时间窗口衰减...")
        overall_multi_decay = entropy_calculator.calculate_multi_threshold_decay(
            all_pages, thresholds=[30, 90, 150, 300]
        )
        overall_time_decay_entropy = overall_multi_decay['thresholds'].get(30, {}).get('rate', 0)
        
        overall_link_breakage_rate, _, overall_link_stats = entropy_calculator.calculate_link_breakage_rate(
            all_pages
        )
        
        # 计算新增指标
        print("  计算活跃度指标...")
        activity_metrics = entropy_calculator.calculate_activity_metrics(all_pages)
        
        print("  计算属性完整度...")
        property_metrics = entropy_calculator.calculate_property_completeness(all_pages)
        
        print("  计算分类覆盖率...")
        categorization_metrics = entropy_calculator.calculate_categorization_coverage(all_pages)
        
        print("  抽样检测连接密度...")
        mention_metrics = entropy_calculator.calculate_mention_density(all_pages, sample_rate=0.1)
        
        # 计算健康度评分
        health_score = entropy_calculator.calculate_health_score(
            time_decay_entropy=overall_time_decay_entropy,
            activity_rate_30d=activity_metrics['activity_rate_30d'],
            property_completeness=property_metrics['avg_completeness'],
            categorization_coverage=categorization_metrics['coverage_rate']
        )
        
        print()
        print("✅ 时间衰减熵（多窗口）:")
        for t in [30, 90, 150, 300]:
            decay_data = overall_multi_decay['thresholds'].get(t, {})
            print(f"   >{t}天: {decay_data.get('rate', 0):.1f}% ({decay_data.get('count', 0)}个页面)")
        print(f"✅ 30天活跃率: {activity_metrics['activity_rate_30d']:.2f}%")
        print(f"✅ 属性完整度: {property_metrics['avg_completeness']:.2f}%")
        print(f"✅ 分类覆盖率: {categorization_metrics['coverage_rate']:.2f}%")
        print(f"✅ 连接密度(抽样): {mention_metrics['mention_density']:.2f}%")
        if overall_link_breakage_rate < 0:
            print(f"ℹ️  链接断裂率: 无法计算（数据库未使用关联功能）")
        else:
            print(f"✅ 整体链接断裂率: {overall_link_breakage_rate:.2f}%")
        print(f"🏥 知识库健康度: {health_score['score']:.1f}分 ({health_score['grade']} - {health_score['status']})")
        print()
        
        # 生成报告
        print("📝 正在生成报告...")
        report_content = report_generator.generate_report(
            database_results=database_results,
            overall_time_decay_entropy=overall_time_decay_entropy,
            overall_link_breakage_rate=overall_link_breakage_rate,
            threshold_days=threshold_days,
            warning_threshold=warning_threshold,
            activity_metrics=activity_metrics,
            property_metrics=property_metrics,
            categorization_metrics=categorization_metrics,
            mention_metrics=mention_metrics,
            health_score=health_score,
            multi_threshold_decay=overall_multi_decay
        )
        
        # 保存报告到 report 目录
        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report')
        os.makedirs(report_dir, exist_ok=True)
        report_path = report_generator.save_report(report_content, output_dir=report_dir)
        print(f"✅ 报告已保存: {report_path}")
        print()
        
        # 显示摘要
        print("=" * 60)
        print("检测完成！")
        print("=" * 60)
        print(f"🏥 知识库健康度: {health_score['score']:.1f}分 ({health_score['grade']} - {health_score['status']})")
        print(f"📊 时间衰减熵: {overall_time_decay_entropy:.2f}%")
        print(f"📈 30天活跃率: {activity_metrics['activity_rate_30d']:.2f}%")
        print(f"📄 报告文件: {report_path}")
        print()
        
        # 如果有警告，显示提醒
        if overall_time_decay_entropy > warning_threshold:
            print(f"⚠️  警告: 时间衰减熵超过阈值 ({warning_threshold}%)")
            print("   建议及时清理过期内容")
        
        if overall_link_breakage_rate > 30:
            print(f"⚠️  警告: 链接断裂率较高 ({overall_link_breakage_rate:.2f}%)")
            print("   建议增强知识网络连接")
        elif overall_link_breakage_rate < 0:
            print(f"ℹ️  提示: 数据库未使用 relation（关联）属性")
            print("   链接断裂率指标需要数据库配置关联字段才能计算")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

