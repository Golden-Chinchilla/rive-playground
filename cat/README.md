# Cat Walk — 出去走走

一个独立的 Rive CLI 示例。根据对话中的黑白猫咪参考重新绘制侧身角色：粗描边、黑色耳朵、圆点眼睛、白色身体和灰色阴影。不是对原 PNG 的自动绑定，也不是视频或 GIF 贴图。原有根目录 Character Lab 保持不变。

## 造型修正

本轮重做了圆脸、耳朵和五官，缩短并加圆身体、加粗四肢，调整弯尾。
步幅从 104 缩至 68，抬脚高度降至 18；网页移动速度同步匹配新步幅与 0.66 的支撑期比例。
这是参考原图的矢量重绘，仍是侧身行走姿态，不是原始坐姿 PNG 的逐像素还原。
网页资源带造型版本参数，避免更新后仍命中旧动画缓存。

## 直接看动画

在仓库根目录执行：

```sh
rive cat --fit=contain
```

画板 `Cat Walk`，默认状态机 `Cat`，循环时间线 `Walk`（72 帧 / 60 FPS = 1.2 秒）。Rive 文件本身是原地走路循环；网页同时移动角色的位置。

## 网页预览

```sh
python3 -m http.server 8000 --directory cat/web
# 浏览器打开 http://localhost:8000
```

页面提供播放/暂停、原地循环/往前走和左右方向切换。遵循 `prefers-reduced-motion`，初次加载时如系统要求减少动画则暂停。Rive JS/WASM 从固定版本 CDN 加载，需要网络；`.riv` 从当前网站加载。

## 修改角色或动作

```sh
python3 cat/build.py
rive cat --verify --format=json
rive inspect cat --summary
python3 -m unittest discover -s cat/tests -v
rive cat --once
cp cat/build/walking-cat.riv cat/web/walking-cat.riv
```

`build.py` 是美术和动作的单一源文件，`scene.rml` 和 `web/walking-cat.riv` 是构建结果。不要直接修改生成的 RML。

四肢各自为独立闭合矢量轮廓。生成器计算四拍步态与两段腿部 IK，再将结果烘焙为 **Rive 原生路径关键帧**。运行时不需要 Luau、不计算 IK、不使用骨骼蒙皮。尾巴与头部使用独立节点的旋转、位移关键帧。每条属性在首尾闭合，接触期的脚掌保持地面高度；网页位移速度与接触期脚掌相对速度一致。

前端接入参数：

```js
new rive.Rive({
  src: '/walking-cat.riv',
  canvas: document.querySelector('canvas'),
  artboard: 'Cat Walk',
  animations: 'Walk',
  autoplay: true,
});
```

`web/index.html` 展示完整生命周期、高清画布适配、暂停、减少动态效果、错误提示和页面位移。`build/design-proof.svg` 仅为生成器的静态设计检查图，不能替代真实 `.riv` 的浏览器渲染验收。
