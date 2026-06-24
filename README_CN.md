# EverAlbum

EverAlbum 是一个以 `tkinter` 为界面的智能相册生成项目，当前包含两条主线：

- 相册主程序：按时间线和地点聚合照片，生成 A4 `PDF`，可选导出 `PPTX`
- 人像去背辅助程序：使用 `rembg` 对选定人像去背景，并把透明 PNG 保存到相册素材库，供章节页叠加使用

当前代码已经完成了第一轮模块化，但仍保留了一个现实约束：相册生成的主逻辑还集中在 [`everalbum/album_app.py`](/D:/Codex/EverAlbum/everalbum/album_app.py) 中。后续维护时，建议把它当成“稳定但偏重”的核心文件来对待。

## 目录结构

```text
EverAlbum/
├─ photo_album_generator pro.py          # 主程序兼容启动器
├─ portrait_bg_remover.py                # 去背工具兼容启动器
├─ everalbum/
│  ├─ __init__.py
│  ├─ album_app.py                       # 相册扫描、聚类、叙事、PDF/PPTX 构建、GUI
│  ├─ portrait_app.py                    # 人像去背 GUI
│  └─ services/
│     ├─ config.py                       # AlbumBuildRequest 配置数据模型
│     ├─ narrative_engine.py             # 章节文案 / 页签文案生成
│     ├─ portrait_assets.py              # 人像素材库与 manifest
│     ├─ portrait_removal.py             # rembg 封装
│     └─ workspace.py                    # 工作区根目录 / 默认素材库路径
├─ portrait_elements/                    # 默认人像素材库（运行后自动创建）
└─ SKILL.md                              # 后续维护用技能文档
```

说明：

- 根目录下还有若干 `*_render`、`*_cache`、`*.pdf` 测试产物，它们是调试/验证输出，不是源代码。
- 运行相册生成时，输出目录和缓存目录现在会自动加入扫描排除，避免生成结果被下次误识别为输入照片。

## 当前功能状态

### 相册主程序

- 输入一个或多个照片目录
- 仅读取 EXIF 完成第一次扫描，降低大批量照片的预处理成本
- 按时间间隔和地理半径聚合事件
- 对每个事件做评分、节奏分配和布局分配
- 生成 A4 `PDF`
- 可选导出 A4 `PPTX`
- 支持章节页叠加透明人像元素
- 支持章节叙事文案和页签短文案
- 支持九宫格、圆形簇、六边形蜂巢等特殊版式

### 人像去背工具

- 加载单张图片
- 调用 `rembg` 去背景
- 可预览透明底 / 纯色底 / 渐变底效果
- 可保存到默认人像素材库 `portrait_elements/`
- 主程序可把这些素材作为章节页元素叠加

## 依赖

项目当前没有单独的 `requirements.txt`，按代码现状至少需要：

```powershell
py -3 -m pip install pillow reportlab python-pptx exifread
py -3 -m pip install rembg onnxruntime
py -3 -m pip install pillow-heif
```

说明：

- `python-pptx` 只有在导出 `PPTX` 时才需要
- `pillow-heif` 只有在需要读取 `HEIC/HEIF` 时才需要
- `exifread` 强烈建议安装，否则 GPS 提取可能退回到 Pillow，稳定性会差一些
- `rembg` 和 `onnxruntime` 是去背工具的关键依赖

## 启动方式

### 启动相册主程序

```powershell
py -3 ".\photo_album_generator pro.py"
```

### 启动去背工具

```powershell
py -3 ".\portrait_bg_remover.py"
```

也可以直接运行包内入口：

```powershell
py -3 -c "from everalbum.album_app import App; App().mainloop()"
py -3 -c "from everalbum.portrait_app import App; App().mainloop()"
```

## 核心架构

### 1. 启动层

- [`photo_album_generator pro.py`](/D:/Codex/EverAlbum/photo_album_generator%20pro.py) 只是兼容入口，真正 GUI 在 `everalbum.album_app.App`
- [`portrait_bg_remover.py`](/D:/Codex/EverAlbum/portrait_bg_remover.py) 只是兼容入口，真正 GUI 在 `everalbum.portrait_app.App`

### 2. 服务层

- [`everalbum/services/config.py`](/D:/Codex/EverAlbum/everalbum/services/config.py)
  - 定义 `AlbumBuildRequest`
  - 适合继续承接“参数对象化”和未来 CLI / API 化
- [`everalbum/services/narrative_engine.py`](/D:/Codex/EverAlbum/everalbum/services/narrative_engine.py)
  - 负责事件上下文建模
  - 负责章节故事与照片页签文案
  - 负责整本相册级别的文案去重
- [`everalbum/services/portrait_assets.py`](/D:/Codex/EverAlbum/everalbum/services/portrait_assets.py)
  - 管理 `portrait_elements/`
  - 保存 `manifest.json`
  - 维护 PNG 人像素材与元信息
- [`everalbum/services/portrait_removal.py`](/D:/Codex/EverAlbum/everalbum/services/portrait_removal.py)
  - 对 `rembg` 做懒加载封装
  - 避免 GUI 启动时直接阻塞
