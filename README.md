# Character Lab — Look Alive

黑白粗描边的交互人物海报。原来的矢量角色保留在中央，周围增加标题、环形背景、对话气泡、手写感信息卡、实时注视仪表和底部模式控制。全部 UI 都在 Rive 场景内，不是叠在画布外的 HTML。

## 运行

```sh
rive . --fit=contain
```

画布为 **1280 × 860**。当前版是固定构图海报，窗口改变时请使用 `contain` 等比缩放；尚未做手机竖屏重新排版。Artboard 名称仍为 `Character Follow`，状态机仍为 `Follow`，以保留现有嵌入入口。

| 控制 | 行为 |
| --- | --- |
| FOLLOW | 眼睛先、头部后，跟随指针；离开后平滑回正。 |
| IDLE | 忽略指针，只做轻微的待机运动。 |
| WANDER | 自主左右张望，仪表跟随实际视线。 |
| RESET | 回到 FOLLOW，并把目标视线复位。 |

气泡和状态卡有克制的漂浮；右侧点位和 X/Y 仪表读取平滑后的视线，底部黑色标记指示当前模式。点击要求按下、释放都落在同一按钮内，拖出不会误触。

## 编辑与构建

`scene.rml` 是生成文件。修改下面的源文件后重新生成，避免手改 RML 被下一次构建覆盖：

```sh
python3 authoring/build_character.py
rive . --verify --format=json
rive inspect . --summary
python3 -m unittest discover -s tests -v
rive . --once
```

- `source/character.svg`：原人物 SVG，未改变美术几何。
- `authoring/build_character.py`：保留原人物路径与脖子绑定，组装完整画布。
- `authoring/poster.py`：UI 布局、配色、矢量图形与原创单线字形；不依赖外部字体或位图。
- `follow.luau`：人物跟随、按钮命中、三种模式、实时仪表。
- `tests/test_poster.py`：5 项结构检查、6 项使用真实 Rive CLI 指针事件与数据转储的行为测试。无 CLI 时仅跳过行为测试；可通过 `RIVE_BIN` 指定可执行文件。
- `authoring/preview_svg.py`：将本项目使用的 RML 矢量子集导出为静态 SVG 布局预览，不是通用 RML 转换器。
- `legacy-backup/`、`tools/`、`track.luau`：保留旧文件，不参与当前构建。

## 预览与行为检查

```sh
rive . --screenshot=build/rest.png --advance=1
rive . --screenshot=build/look-right.png --pointer=move@1180,270 --advance=60
rive . --data-dump=build/wander.json --pointer=click@506,783 --advance=60
rive . --data-dump=build/reset.json --pointer=click@506,783 --advance=60 --pointer=click@670,783 --advance=90
```

静态构图预览（只需 Python 标准库，可在浏览器打开）：

```sh
python3 authoring/preview_svg.py
# build/poster-preview.svg

# 也可应用 Rive 原生运行时导出的实际姿态：
python3 authoring/preview_svg.py --pose build/wander.json --output build/wander-preview.svg
```

本次验证环境为 Rive CLI 1.0.4 / Linux：编译与 inspect 无错误、无警告，11 项测试通过。在该无头环境中，新版和改动前的原版项目都生成了纯色原生截图，因此 **SVG 布局预览不代表原生渲染已完成视觉验收**。最终原生显示效果仍需在本地 `rive . --fit=contain` 中确认。

## 嵌入参数

启动 `Follow` 状态机并启用自动数据绑定。公开数字属性：

- `mode`：`0` = FOLLOW，`1` = IDLE，`2` = WANDER。
- `motion`：`1` = 正常，`0` = 静止姿态；宿主可用它响应减少动态效果设置。

例如：

```sh
rive . --data=motion=0 --fit=contain
```

`.riv` 是离线 unsigned 构建，嵌入环境需支持 Rive 脚本。正式发布可使用已登录 CLI 的 `rive . --publish`。本项目根据静态 SVG 与录屏重建，不包含原作骨骼或原始动画时间线。素材来源与许可说明见 [ATTRIBUTION.md](ATTRIBUTION.md)。

## CI

GitHub Actions 在 `main` 和 PR 上执行重新生成、编译、结构/交互测试，并保留诊断与布局预览。普通提交要求 `scene.rml` 已同步。直接向 `main` 提交且提交信息包含 `[rebuild-scene]` 时，CI 在验证通过后补交生成的 `scene.rml`；不会强推，若远端分支已前进则停止，避免覆盖其他工作。
