/**
 * 「应力场」背景：等高线（力与地形）、制图网格（建筑）与注意力网络（信息 / AI）。
 * 纯 WebGL + Canvas 2D 实现，不依赖第三方库；不可用时静默降级为纯色背景。
 */

import { Scene3D, type SceneWeights } from './scene3d'

export interface FieldOptions {
  /** 0 – 1，整体可见度 */
  intensity: number
  /** 是否绘制十字准星坐标（仅首页首屏） */
  crosshair: boolean
  /** 0 – 1，混沌到秩序：滚动越深，等高线越趋于规整 */
  order: number
  /** 首页三维场景：各章节的可见度（0 – 1）；为 null 时不绘制三维层 */
  scene: SceneWeights | null
  /** 二维节点网络的强度系数（首页三维层出现时减弱） */
  network: number
}

type Rgb = [number, number, number]

const VERTEX = `#version 300 es
in vec2 aPosition;
void main() { gl_Position = vec4(aPosition, 0.0, 1.0); }`

const FRAGMENT = `#version 300 es
precision highp float;
uniform vec2 uRes;
uniform float uTime;
uniform vec2 uMouse;
uniform float uPresence;
uniform float uScroll;
uniform float uOrder;
uniform float uIntensity;
uniform float uDpr;
uniform vec4 uRipples[4];
uniform vec3 uInk;
uniform vec3 uAccent;
out vec4 outColor;

vec3 permute(vec3 x) { return mod(((x * 34.0) + 1.0) * x, 289.0); }
float snoise(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
  vec2 i = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
  vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
  m = m * m; m = m * m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  vec3 g;
  g.x = a0.x * x0.x + h.x * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}
float fbm(vec2 p) {
  float sum = 0.0, amp = 0.5;
  for (int i = 0; i < 4; i++) { sum += amp * snoise(p); p = p * 2.03 + vec2(17.3, 9.1); amp *= 0.5; }
  return sum;
}
vec4 over(vec4 base, vec3 color, float alpha) {
  return base + vec4(color * alpha, alpha) * (1.0 - base.a);
}
float gridLine(vec2 coord, float spacing, float width) {
  vec2 d = abs(fract(coord / spacing - 0.5) - 0.5) * spacing;
  return 1.0 - smoothstep(0.0, width, min(d.x, d.y));
}

void main() {
  vec2 frag = gl_FragCoord.xy;
  float unit = min(uRes.x, uRes.y);
  vec2 p = (frag - 0.5 * uRes) / unit;
  vec2 m = (uMouse - 0.5 * uRes) / unit;
  float t = uTime * 0.035;
  vec2 q = p + vec2(0.0, uScroll / unit * 0.28);

  // 荷载：鼠标是一个作用在场上的集中力，等高线在它周围聚拢。
  vec2 dm = p - m;
  float d2 = dot(dm, dm);
  float load = uPresence * 0.42 * exp(-d2 * 7.0);
  float chaos = mix(1.0, 0.28, uOrder);
  // 点击涟漪：一圈向外扩散的波，推开等高线并留下暖色的环
  float ripple = 0.0;
  float ring = 0.0;
  for (int r = 0; r < 4; r++) {
    vec4 rp = uRipples[r];
    if (rp.w <= 0.0) continue;
    float rd = length(p - (rp.xy - 0.5 * uRes) / unit);
    float front = rp.z * 0.55;
    float fade = exp(-rp.z * 1.3) * rp.w;
    ripple += exp(-pow((rd - front) * 10.0, 2.0)) * fade;
    // 一道清晰的波前，加一道较弱的回声
    ring += (exp(-pow((rd - front) * 95.0, 2.0)) + 0.35 * exp(-pow((rd - front * 0.72) * 120.0, 2.0))) * fade;
  }
  float f = fbm(q * 1.08 + vec2(t, -t * 0.7)) * chaos + q.y * mix(0.22, 1.35, uOrder) + load + ripple * 0.3;

  vec4 acc = vec4(0.0);
  float near = uPresence * exp(-d2 * 9.0);

  // 等高线：每第五条为计曲线。
  float v = f * 13.0;
  float w = fwidth(v);
  float dist = abs(fract(v + 0.5) - 0.5);
  float isIndex = step(abs(mod(floor(v + 0.5), 5.0)), 0.5);
  float width = mix(0.9, 1.7, isIndex) * w;
  float contour = 1.0 - smoothstep(0.0, width, dist);
  float contourAlpha = contour * mix(0.075, 0.17, isIndex) * (1.0 + near * 2.4);
  acc = over(acc, mix(uInk, uAccent, clamp(near * 1.6, 0.0, 1.0)), contourAlpha);

  // 制图网格：被场轻微扭曲，越往下越规整。
  vec2 warp = vec2(sin(f * 3.1), cos(f * 2.7)) * 7.0 * uDpr * (1.0 - uOrder * 0.85);
  vec2 g = frag + warp + vec2(0.0, uScroll * uDpr * 0.28);
  float minor = gridLine(g, 28.0 * uDpr, 0.85 * uDpr);
  float major = gridLine(g, 140.0 * uDpr, 0.9 * uDpr);
  float edge = smoothstep(0.15, 0.95, length(p * vec2(0.85, 1.15)));
  acc = over(acc, uInk, minor * 0.022 * (0.45 + edge));
  acc = over(acc, uInk, major * 0.05 * (0.55 + edge));
  vec2 md = abs(fract(g / (140.0 * uDpr) - 0.5) - 0.5) * 140.0 * uDpr;
  float cross = (step(md.x, 0.7 * uDpr) * step(md.y, 5.0 * uDpr)) + (step(md.y, 0.7 * uDpr) * step(md.x, 5.0 * uDpr));
  acc = over(acc, uInk, clamp(cross, 0.0, 1.0) * 0.16);

  // 一束暖光跟随光标。
  acc = over(acc, uAccent, uPresence * 0.07 * exp(-d2 * 2.4));

  outColor = acc * uIntensity;
  // 涟漪不随页面强度衰减，保证在内页也清晰可见
  outColor = over(outColor, uAccent, clamp(ripple, 0.0, 1.0) * 0.03 + clamp(ring, 0.0, 1.0) * 0.13);
}`