- [`everalbum/services/workspace.py`](/D:/Codex/EverAlbum/everalbum/services/workspace.py)
  - 统一“工作区根目录”和默认人像素材目录

### 3. 相册主链路

主流程入口是 [`build_album()`](/D:/Codex/EverAlbum/everalbum/album_app.py:2431)。

当前相册生成大致分成以下阶段：

1. `scan_exif_only`
   - 扫描文件夹
   - 只读取 EXIF / 时间 / GPS 等元数据
   - 避免一开始就把所有图片完整解码进内存
2. `EventClusterer.cluster`
   - 按时间间隔和地理半径聚合事件
3. `EventClusterer.merge_small_events`
   - 当前规则：少于 5 张的事件只在“同月内”合并，不跨月吞并
4. 评分阶段
   - 对候选照片做清晰度 / 曝光等评分
5. 地点阶段
   - 可选做反向地理编码
   - 当前也支持纯坐标回退
6. `StoryEngine.plan` / `NarrativeEngine`
   - 生成章节叙事和页签短句
7. `AlbumBuilder`
   - 渲染 PDF
8. `PptxBuilder`
   - 渲染 A4 比例 PPTX

## 目前的重要规则

这几条属于“维护时不要无意改坏”的项目行为：

- 章节页如果没有可靠地名，不再显示“途中坐标”作为大标题
- 月份照片少于 `10` 张时，不创建月份分隔页
- 事件照片少于 `5` 张时，只允许在同月内合并
- 相册页面顶部标签和照片之间要留空，不得压住照片
- 六边形版式已修成“不重叠前提下尽量放大”
- 生成输出目录会自动排除扫描，避免测试产物污染下一次构建

## 当前主要模块说明

### `everalbum/album_app.py`

这是当前最重要、也最需要谨慎维护的文件。它同时包含：

- EXIF 扫描与通用工具
- 缩略图缓存
- 事件聚类
- 页面节奏与布局选择
- PDF 构建器
- PPTX 构建器
- 主 GUI

优点：

- 所有主流程都在一处，定位问题很直接

缺点：

- 文件偏大
- PDF / PPTX 两套布局逻辑并存，修改版式时容易漏一边

后续如果做更深的重构，优先建议拆分为：

- `pipeline/`
- `layout_strategies/`
- `builders/pdf_builder.py`
- `builders/pptx_builder.py`
- `gui/`

### `everalbum/services/narrative_engine.py`

这里是“故事感”的核心。

现在它负责：

- 事件上下文抽取
- 节奏 / 能量 / 场景推断
- 章节文案生成
- 页签短文案生成
- 整本相册内的精确去重
- 当大事件页数超过预生成数量时，按需扩展新文案

如果以后用户继续反馈“读起来像同一个句子在换词”，优先看这里。

### `everalbum/portrait_app.py`

这是相对独立的 GUI，最好继续保持独立，不要把去背逻辑重新塞回 `album_app.py`。

推荐的维护方向是：

- 保持它作为一个独立工具存在
- 但让主程序未来可以“选中照片后直接送去去背”

## 维护时的高风险点

### 1. PDF 和 PPTX 不一致

任何改动只要碰到版式、章节页、页签条、形状图片，通常都要同步看：

- `AlbumBuilder`
- `PptxBuilder`

如果只改了一边，另一边大概率会悄悄落后。

### 2. 终端乱码不等于 PDF 真乱码

这个仓库里有一些历史中文字符串在终端里会出现乱码表现，尤其在 Windows 控制台和某些字体回退环境下。

维护时注意：

- 优先使用 `py -3 -X utf8 -` 跑小脚本
- 优先看生成出来的 PDF / GUI / 实际文本渲染
- 不要只因为 PowerShell 里显示异常，就直接断言最终文案有问题

### 3. 大批量测试很慢

对 `F:\Annual 2025` 这类大目录做真实生成时，整本 PDF 可能需要很多分钟。

先做：

- AST 检查
- 模块导入检查
- 单页样张

再做整本测试，会更稳。

### 4. 测试输出目录不能再被扫回输入

虽然当前已经做了自动排除，但如果未来改动了 `build_album()` 的输入/输出路径逻辑，一定要重新验证：

- 在源目录下新建测试文件夹
- 输出 PDF 到测试文件夹
- 第二次构建时，测试文件夹不会被重新扫描进相册

## 推荐测试方式

### 1. 基础静态检查

```powershell
@'
from pathlib import Path
import ast
for rel in ['everalbum/album_app.py', 'everalbum/services/narrative_engine.py']:
    ast.parse(Path(rel).read_text(encoding='utf-8'))
    print('AST OK', rel)
'@ | py -3 -X utf8 -
```

### 2. 导入检查

```powershell
@'
import importlib
for mod in ['everalbum.album_app', 'everalbum.portrait_app', 'everalbum.services.narrative_engine']:
    importlib.import_module(mod)
    print('IMPORT OK', mod)
'@ | py -3 -X utf8 -
```