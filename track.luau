type Track = {
    size: Vector,
    headX: Property<number>?, headY: Property<number>?, headRotation: Property<number>?,
    eyeX: Property<number>?, eyeY: Property<number>?,
    x: number, y: number, targetX: number, targetY: number,
}

function init(self: Track, context: Context): boolean
    local vm = context:viewModel()
    if vm == nil then return true end
    self.headX = vm:getNumber('headX')
    self.headY = vm:getNumber('headY')
    self.headRotation = vm:getNumber('headRotation')
    self.eyeX = vm:getNumber('eyeX')
    self.eyeY = vm:getNumber('eyeY')
    return true
end

function resize(self: Track, size: Vector)
    self.size = size
    if self.targetX < 0 then
        self.x = size.x * 0.5
        self.y = size.y * 0.43
        self.targetX = self.x
        self.targetY = self.y
    end
end
function pointerMove(self: Track, event: PointerEvent) self.targetX = event.position.x; self.targetY = event.position.y end
function pointerExit(self: Track, event: PointerEvent)
    self.targetX = self.size.x * 0.5
    self.targetY = self.size.y * 0.43
end

function advance(self: Track, seconds: number): boolean
    local response = 1 - math.exp(-8.5 * seconds)
    self.x += (self.targetX - self.x) * response
    self.y += (self.targetY - self.y) * response
    local width = if self.size.x > 0 then self.size.x else 668
    local height = if self.size.y > 0 then self.size.y else 816
    local nx = math.clamp((self.x / width) * 2 - 1, -1, 1)
    local ny = math.clamp((self.y / height) * 2 - 0.86, -1, 1)

    if self.headX ~= nil then self.headX.value = 334 + nx * 18 end
    if self.headY ~= nil then self.headY.value = 350 + ny * 13 end
    if self.headRotation ~= nil then self.headRotation.value = nx * 0.045 end
    if self.eyeX ~= nil then self.eyeX.value = nx * 10 end
    if self.eyeY ~= nil then self.eyeY.value = ny * 7 end
    return true
end

return function(context: Context): Layout<Track>
    return { size = Vector.xy(0, 0), headX = nil, headY = nil, headRotation = nil,
        eyeX = nil, eyeY = nil,
        x = 334, y = 350, targetX = -1, targetY = -1,
        init = init, resize = resize, advance = advance, pointerMove = pointerMove, pointerExit = pointerExit }
end