const GLOSSES = ['∇L', 'σ(Wx+b)', 'QKᵀ/√d', 'Ku=f', '{ }', 'p(y|x)', '0x1F', 'Σ', 'h_t', '∂/∂θ', '</>', 'IoU', '∴', 'λx.x', 'H(X)=−Σp·log p', '♩ = 63', '道', 'MQTT · 1883', '∞', 'Γ ⊢ φ', 'e^{iπ}+1=0', '¬∃x', 'f(t) ↔ F(ω)', '知', '01101', 'A ≡ A']

interface Node {
  x: number
  y: number
  vx: number
  vy: number
  phase: number
  sensor: boolean
}

function parseColor(value: string, probe: CanvasRenderingContext2D): Rgb {
  probe.fillStyle = '#000'
  probe.fillStyle = value.trim() || '#000'
  const normalized = String(probe.fillStyle)
  if (normalized.startsWith('#')) {
    const hex = normalized.slice(1)
    return [0, 2, 4].map((index) => parseInt(hex.slice(index, index + 2), 16) / 255) as Rgb
  }
  const parts = normalized.match(/[\d.]+/g)?.slice(0, 3).map(Number) || [0, 0, 0]
  return parts.map((part) => part / 255) as Rgb
}

function compile(gl: WebGL2RenderingContext, type: number, source: string) {
  const shader = gl.createShader(type)
  if (!shader) return null
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.warn(gl.getShaderInfoLog(shader))
    gl.deleteShader(shader)
    return null
  }
  return shader
}

