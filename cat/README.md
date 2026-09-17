# Cat Walk — 出去走走

使用现有 Rive CLI 技术栈制作的黑白侧身猫咪走路循环。造型参考对话中的九宫格：白色身体、粗黑圆角描边、单只椭圆眼睛、短胡须、竖耳和向上弯曲的尾巴。所有姿势使用同一套矢量部件，不切换角色图片。根目录原有 Character Lab 保持不变。

## 直接运行

在仓库根目录执行：

```sh
rive cat --fit=contain
```

画板为 `Cat Walk`，默认状态机为 `Cat`，循环时间线为 `Walk`：**72 帧 / 60 FPS = 1.2 秒**。第 72 帧与第 0 帧闭合；它是循环边界，不额外停留一帧。

## 网页预览

```sh
python3 -m http.server 8000 --directory cat/web
# 浏览器打开 http://localhost:8000
```

默认在画面中央原地走路，也可以播放/暂停、切换往前走和左右方向。初次加载遵循 `prefers-reduced-motion`。网页只控制时间、整体位移和镜像；腿部、身体、头部和尾巴的动画都来自真实 `.riv` 中的原生关键帧，而不是 CSS 动画或 SVG 替代品。

Rive JS/WASM 从固定版本 CDN 加载，需要网络；`.riv` 从当前网站加载。资源带造型版本参数，避免命中旧版猫咪缓存。

## 动作与角色一致性

四肢保持固定身份及遮挡关系。着地顺序为近侧后腿 → 近侧前腿 → 远侧后腿 → 远侧前腿，每隔四分之一周期迈一步；始终至少两脚处于支撑期。步幅为 96，抬脚高度为 24，支撑期比例为 0.66。头部、耳朵、五官、身体及尾巴的局部轮廓在整个循环中不变，只通过独立节点产生轻微起伏和跟随摆动。

生成器计算脚掌轨迹与两段腿部 IK，以柔化后的轮廓绘制短腿，再烘焙为 **Rive 原生路径关键帧**。运行时不依赖 Luau、IK 脚本、骨骼蒙皮、位图或外部字体。近侧腿使用闭合填充和开放描边，避免腿根出现横向黑色接缝。

接触阶段的脚掌高度固定；进入抬脚阶段和重新落地时，轨迹的位置及速度连续。网页往前走的速度与支撑期脚掌的相对速度匹配。原地循环模式本身不产生整体位移。

## 修改与构建

```sh
python3 cat/build.py
rive cat --verify --format=json
rive inspect cat --summary
python3 -m unittest discover -s cat/tests -v
rive cat --once
cp cat/build/walking-cat.riv cat/web/walking-cat.riv
```

`build.py` 是角色造型和步态的单一源文件；`scene.rml` 和 `web/walking-cat.riv` 是生成结果，不要直接编辑。生成器同时输出：

- `build/design-proof.svg`：单帧设计检查图。
- `build/contact-sheet.svg`：按行排列的九个检查姿势，时间为 0、0.15、0.30、0.45、0.60、0.75、0.90、1.05、1.20 秒，最后一格与第一格相同。

这些 SVG 只用于检查作者几何，不能代替真实 `.riv` 的渲染验收。

## 验证与真实渲染

标准库测试覆盖 20 项结构及运动不变量，包括：四肢独立、角色局部几何不漂移、四拍顺序、接触连续性、所有脚掌的 IK 可达性、首尾关键帧闭合、生成结果可重复，以及网页位移速度一致性。

GitHub Actions 编译 RML 后，使用官方 Canvas 运行时在 Chromium 中加载实际 `.riv`，检查原地走、前进、左右方向、暂停、移动端布局及减少动态效果，并导出真实渲染的 GIF、九宫格和九张独立关键帧。首尾检查直接读取原生时间线的最后一帧，不通过 JavaScript 取模回到第零帧。

CI 的 `walking-cat-preview` 工件包含 `.riv`、RML、验证日志和 `browser/` 下的预览。主分支提交信息包含 `[rebuild-cat]` 时，现有工作流会在全部验证通过后，将重新生成的 RML 和 `.riv` 补交到 `main`；不会强推覆盖其他提交。

## 前端接入

```js
new rive.Rive({
  src: '/walking-cat.riv',
  canvas: document.querySelector('canvas'),
  artboard: 'Cat Walk',
  animations: 'Walk',
  autoplay: true,
});
```

也可以启用 `Cat` 状态机。公开名称保持不变，现有嵌入入口仍可使用。
