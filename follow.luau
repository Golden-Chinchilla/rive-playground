-- Pointer motion drives editable SVG-derived RML; no rasterized artwork.
type Anchor = { name: string, x: number, y: number }
local anchors: {Anchor} = {
    { name = "neck0", x = 415.52, y = 589.33 },
    { name = "neck1", x = 429.23, y = 667.06 },
    { name = "neck2", x = 219.62, y = 466.33 },
    { name = "neck3", x = 170.51, y = 667.13 },
    { name = "neck4", x = 217.7, y = 481.4 },
    { name = "neck5", x = 313.7, y = 577.3 },
    { name = "neck6", x = 413.2, y = 589.1 },
    { name = "neck7", x = 420.1, y = 626.3 },
    { name = "neck8", x = 290.1, y = 600.2 },
    { name = "neck9", x = 217.7, y = 481.4 },
    { name = "neck10", x = 169.5, y = 667.0 },
    { name = "neck11", x = 217.4, y = 462.0 },
    { name = "neck12", x = 406.6, y = 548.0 },
    { name = "neck13", x = 429.5, y = 667.0 },}

-- Artboard-space controls. Keep these rectangles aligned with poster.py.
local WIDTH = 1280
local UI_PROPERTIES = {"bubbleY", "statusY", "gazeX", "gazeY", "meterX", "meterY", "modeX", "mode", "motion"}
type Follow = {
    props: {[string]: Property<number>},
    tx: number, ty: number, hx: number, hy: number, ex: number, ey: number,
    elapsed: number, mode: number, pressed: number, modeX: number,
}
local function put(self: Follow, name: string, value: number)
    local p = self.props[name]
    if p then p.value = value end
end
local function init(self: Follow, context: Context): boolean
    local vm = context:viewModel()
    if not vm then return false end
    for _, name in ipairs({"headX", "headY", "headRotation", "headScaleX", "featuresX", "featuresY", "eyesX", "eyesY", "noseX", "noseY", "mouthX", "mouthY"}) do
        local p = vm:getNumber(name)
        if p then self.props[name] = p end
    end
    for _, name in ipairs(UI_PROPERTIES) do
        local p = vm:getNumber(name)
        if p then self.props[name] = p end
    end
    for _, a in ipairs(anchors) do
        for _, axis in ipairs({"X", "Y"}) do
            local p = vm:getNumber(a.name .. axis)
            if p then self.props[a.name .. axis] = p end
        end
    end
    return true
end
local function hitButton(x: number, y: number): number
    if y < 760 or y > 809 then return -1 end
    for i = 0, 2 do
        local left = 64 + i * 180
        if x >= left and x <= left + 164 then return i end
    end
    if x >= 613 and x <= 731 then return 3 end
    return -1
end
local function pointerMove(self: Follow, event: PointerEvent)
    local p = event.position
    -- Moving over the controls should not pull the face down out of its portrait.
    if p.x < 0 or p.x > WIDTH or p.y < 0 or p.y > 748 then
        self.tx = 0; self.ty = 0
    else
        self.tx = math.clamp((p.x - 646) / 535, -1, 1)
        self.ty = math.clamp((p.y - 410) / 325, -1, 1)
    end
end
local function pointerExit(self: Follow, event: PointerEvent)
    self.tx = 0; self.ty = 0; self.pressed = -1
end
local function pointerDown(self: Follow, event: PointerEvent)
    self.pressed = hitButton(event.position.x, event.position.y)
end
local function pointerUp(self: Follow, event: PointerEvent)
    local target = hitButton(event.position.x, event.position.y)
    if target >= 0 and target == self.pressed then
        if target == 3 then
            self.mode = 0
            self.tx = 0; self.ty = 0; self.elapsed = 0
        else
            self.mode = target
        end
        put(self, "mode", self.mode)
    end
    self.pressed = -1
end
local function advance(self: Follow, dt: number): boolean
    dt = math.clamp(dt, 0, 0.05)
    self.elapsed += dt
    local modeProperty = self.props["mode"]
    if modeProperty then self.mode = math.clamp(math.floor(modeProperty.value), 0, 2) end
    local motionProperty = self.props["motion"]
    local motion = if motionProperty then math.clamp(motionProperty.value, 0, 1) else 1
    local t = self.elapsed
    local tx, ty = self.tx, self.ty
    if self.mode == 1 then
        tx = math.sin(t * 0.55) * 0.06
        ty = math.sin(t * 0.9) * 0.035
    elseif self.mode == 2 then
        tx = math.sin(t * 0.63) * 0.78
        ty = math.sin(t * 0.41) * 0.52
    end
    tx *= motion; ty *= motion
    local headBlend = 1 - math.exp(-9 * dt)
    local eyeBlend = 1 - math.exp(-19 * dt)
    self.hx += (tx - self.hx) * headBlend
    self.hy += (ty - self.hy) * headBlend
    self.ex += (tx - self.ex) * eyeBlend
    self.ey += (ty - self.ey) * eyeBlend
    if motion == 0 then self.hx = 0; self.hy = 0; self.ex = 0; self.ey = 0 end
    local x, y = self.hx, self.hy
    local r = x * 0.055
    local sx = 1 - x * 0.025
    put(self, "headX", 340 + x * 14)
    put(self, "headY", 450 + y * 10)
    put(self, "headRotation", r)
    put(self, "headScaleX", sx)
    put(self, "featuresX", x * 13)
    put(self, "featuresY", y * 23)
    put(self, "noseX", x * 17)
    put(self, "noseY", y * 25)
    put(self, "mouthX", x * 11)
    put(self, "mouthY", y * 18)
    put(self, "eyesX", x * 13 + self.ex * 7)
    put(self, "eyesY", y * 23 + self.ey * 10)
    -- Preserve the original zero-weight fixed neck base.
    for _, a in ipairs(anchors) do
        local w = math.clamp((667 - a.y) / 100, 0, 1)
        local px, py = (a.x - 340) * sx, a.y - 450
        local nx = 340 + x * 14 + px * math.cos(r) - py * math.sin(r)
        local ny = 450 + y * 10 + px * math.sin(r) + py * math.cos(r)
        put(self, a.name .. "X", a.x + (nx - a.x) * w)
        put(self, a.name .. "Y", a.y + (ny - a.y) * w)
    end
    -- Cards respond subtly. The tracker displays the actual smoothed gaze.
    put(self, "bubbleY", 116 + (math.sin(t * 1.25) * 3 + y * 2) * motion)
    put(self, "statusY", 292 + (math.sin(t * 0.9) * 2 - y * 2) * motion)
    put(self, "gazeX", 79 + self.ex * 46)
    put(self, "gazeY", 117 + self.ey * 43)
    put(self, "meterX", 212 + self.ex * 29)
    put(self, "meterY", 212 + self.ey * 29)
    local selectedX = 76 + self.mode * 180
    self.modeX += (selectedX - self.modeX) * (1 - math.exp(-20 * dt))
    if motion == 0 then self.modeX = selectedX end
    put(self, "modeX", self.modeX)
    return true
end
return function(): Node<Follow>
    return {
        props = {}, tx = 0, ty = 0, hx = 0, hy = 0, ex = 0, ey = 0,
        elapsed = 0, mode = 0, pressed = -1, modeX = 76,
        init = init, advance = advance,
        pointerMove = pointerMove, pointerExit = pointerExit,
        pointerDown = pointerDown, pointerUp = pointerUp,
    }
end
