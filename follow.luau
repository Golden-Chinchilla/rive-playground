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
type Follow = { props: {[string]: Property<number>}, tx: number, ty: number, hx: number, hy: number, ex: number, ey: number }
local function put(self: Follow, name: string, value: number)
    local p = self.props[name]
    if p then p.value = value end
end
local function init(self: Follow, context: Context): boolean
    local vm = context:viewModel()
    if vm then
        for _, name in ipairs({"headX", "headY", "headRotation", "headScaleX", "featuresX", "featuresY", "eyesX", "eyesY", "noseX", "noseY", "mouthX", "mouthY"}) do
            local p = vm:getNumber(name)
            if p then self.props[name] = p end
        end
        for _, a in ipairs(anchors) do
            for _, axis in ipairs({"X", "Y"}) do
                local p = vm:getNumber(a.name .. axis)
                if p then self.props[a.name .. axis] = p end
            end
        end
    end
    return true
end
local function pointerMove(self: Follow, event: PointerEvent)
    local p = event.position
    if p.x < 0 or p.x > 668 or p.y < 0 or p.y > 816 then
        self.tx = 0; self.ty = 0
    else
        self.tx = math.clamp((p.x - 334) / 334, -1, 1)
        self.ty = math.clamp((p.y - 360) / 380, -1, 1)
    end
end
local function pointerExit(self: Follow, event: PointerEvent)
    self.tx = 0; self.ty = 0
end
local function advance(self: Follow, dt: number): boolean
    local headBlend = 1 - math.exp(-9 * dt)
    local eyeBlend = 1 - math.exp(-19 * dt)
    self.hx += (self.tx - self.hx) * headBlend
    self.hy += (self.ty - self.hy) * headBlend
    self.ex += (self.tx - self.ex) * eyeBlend
    self.ey += (self.ty - self.ey) * eyeBlend
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
    -- Deform the upper neck with the head, with a zero-weight fixed base.
    for _, a in ipairs(anchors) do
        local w = math.clamp((667 - a.y) / 100, 0, 1)
        local px, py = (a.x - 340) * sx, a.y - 450
        local nx = 340 + x * 14 + px * math.cos(r) - py * math.sin(r)
        local ny = 450 + y * 10 + px * math.sin(r) + py * math.cos(r)
        put(self, a.name .. "X", a.x + (nx - a.x) * w)
        put(self, a.name .. "Y", a.y + (ny - a.y) * w)
    end
    return true
end
return function(): Node<Follow>
    return { props = {}, tx = 0, ty = 0, hx = 0, hy = 0, ex = 0, ey = 0,
        init = init, advance = advance, pointerMove = pointerMove, pointerExit = pointerExit }
end
