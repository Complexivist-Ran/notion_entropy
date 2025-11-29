# 设置指南

## 第一步：创建 Notion Integration

1. 访问 https://www.notion.so/my-integrations
2. 点击 "New integration" 创建新集成
3. 填写集成信息：
   - **Name**: 例如 "Entropy Checker"
   - **Logo**: 可选
   - **Associated workspace**: 选择要监控的工作区
4. 设置权限：
   - **Capabilities**: 至少需要 "Read content" 权限
   - 建议选择 "Read content" 和 "Update content"（如果需要后续扩展功能）
5. 点击 "Submit" 创建集成
6. 复制 **Internal Integration Token**（可能是 `secret_` 或 `ntn_` 开头，取决于 Notion 版本）

## 第二步：授权集成访问数据库

1. 打开你要监控的 Notion 数据库
2. 点击右上角的 "..." 菜单
3. 选择 "Add connections" 或 "连接"
4. 搜索并选择你刚创建的集成
5. 确认授权

**注意**：
- 如果数据库在多个页面中，需要在每个页面中分别授权
- 或者在工作区级别授权（如果集成有工作区权限）

## 第三步：获取数据库 ID

1. 打开要监控的数据库
2. 查看浏览器地址栏，URL 格式类似：
   ```
   https://www.notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...
   ```
3. 复制 URL 中的 32 位十六进制字符串（`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`），这就是数据库 ID

**可选**：如果要监控多个数据库，可以收集多个数据库 ID，用逗号分隔。

## 第四步：配置环境变量

1. 在项目目录下创建 `.env` 文件：
   ```bash
   cp .env.example .env
   ```
   
   或者手动创建 `.env` 文件，内容如下：
   ```
   NOTION_TOKEN=secret_你的token
   DATABASE_IDS=数据库ID1,数据库ID2
   TIME_DECAY_THRESHOLD_DAYS=30
   TIME_DECAY_WARNING_THRESHOLD=40
   ```

2. 编辑 `.env` 文件，填入你的配置：
   - `NOTION_TOKEN`: 第一步获取的 Integration Token（必需）
   - `DATABASE_IDS`: 数据库ID列表，多个用逗号分隔（可选，留空则监控所有可访问的数据库）
   - `TIME_DECAY_THRESHOLD_DAYS`: 时间衰减阈值天数，默认30天（可选）
   - `TIME_DECAY_WARNING_THRESHOLD`: 警告阈值百分比，默认40%（可选）

## 第五步：安装依赖

```bash
pip install -r requirements.txt
```

## 第六步：运行检测

```bash
python notion_entropy_checker.py
```

## 输出说明

脚本运行后会：
1. 连接 Notion API
2. 收集所有指定数据库的页面数据
3. 计算时间衰减熵和链接断裂率
4. 生成 Markdown 格式的报告文件：`entropy_report_YYYYMMDD_HHMMSS.md`

报告包含：
- 整体指标概览
- 各数据库的详细分析
- 过期页面列表
- 孤立页面列表
- 改进建议

## 常见问题

### Q: 提示 "NOTion Token 未设置"
A: 检查 `.env` 文件是否存在，以及 `NOTION_TOKEN` 是否正确设置。

### Q: 提示 "无法访问数据库"
A: 确保集成已被授权访问该数据库。在工作区中打开数据库，点击右上角菜单，选择 "Add connections"，添加你的集成。

### Q: 找不到任何数据库
A: 检查集成是否有工作区访问权限，或者尝试在 `.env` 中明确指定 `DATABASE_IDS`。

### Q: API 请求频率限制
A: Notion API 有速率限制。如果遇到限制，脚本会自动处理，但可能需要等待。建议不要过于频繁地运行脚本。

## 定时运行

### Windows (任务计划程序)
1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器（例如：每周一）
4. 设置操作：启动程序
   - 程序：`python`
   - 参数：`D:\G\vibe_projects\202504_notion_cleaner\notion_entropy_checker.py`
   - 起始于：`D:\G\vibe_projects\202504_notion_cleaner`

### Linux/Mac (cron)
```bash
# 编辑 crontab
crontab -e

# 添加以下行（每周一早上9点运行）
0 9 * * 1 cd /path/to/202504_notion_cleaner && python notion_entropy_checker.py
```

