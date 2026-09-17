# Cat Walk — 出去走走

现有 Rive CLI 技术栈上的黑白猫咪四拍行走循环。根目录 Character Lab 不变。

## 运行

```sh
# 仓库根目录
rive cat --fit=contain

# 网页预览
python3 -m http.server 8000 --directory cat/web
# http://localhost:8000
```

公开入口保持为画板 `Cat Walk`、状态机 `Cat`、时间线 `Walk`。周期 1.2 秒，72 帧 / 60 FPS；第 72 帧是与第 0 帧重合的循环边界，不额外停顿。网页默认原地循环，支持暂停、前进、左右方向和减少动态效果偏好。

## 本轮修正：轮廓和支撑转换

旧版本把闭合身体、腿部填充、开放描边分别叠放，某些姿势会露出腿根封口、重复黑线和针状小缝。本轮不再用遮盖补丁处理这些位置：

- **近侧两腿、身体、头部外缘和尾巴共用一条闭合外轮廓**；各段由独立函数生成，再以固定拓扑拼接。胸口和腹部接腿处共享切线，去掉横向脖子接缝。
- 远侧两腿保持独立，根部封口始终藏在身体内部；四条腿的身份与前后遮挡关系不在循环中互换。
- 脚掌和小腿改成连续三次曲线，去掉直线鞋底、突出的靴尖和多段弯折的小鼓包。
- 前后躯分别计算支撑转换后的轻微压低/抬起，带少量身体俯仰；头部略有滞后，尾巴轻摆。头部轮廓和五官使用同一个刚性变换，不逐帧变脸。
- 步幅 88，抬脚 28，支撑期比例 0.62。着地顺序为近后 → 近前 → 远后 → 远前，始终至少两脚支撑。网页前进速度匹配支撑期脚掌的后移速度。
- 每个原生帧烘焙一次，减少两帧间插值造成的轮廓漂移。仍是 Rive 原生路径关键帧，不是位图序列、CSS 动画或运行时 IK。

**背景变化：** 本版 `.riv` 自带浅灰白色背景 `#f7f7f5`，使 CLI 深色预览器下也能看清黑色轮廓；不再内置浅色椭圆地垫。它不是透明资源。网页舞台使用同色背景，地面参考线由网页绘制。

## 修改和构建

`cat/build.py` 是造型和动作的源文件；`cat/scene.rml`、`cat/web/walking-cat.riv` 是生成结果，不要直接修改。

```sh
python3 cat/build.py
rive cat --verify --format=json
rive inspect cat --summary
python3 -m unittest discover -s cat/tests -v
rive cat --once
cp cat/build/walking-cat.riv cat/web/walking-cat.riv
```

生成器只依赖 Python 标准库。RML 属性键沿用 CLI 验证过的 schema；CI 保留相关 schema 和编译诊断。需要调步幅、周期或支撑比例时，同步修改网页中的 `cycle` 和 `unitsPerSecond`，测试会检查一致性。

关键函数：`limb()` 生成每条腿，`silhouette()` 拼接近侧连续轮廓，`foot()` 控制接触/抬脚轨迹，`load_y()` 控制前后躯承重起伏。统一轮廓意味着近侧两腿不再是可单独旋转的 Rive Shape，而是外轮廓中的独立顶点段；不要恢复旧的叠层腿根方案。

## 验收

标准库回归检查覆盖原生循环、四拍顺序、接触速度连续、半帧采样的外轮廓自交、远侧封口是否埋入躯干、腿腹接点切线连续、头部刚性、稳定拓扑和生成结果同步。

CI 编译后仍使用官方 Canvas 运行时和 Chromium 加载真实 `.riv`，检查原地走、前进、左右、暂停、首尾闭合、移动端布局和减少动态效果。`walking-cat-preview` 工件中的 `browser/walking-cat.gif`、`browser/contact-sheet.png` 和九张独立关键帧来自实际 `.riv`。`build/design-proof.svg`、`build/contact-sheet.svg` 只是作者几何预览，不能替代这些运行时结果。

自动测试不证明动画已经自然或美术已经准确；修改后仍需检查完整循环，尤其是四肢交叠、腿根和身体起伏。主分支提交信息包含 `[rebuild-cat]` 时，现有 CI 在验证通过后补交生成资源，不强推。

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

也可以启用 `Cat` 状态机。网页 JS/WASM 仍固定在 `@rive-app/canvas@2.42.1`，从 CDN 加载，需要网络。