export class FieldRenderer {
  private gl: WebGL2RenderingContext | null = null
  private program: WebGLProgram | null = null
  private uniforms: Record<string, WebGLUniformLocation | null> = {}
  private overlay: CanvasRenderingContext2D | null
  private probe: CanvasRenderingContext2D | null
  private frame = 0
  private last = 0
  private start = performance.now()
  private width = 0
  private height = 0
  private glDpr = 1
  private uiDpr = 1
  private nodes: Node[] = []
  private mouse = { x: -9999, y: -9999, tx: -9999, ty: -9999, presence: 0, target: 0 }
  private lastInput = performance.now()
  private ink: Rgb = [0.12, 0.11, 0.1]
  private accent: Rgb = [0.79, 0.42, 0.28]
  private inkCss = 'rgb(30 29 26)'
  private accentCss = 'rgb(201 106 72)'
  private reduced: boolean
  private stopped = false
  private skip = 0
  private ripples: Array<{ x: number; y: number; t: number }> = []
  private burst: { x: number; y: number; t: number } | null = null
  private packets: Array<{ a: number; b: number; t: number; speed: number; hot: boolean }> = []
  private quality = 1
  private slowFrames = 0
  options: FieldOptions = { intensity: 1, crosshair: true, order: 0, scene: null, network: 1 }
  private smooth = { intensity: 0, order: 0, crosshair: 0, network: 1 }
  private scene: Scene3D | null = null
  private sceneCanvas: HTMLCanvasElement | null = null
  private sceneVisible = false

  constructor(private canvas: HTMLCanvasElement, private overlayCanvas: HTMLCanvasElement) {
    this.reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    this.overlay = overlayCanvas.getContext('2d')
    this.probe = document.createElement('canvas').getContext('2d')
    this.setupGl()
    this.readTheme()
    this.resize()
    this.smooth.intensity = this.options.intensity
  }

  get supported() { return Boolean(this.gl && this.program) }

