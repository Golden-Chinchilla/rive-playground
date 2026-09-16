# Character Follow

从提供的 SVG 重新生成的原生 Rive 矢量角色。头部轻转、五官视差、瞳孔快速跟随、脖子底部固定；鼠标离开后平滑回正。

运行（在此目录）：

```sh
rive . --fit=contain
```

构建与检查：

```sh
rive . --verify
rive inspect . --summary
rive . --once
rive . --screenshot --advance=1
rive . --screenshot=build/look-right.png --pointer=move@630,650 --advance=45
```

- `scene.rml`：26 个可编辑矢量 Shape，保留 SVG 的三次贝塞尔曲线、描边和图层。
- `follow.luau`：指针归一化、指数平滑、各部位跟随幅度、脖子锚定。
- `source/character.svg`：用户提供的 SVG 原件。
- `authoring/build_character.py`：重新生成 RML（会覆盖 scene.rml）。只支持此 SVG 使用的绝对 M/L/H/V/C/Z 和 ellipse；不接受任意 SVG。
- `build/character-follow.riv`：CLI 构建的运行时文件，包含跟随脚本。
- `legacy-backup/`：之前的项目文件备份，不参与构建。

画布为 668 × 816，预览或嵌入时使用 contain 等比缩放，启动 `Follow` 状态机并启用自动数据绑定。嵌入环境需支持 Rive 脚本；CLI 的本地预览已验证。`.riv` 使用离线 unsigned 构建；正式发布可使用已登录 CLI 的 `rive . --publish`。

这是根据静态 SVG 和录屏重新实现的交互，不包含原作的骨骼或原始动画时间线。

素材来源与许可说明见 ATTRIBUTION.md。