  private setupGl() {
    const gl = this.canvas.getContext('webgl2', { alpha: true, antialias: false, premultipliedAlpha: true, powerPreference: 'low-power' })
    if (!gl) return
    const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX)
    const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT)
    if (!vertex || !fragment) return
    const program = gl.createProgram()
    if (!program) return
    gl.attachShader(program, vertex)
    gl.attachShader(program, fragment)
    gl.linkProgram(program)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return
    gl.useProgram(program)
    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
    const position = gl.getAttribLocation(program, 'aPosition')
    gl.enableVertexAttribArray(position)
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0)
    for (const name of ['uRes', 'uTime', 'uMouse', 'uPresence', 'uScroll', 'uOrder', 'uIntensity', 'uDpr', 'uInk', 'uAccent', 'uRipples']) {
      this.uniforms[name] = gl.getUniformLocation(program, name)
    }
    this.gl = gl
    this.program = program
  }

  readTheme() {
    if (!this.probe) return
    const styles = getComputedStyle(document.documentElement)
    const ink = styles.getPropertyValue('--field-ink') || styles.getPropertyValue('--color-ink')
    const accent = styles.getPropertyValue('--field-accent') || styles.getPropertyValue('--color-accent')
    this.ink = parseColor(ink, this.probe)
    this.accent = parseColor(accent, this.probe)
    const toCss = (rgb: Rgb) => `${Math.round(rgb[0] * 255)} ${Math.round(rgb[1] * 255)} ${Math.round(rgb[2] * 255)}`
    this.inkCss = toCss(this.ink)
    this.accentCss = toCss(this.accent)
    this.scene?.colors(this.inkCss, this.accentCss, document.documentElement.dataset.theme === 'dark')
    this.requestStatic()
  }

  resize() {
    const width = window.innerWidth
    const height = window.innerHeight
    const mobile = width < 760
    this.width = width
    this.height = height
    this.glDpr = Math.min(window.devicePixelRatio || 1, mobile ? 1 : 1.25) * this.quality
    this.uiDpr = Math.min(window.devicePixelRatio || 1, 2)
    this.canvas.width = Math.round(width * this.glDpr)
    this.canvas.height = Math.round(height * this.glDpr)
    this.overlayCanvas.width = Math.round(width * this.uiDpr)
    this.overlayCanvas.height = Math.round(height * this.uiDpr)
    this.scene?.resize(width, height, this.uiDpr * (mobile ? 1 : 0.9))
    const count = Math.round(Math.min(78, Math.max(26, (width * height) / 21000)))
    if (this.nodes.length !== count) this.seed(count)
    this.requestStatic()
  }

  private seed(count: number) {
    let state = 20260705
    const random = () => ((state = (state * 1664525 + 1013904223) % 4294967296) / 4294967296)
    this.nodes = Array.from({ length: count }, (_, index) => ({
      x: random() * this.width,
      y: random() * this.height,
      vx: 0,
      vy: 0,
      phase: random() * Math.PI * 2,
      sensor: index % 7 === 0,
    }))
  }

  pointer(x: number, y: number) {
    this.mouse.tx = x
    this.mouse.ty = y
    if (this.mouse.x < -9000) { this.mouse.x = x; this.mouse.y = y }
    this.mouse.target = 1
    this.lastInput = performance.now()
  }

  leave() { this.mouse.target = 0 }

  /** 点击 / 触摸：在场中激起一圈涟漪，并从最近的节点发出一组数据包。 */
  ripple(x: number, y: number) {
    this.ripples.push({ x, y, t: performance.now() / 1000 })
    this.burst = { x, y, t: performance.now() / 1000 }
    this.lastInput = performance.now()
    this.requestStatic()
  }

  touch() { this.lastInput = performance.now() }

  startLoop() {
    this.stopped = false
    if (this.reduced) { this.requestStatic(); return }
    if (!this.frame) this.frame = requestAnimationFrame(this.tick)
  }

  stopLoop() {
    this.stopped = true
    cancelAnimationFrame(this.frame)
    this.frame = 0
  }

  private requestStatic() {
    if (!this.reduced && !this.stopped && this.frame) return
    requestAnimationFrame(() => this.draw(performance.now(), 1 / 60))
  }

  private tick = (now: number) => {
    this.frame = 0
    if (this.stopped) return
    this.frame = requestAnimationFrame(this.tick)
    if (document.hidden) return
    // 无交互时降低到约 30fps，节省电量；交互时保持满帧。
    const idle = now - this.lastInput > 5000
    if (idle && (this.skip = (this.skip + 1) % 2)) return
    const raw = (now - (this.last || now)) / 1000
    const dt = Math.min(0.05, raw)
    this.last = now
    // 自适应画质：持续掉帧时降低场的分辨率，保证滚动丝滑。
    if (!idle && raw > 0.026) this.slowFrames += 1
    else this.slowFrames = Math.max(0, this.slowFrames - 1)
    if (this.slowFrames > 90 && this.quality > 0.6) {
      this.quality = Math.max(0.6, this.quality - 0.2)
      this.slowFrames = 0
      this.resize()
    }
    this.draw(now, dt || 1 / 60)
  }

  private draw(now: number, dt: number) {
    const ease = (rate: number) => 1 - Math.exp(-dt * rate)
    const mouse = this.mouse
    mouse.x += (mouse.tx - mouse.x) * ease(7)
    mouse.y += (mouse.ty - mouse.y) * ease(7)
    mouse.presence += (mouse.target - mouse.presence) * ease(3)
    this.smooth.intensity += (this.options.intensity - this.smooth.intensity) * ease(this.reduced ? 1000 : 2.4)
    this.smooth.order += (this.options.order - this.smooth.order) * ease(this.reduced ? 1000 : 4)
    this.smooth.crosshair += ((this.options.crosshair ? 1 : 0) - this.smooth.crosshair) * ease(this.reduced ? 1000 : 5)
    this.smooth.network += (this.options.network - this.smooth.network) * ease(this.reduced ? 1000 : 3)
    // rAF 的时间戳可能早于 start（同一帧内创建），负时间会让取模索引越界
    const time = this.reduced ? 12 : Math.max(0, (now - this.start) / 1000)
    this.drawField(time)
    this.drawNetwork(time, dt)
    this.drawScene(time, dt)
  }

  private drawField(time: number) {
    const gl = this.gl
    if (!gl || !this.program) return
    const u = this.uniforms
    gl.viewport(0, 0, this.canvas.width, this.canvas.height)
    gl.clearColor(0, 0, 0, 0)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.uniform2f(u.uRes!, this.canvas.width, this.canvas.height)
    gl.uniform1f(u.uTime!, time)
    gl.uniform2f(u.uMouse!, this.mouse.x * this.glDpr, (this.height - this.mouse.y) * this.glDpr)
    gl.uniform1f(u.uPresence!, this.mouse.presence)
    gl.uniform1f(u.uScroll!, window.scrollY * this.glDpr)
    gl.uniform1f(u.uOrder!, this.smooth.order)
    gl.uniform1f(u.uIntensity!, this.smooth.intensity)
    gl.uniform1f(u.uDpr!, this.glDpr)
    const rippleData = new Float32Array(16)
    const clock = performance.now() / 1000
    this.ripples = this.ripples.filter((r) => clock - r.t < 3)
    this.ripples.slice(-4).forEach((r, i) => rippleData.set([r.x * this.glDpr, (this.height - r.y) * this.glDpr, clock - r.t, 1], i * 4))
    gl.uniform4fv(u.uRipples!, rippleData)
    gl.uniform3fv(u.uInk!, this.ink)
    gl.uniform3fv(u.uAccent!, this.accent)
    gl.drawArrays(gl.TRIANGLES, 0, 3)
  }

  private drawNetwork(time: number, dt: number) {
    const ctx = this.overlay
    if (!ctx) return
    const { width, height } = this
    const intensity = this.smooth.intensity * this.smooth.network
    ctx.setTransform(this.uiDpr, 0, 0, this.uiDpr, 0, 0)
    ctx.clearRect(0, 0, width, height)
    if (intensity < 0.01) return
    const mouse = this.mouse
    const scrollShift = window.scrollY * 0.12
    const step = this.reduced ? 0 : dt * 60
    const link = Math.min(132, Math.max(96, width / 11))
    const points: Array<{ x: number; y: number; node: Node; d: number }> = []
    for (const node of this.nodes) {
      // 沿缓慢变化的流场漂移，像沿主应力迹线移动的信号。
      const angle = Math.sin(node.x * 0.0021 + time * 0.16) * Math.cos(node.y * 0.0018 - time * 0.12) * Math.PI * 1.4
      node.vx = (node.vx + Math.cos(angle) * 0.018 * step) * Math.pow(0.965, step)
      node.vy = (node.vy + Math.sin(angle) * 0.018 * step) * Math.pow(0.965, step)
      const wrap = (value: number) => ((value + 20) % (height + 40) + height + 40) % (height + 40) - 20
      const screenY = wrap(node.y - scrollShift)
      const dx = node.x - mouse.x, dy = screenY - mouse.y
      const dist = Math.hypot(dx, dy)
      if (dist < 150 && mouse.presence > 0.05) {
        const push = (1 - dist / 150) * 0.12 * mouse.presence * step
        node.vx += (dx / (dist || 1)) * push
        node.vy += (dy / (dist || 1)) * push
      }
      node.x += node.vx * step
      node.y += node.vy * step
      if (node.x < -20) node.x += width + 40
      if (node.x > width + 20) node.x -= width + 40
      node.y = wrap(node.y)
      const y = wrap(node.y - scrollShift)
      points.push({ x: node.x, y, node, d: Math.hypot(node.x - mouse.x, y - mouse.y) })
    }
    ctx.lineWidth = 0.6
    const edges: Array<[number, number]> = []
    for (let i = 0; i < points.length; i++) {
      const a = points[i]!
      for (let j = i + 1; j < points.length; j++) {
        const b = points[j]!
        const dx = a.x - b.x, dy = a.y - b.y
        if (Math.abs(dx) > link || Math.abs(dy) > link) continue
        const d = Math.hypot(dx, dy)
        if (d > link) continue
        edges.push([i, j])
        const glow = Math.max(0, 1 - Math.min(a.d, b.d) / 260) * mouse.presence
        const alpha = (1 - d / link) * (0.11 + glow * 0.25) * intensity
        ctx.strokeStyle = `rgb(${glow > 0.3 ? this.accentCss : this.inkCss} / ${alpha.toFixed(3)})`
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.stroke()
      }
    }
    // 数据包沿网络连线传输；点击时从最近的节点向四周爆发一组。
    if (edges.length) {
      const clock = performance.now() / 1000
      if (this.burst && clock - this.burst.t < 0.05) {
        const origin = points.reduce((best, p, i) => (Math.hypot(p.x - this.burst!.x, p.y - this.burst!.y) < Math.hypot(points[best]!.x - this.burst!.x, points[best]!.y - this.burst!.y) ? i : best), 0)
        edges.filter(([a, b]) => a === origin || b === origin).forEach(([a, b]) => this.packets.push({ a: a === origin ? a : b, b: a === origin ? b : a, t: 0, speed: 1.4 + Math.random(), hot: true }))
        this.burst = null
      }
      const quota = Math.min(14, Math.round(edges.length / 6))
      while (this.packets.filter((p) => !p.hot).length < quota && !this.reduced) {
        const [a, b] = edges[Math.floor(Math.random() * edges.length)]!
        this.packets.push(Math.random() > 0.5 ? { a, b, t: 0, speed: 0.4 + Math.random() * 0.6, hot: false } : { a: b, b: a, t: 0, speed: 0.4 + Math.random() * 0.6, hot: false })
      }
      this.packets = this.packets.filter((packet) => packet.t < 1 && points[packet.a] && points[packet.b])
      for (const packet of this.packets) {
        packet.t += (this.reduced ? 0 : dt) * packet.speed
        const a = points[packet.a]!, b = points[packet.b]!
        if (Math.hypot(a.x - b.x, a.y - b.y) > link * 1.3) { packet.t = 1; continue }
        const x = a.x + (b.x - a.x) * packet.t, y = a.y + (b.y - a.y) * packet.t
        const tail = Math.max(0, packet.t - 0.18)
        const tx = a.x + (b.x - a.x) * tail, ty = a.y + (b.y - a.y) * tail
        ctx.strokeStyle = `rgb(${this.accentCss} / ${((packet.hot ? 0.55 : 0.35) * intensity).toFixed(3)})`
        ctx.lineWidth = packet.hot ? 1.2 : 1
        ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(x, y); ctx.stroke()
        if (packet.hot && packet.t >= 0.98 && Math.random() < 0.35) {
          const next = edges.filter(([p, q]) => (p === packet.b || q === packet.b) && p !== packet.a && q !== packet.a)
          const pick = next[Math.floor(Math.random() * next.length)]
          if (pick) this.packets.push({ a: packet.b, b: pick[0] === packet.b ? pick[1] : pick[0], t: 0, speed: packet.speed * 0.9, hot: true })
        }
      }
      ctx.lineWidth = 0.6
    }
    // 少数节点挂着公式与代码片段：信息化、智能化的低语。
    ctx.font = '400 10px ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace'
    points.forEach((point, index) => {
      if (index % 9 !== 4) return
      const text = GLOSSES[(index / 9 | 0) % GLOSSES.length]!
      const glow = Math.max(0, 1 - point.d / 200) * mouse.presence
      ctx.fillStyle = `rgb(${glow > 0.2 ? this.accentCss : this.inkCss} / ${((0.16 + glow * 0.5) * intensity).toFixed(3)})`
      ctx.fillText(text, point.x + 7, point.y - 6)
    })
    for (const point of points) {
      const pulse = 0.5 + 0.5 * Math.sin(time * 1.4 + point.node.phase)
      const glow = Math.max(0, 1 - point.d / 220) * mouse.presence
      const alpha = (0.28 + pulse * 0.16 + glow * 0.5) * intensity
      if (point.node.sensor) {
        const size = 3.2 + glow * 2
        ctx.strokeStyle = `rgb(${this.accentCss} / ${Math.min(1, alpha + 0.12).toFixed(3)})`
        ctx.lineWidth = 0.9
        ctx.strokeRect(point.x - size / 2, point.y - size / 2, size, size)
      } else {
        ctx.fillStyle = `rgb(${glow > 0.25 ? this.accentCss : this.inkCss} / ${alpha.toFixed(3)})`
        ctx.beginPath()
        ctx.arc(point.x, point.y, 1.25 + glow * 1.4, 0, Math.PI * 2)
        ctx.fill()
      }
    }
    if (mouse.presence < 0.02) return
    // 注意力：光标与最近的节点相连，脉冲沿连线传递。
    const nearest = points.filter((point) => point.d < 300).sort((a, b) => a.d - b.d).slice(0, 6)
    ctx.lineWidth = 0.75
    nearest.forEach((point, index) => {
      const alpha = (1 - point.d / 300) * 0.42 * mouse.presence * intensity
      ctx.strokeStyle = `rgb(${this.accentCss} / ${alpha.toFixed(3)})`
      ctx.setLineDash([2, 4])
      ctx.beginPath()
      ctx.moveTo(mouse.x, mouse.y)
      ctx.lineTo(point.x, point.y)
      ctx.stroke()
      ctx.setLineDash([])
      const travel = (time * 0.55 + index * 0.17) % 1
      ctx.fillStyle = `rgb(${this.accentCss} / ${(alpha * 1.8).toFixed(3)})`
      ctx.beginPath()
      ctx.arc(point.x + (mouse.x - point.x) * travel, point.y + (mouse.y - point.y) * travel, 1.4, 0, Math.PI * 2)
      ctx.fill()
    })
    const cross = this.smooth.crosshair * mouse.presence * intensity
    if (cross < 0.02) return
    ctx.strokeStyle = `rgb(${this.inkCss} / ${(0.24 * cross).toFixed(3)})`
    ctx.lineWidth = 0.7
    ctx.setLineDash([1, 5])
    ctx.beginPath()
    ctx.moveTo(0, mouse.y); ctx.lineTo(width, mouse.y)
    ctx.moveTo(mouse.x, 0); ctx.lineTo(mouse.x, height)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.strokeStyle = `rgb(${this.accentCss} / ${(0.95 * cross).toFixed(3)})`
    ctx.lineWidth = 1.1
    ctx.beginPath()
    ctx.arc(mouse.x, mouse.y, 9, 0, Math.PI * 2)
    ctx.stroke()
    ctx.fillStyle = `rgb(${this.accentCss} / ${(0.95 * cross).toFixed(3)})`
    ctx.beginPath()
    ctx.arc(mouse.x, mouse.y, 1.6, 0, Math.PI * 2)
    ctx.fill()
    ctx.font = '600 11px ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace'
    ctx.fillStyle = `rgb(${this.inkCss} / ${(0.9 * cross).toFixed(3)})`
    const label = `X ${String(Math.round((mouse.x / width) * 1000)).padStart(4, '0')}  Y ${String(Math.round((mouse.y / height) * 1000)).padStart(4, '0')}`
    const flip = mouse.x > width - 150
    ctx.textAlign = flip ? 'right' : 'left'
    ctx.fillText(label, mouse.x + (flip ? -16 : 16), mouse.y - 12)
    ctx.textAlign = 'left'
  }

  /** 三维层画在独立画布上，只在首页挂载。 */
  attachScene(canvas: HTMLCanvasElement | null) {
    this.sceneCanvas = canvas
    this.scene = canvas ? new Scene3D(canvas) : null
    if (this.scene) {
      this.scene.colors(this.inkCss, this.accentCss, document.documentElement.dataset.theme === 'dark')
      this.scene.resize(this.width, this.height, this.uiDpr * (this.width < 760 ? 1 : 0.9))
    }
  }

  private drawScene(time: number, dt: number) {
    const weights = this.options.scene
    if (!this.scene || !this.sceneCanvas) return
    if (!weights) {
      if (this.sceneVisible) { this.sceneCanvas.getContext('2d')?.clearRect(0, 0, this.sceneCanvas.width, this.sceneCanvas.height); this.sceneVisible = false }
      return
    }
    this.sceneVisible = true
    this.scene.setWeights(weights)
    this.scene.pointer(this.mouse.x, this.mouse.y, this.mouse.presence)
    this.scene.draw(time, dt, this.reduced)
  }

  destroy() {
    this.stopLoop()
    const lose = this.gl?.getExtension('WEBGL_lose_context')
    lose?.loseContext()
  }
}
