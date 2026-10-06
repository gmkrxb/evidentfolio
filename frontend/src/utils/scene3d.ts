/**
 * 首页三维背景：以透视投影的线框 / 点云绘制，随滚动在六个「章节」之间过渡：
 *   序 · 地形与斜拉桥（力学、物联网上行）     宣言 · 地球与数据传输
 *   方法 · CNN / MLP / RNN 架构                 证据 · 损失曲面与梯度下降
 *   作品 · 代码与公式云                         方向 · 知识图谱
 * 纯 Canvas 2D 实现，无第三方依赖；鼠标改变视角、抬升地形、点亮附近元素。
 */
import { City3D } from './city3d'
import { Neural3D } from './neural3d'
import { Globe3D } from './globe3d'

export type SceneWeights = Record<'intro' | 'manifesto' | 'capabilities' | 'agents' | 'overview' | 'featured' | 'directions' | 'connect', number>

type V3 = { x: number; y: number; z: number }
type Proj = { x: number; y: number; z: number; k: number; visible: boolean }
type View = { yaw: number; pitch: number; dist: number; cx: number; cy: number; f: number; scale: number; lift: number }

const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v))
const smooth = (v: number) => { const t = clamp(v); return t * t * (3 - 2 * t) }

function rng(seed: number) {
  let s = seed >>> 0
  return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296)
}

const CODE = [
  'loss.backward()', 'optimizer.step()', 'model = Transformer(d=512, h=8)', 'for x, y in loader:', 'z = torch.fft.rfft(window)',
  'mqtt.publish("bridge/A3/acc", z)', 'SELECT avg(acc) FROM sensors INTERVAL(1s)', 'docker compose up -d', 'git commit -m "evidence"',
  'async def infer(req): ...', 'conv = nn.Conv1d(1, 64, 7)', 'h, c = lstm(x, (h, c))', 'retriever.search(q, k=8)', 'kubectl rollout status',
  'ws.send(json.dumps(frame))', 'fit(epochs=100, lr=3e-4)',
]
const FORMULAS = [
  'softmax(QKᵀ/√d)·V', '∂L/∂w = δ · xᵀ', 'θ ← θ − η∇L(θ)', 'hₜ = tanh(Wₕhₜ₋₁ + Wₓxₜ)', 'y = σ(W ∗ x + b)', 'L = −Σ y·log ŷ',
  'K·u = f', 'σ = M·y / I', 'EI·w⁗ = q(x)', 'p(y | x, evidence)', 'IoU = |A∩B| / |A∪B|', 'X(f) = Σ x[n]e^{−j2πfn/N}',
]
const GRAPH_WORDS = ['结构', '荷载', '传感', '模型', '证据', '推理', '数据', '图谱', 'BIM', 'IoT', 'LLM', 'RAG', '诗', '理']

export class Scene3D {
  private ctx: CanvasRenderingContext2D | null
  private width = 0
  private height = 0
  private dpr = 1
  private mobile = false
  private ink = '30 29 26'
  private accent = '201 106 72'
  private dark = false
  private weights: SceneWeights = { intro: 1, manifesto: 0, capabilities: 0, agents: 0, overview: 0, featured: 0, directions: 0, connect: 0 }
  private smoothW: SceneWeights = { ...this.weights }
  private mouse = { x: 0, y: 0, nx: 0, ny: 0, presence: 0 }
  private terrain: { nx: number; nz: number; base: Float32Array } = { nx: 0, nz: 0, base: new Float32Array() }
  private city = new City3D()
  /** 把数据中心、斜拉桥与城市串起来的道路（含沿路光缆）与谷底河流 */
  private road: { points: V3[]; lengths: number[]; total: number; bridge: [number, number] } = { points: [], lengths: [], total: 0, bridge: [0, 0] }
  private river: V3[] = []
  private neural = new Neural3D()
  private globe = new Globe3D()
  private paper = '243 239 231'
  private cloud: Array<{ x: number; y: number; z: number; text: string; formula: boolean }> = []
  private graph: { nodes: Array<V3 & { label?: string }>; edges: Array<[number, number]> } = { nodes: [], edges: [] }
  private ball = { x: 2.6, y: 2.2, vx: 0, vy: 0, trail: [] as V3[], losses: [] as number[], rest: 0 }
  private random = rng(2027)

  constructor(private canvas: HTMLCanvasElement) {
    this.ctx = canvas.getContext('2d')
  }

  resize(width: number, height: number, dpr: number) {
    this.width = width
    this.height = height
    this.dpr = Math.min(dpr, 2)
    this.mobile = width < 760
    this.canvas.width = Math.round(width * this.dpr)
    this.canvas.height = Math.round(height * this.dpr)
    this.build()
  }

  colors(ink: string, accent: string, dark: boolean) {
    this.ink = ink
    this.accent = accent
    this.dark = dark
    // 实体面用页面底色填充，以遮住身后的线条。
    const probe = document.createElement('canvas').getContext('2d')
    if (probe) {
      probe.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-bg').trim() || '#f3efe7'
      const value = String(probe.fillStyle)
      if (value.startsWith('#')) this.paper = [1, 3, 5].map((i) => parseInt(value.slice(i, i + 2), 16)).join(' ')
      else this.paper = (value.match(/[\d.]+/g) || ['243', '239', '231']).slice(0, 3).join(' ')
    }
  }

  setWeights(weights: SceneWeights) { this.weights = weights }

  pointer(x: number, y: number, presence: number) {
    this.mouse.x = x
    this.mouse.y = y
    this.mouse.presence = presence
  }

  // —— 几何构建 ——
  private build() {
    const random = rng(7)
    const nx = this.mobile ? 34 : 58, nz = this.mobile ? 18 : 28
    const base = new Float32Array(nx * nz)
    for (let j = 0; j < nz; j++) {
      for (let i = 0; i < nx; i++) {
        const x = -1100 + (i / (nx - 1)) * 2200
        const z = (j / (nz - 1)) * 1700
        const valley = Math.pow(clamp(Math.abs(x) / 760), 1.5)
        const n1 = 0.5 + 0.5 * Math.sin(x * 0.0042 + z * 0.0031) * Math.cos(z * 0.0052 - x * 0.0021)
        const n2 = Math.sin(x * 0.013 + z * 0.011) * Math.sin(z * 0.009 + 1.3)
        base[j * nx + i] = 20 + valley * 300 * (0.55 + 0.45 * n1) + n2 * 26 + (z / 1700) * 120 * valley
      }
    }
    this.terrain = { nx, nz, base }
    // 为城市与数据中心整平场地，再在平整后的地面上布置建筑。
    const pads = [
      { x0: 380, x1: 1030, z0: -560, z1: 140 },
      { x0: this.mobile ? -900 : -910, x1: -470, z0: -560, z1: -120 },
    ]
    for (const pad of pads) {
      let sum = 0, count = 0
      for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
        const x = -1100 + (i / (nx - 1)) * 2200, z = (j / (nz - 1)) * 1700 - 700
        if (x >= pad.x0 && x <= pad.x1 && z >= pad.z0 && z <= pad.z1) { sum += base[j * nx + i]!; count++ }
      }
      const level = count ? sum / count * 0.85 : 150
      for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
        const x = -1100 + (i / (nx - 1)) * 2200, z = (j / (nz - 1)) * 1700 - 700
        const dx = Math.max(pad.x0 - x, 0, x - pad.x1), dz = Math.max(pad.z0 - z, 0, z - pad.z1)
        const t = clamp(1 - Math.hypot(dx, dz) / 140)
        base[j * nx + i] = base[j * nx + i]! * (1 - t) + level * t
      }
    }
    this.city.build(this.mobile, (x, z) => this.heightAt(x, z + 700) - 170)
    this.buildNetwork()
    const items = [...CODE, ...FORMULAS]
    this.cloud = Array.from({ length: this.mobile ? 18 : 34 }, (_, k) => ({
      x: (random() - 0.5) * 2000, y: (random() - 0.5) * 1000, z: random() * 2000, text: items[k % items.length]!, formula: k % items.length >= CODE.length,
    }))
    const nodes: Array<V3 & { label?: string }> = Array.from({ length: this.mobile ? 30 : 48 }, (_, k) => {
      const u = random() * 2 - 1, a = random() * Math.PI * 2, r = 230 + random() * 70
      const s = Math.sqrt(1 - u * u)
      return { x: Math.cos(a) * s * r, y: u * r, z: Math.sin(a) * s * r, label: k < GRAPH_WORDS.length ? GRAPH_WORDS[k] : undefined }
    })
    const edges: Array<[number, number]> = []
    nodes.forEach((a, i) => {
      nodes.map((b, j) => ({ j, d: Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z) })).filter((e) => e.j !== i).sort((p, q) => p.d - q.d).slice(0, 3)
        .forEach(({ j }) => { if (i < j) edges.push([i, j]) })
    })
    this.graph = { nodes, edges }
  }

  /**
   * 道路：数据中心门前 → 沿左岸 → 爬上引桥 → 斜拉桥面 → 右岸引桥 → 城市主街。
   * 光缆沿路敷设，桥上的传感器数据沿它流回机房，机房再把结果送进城市。
   */
  private buildNetwork() {
    const ground = (x: number, z: number) => this.heightAt(x, z + 700) - 170 + 2
    const hall = this.city.hall
    const deckY = -40, deckZ = -107
    const left: Array<[number, number]> = [[hall.x + hall.w * 0.35, hall.z - 18], [hall.x + hall.w + 30, hall.z - 18], [-500, -190], [-470, deckZ]]
    const right: Array<[number, number]> = [[470, deckZ], [520, -150], [700, -158], [940, -150]]
    const points: V3[] = []
    const push = (x: number, y: number, z: number) => points.push({ x, y, z })
    const segment = (a: [number, number], b: [number, number], steps: number, yOf: (t: number, x: number, z: number) => number) => {
      for (let k = 0; k < steps; k++) {
        const t = k / steps, x = a[0] + (b[0] - a[0]) * t, z = a[1] + (b[1] - a[1]) * t
        push(x, yOf(t, x, z), z)
      }
    }
    for (let k = 0; k < left.length - 2; k++) segment(left[k]!, left[k + 1]!, 14, (_, x, z) => ground(x, z))
    // 引桥：从地面平滑过渡到桥面高度
    const ramp = (t: number) => t * t * (3 - 2 * t)
    const startY = ground(-500, -190)
    segment(left[2]!, left[3]!, 10, (t) => startY + (deckY - startY) * ramp(t))
    segment([-470, deckZ], [-430, deckZ], 2, () => deckY)
    const bridgeStart = points.length
    segment([-430, deckZ], [430, deckZ], 40, () => deckY)
    const bridgeEnd = points.length
    segment([430, deckZ], [470, deckZ], 2, () => deckY)
    const endY = ground(520, -150)
    segment(right[0]!, right[1]!, 10, (t) => deckY + (endY - deckY) * ramp(t))
    segment(right[1]!, right[2]!, 12, (_, x, z) => ground(x, z))
    segment(right[2]!, right[3]!, 14, (_, x, z) => ground(x, z))
    push(right[3]![0], ground(right[3]![0], right[3]![1]), right[3]![1])
    const lengths = [0]
    for (let k = 1; k < points.length; k++) {
      const a = points[k - 1]!, b = points[k]!
      lengths.push(lengths[k - 1]! + Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z))
    }
    this.road = { points, lengths, total: lengths[lengths.length - 1]!, bridge: [bridgeStart, bridgeEnd] }
    // 谷底河流：沿 z 方向蜿蜒穿过桥下
    this.river = Array.from({ length: 60 }, (_, k) => {
      const z = -700 + (k / 59) * 1700
      const x = Math.sin(z * 0.0035 + 0.6) * 46
      return { x, y: this.heightAt(x, z + 700) - 170 + 1, z }
    })
  }

  /** 沿道路按弧长取点（u ∈ [0, 1]），offset 为垂直于道路的水平偏移。 */
  private along(u: number, offset = 0): V3 {
    const { points, lengths, total } = this.road
    const target = clamp(u) * total
    let k = 1
    while (k < lengths.length - 1 && lengths[k]! < target) k++
    const a = points[k - 1]!, b = points[k]!
    const span = (lengths[k]! - lengths[k - 1]!) || 1
    const t = (target - lengths[k - 1]!) / span
    const dx = b.x - a.x, dz = b.z - a.z, len = Math.hypot(dx, dz) || 1
    return { x: a.x + dx * t - (dz / len) * offset, y: a.y + (b.y - a.y) * t, z: a.z + dz * t + (dx / len) * offset }
  }

  private heightAt(x: number, z: number) {
    const { nx, nz, base } = this.terrain
    const i = clamp(Math.round(((x + 1100) / 2200) * (nx - 1)), 0, nx - 1)
    const j = clamp(Math.round((z / 1700) * (nz - 1)), 0, nz - 1)
    return base[j * nx + i] || 0
  }

  private sphere(lat: number, lon: number, r: number): V3 {
    const phi = (lat * Math.PI) / 180, lam = (lon * Math.PI) / 180
    return { x: r * Math.cos(phi) * Math.sin(lam), y: r * Math.sin(phi), z: r * Math.cos(phi) * Math.cos(lam) }
  }

  // —— 投影 ——
  private project(p: V3, v: View): Proj {
    const cy = Math.cos(v.yaw), sy = Math.sin(v.yaw), cp = Math.cos(v.pitch), sp = Math.sin(v.pitch)
    const x1 = p.x * cy + p.z * sy
    const z1 = -p.x * sy + p.z * cy
    const y2 = p.y * cp - z1 * sp
    const z2 = p.y * sp + z1 * cp
    const depth = z2 + v.dist
    if (depth < 40) return { x: 0, y: 0, z: depth, k: 0, visible: false }
    const k = (v.f / depth) * v.scale
    return { x: v.cx + x1 * k, y: v.cy - y2 * k + v.lift, z: depth, k, visible: true }
  }

  private rgba(color: 'ink' | 'accent', alpha: number) {
    return `rgb(${color === 'ink' ? this.ink : this.accent} / ${clamp(alpha).toFixed(3)})`
  }

  // —— 主循环入口 ——
  draw(time: number, dt: number, reduced: boolean) {
    const ctx = this.ctx
    if (!ctx || !this.width) return
    const ease = 1 - Math.exp(-dt * 4)
    for (const key of Object.keys(this.weights) as Array<keyof SceneWeights>) {
      this.smoothW[key] += (this.weights[key] - this.smoothW[key]) * (reduced ? 1 : ease)
    }
    const m = this.mouse
    m.nx += ((m.x / (this.width || 1) - 0.5) * m.presence - m.nx) * (1 - Math.exp(-dt * 3))
    m.ny += ((m.y / (this.height || 1) - 0.5) * m.presence - m.ny) * (1 - Math.exp(-dt * 3))
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0)
    ctx.clearRect(0, 0, this.width, this.height)
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    const strength = this.dark ? 0.95 : 0.8
    // 手机上文字与背景挨得更近，正文区段的背景再淡一些。
    const quiet = this.mobile ? 0.55 : 1
    const w = this.smoothW
    const terrain = Math.max(w.intro, w.connect * 0.9)
    if (terrain > 0.01) {
      this.drawTerrain(ctx, time, smooth(terrain) * strength)
      // 地形只占画面下部：上半部分逐渐擦除，避免穿过标题。
      ctx.save()
      ctx.globalCompositeOperation = 'destination-out'
      const top = this.height * (this.mobile ? 0.5 : 0.36), bottom = this.height * (this.mobile ? 0.72 : 0.62)
      const fade = ctx.createLinearGradient(0, top, 0, bottom)
      fade.addColorStop(0, 'rgba(0,0,0,1)')
      fade.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = 'rgba(0,0,0,1)'
      ctx.fillRect(0, 0, this.width, top)
      ctx.fillStyle = fade
      ctx.fillRect(0, top, this.width, bottom - top)
      ctx.restore()
    }
    if (w.manifesto > 0.01) this.drawGlobe(ctx, time, smooth(w.manifesto) * strength * (this.mobile ? 0.7 : 1))
    if (w.capabilities > 0.01) this.drawNetwork(ctx, time, smooth(w.capabilities) * strength)
    if (w.agents > 0.01) this.drawAgents(ctx, time, smooth(w.agents) * strength * 0.8 * quiet)
    if (w.overview > 0.01) this.drawLoss(ctx, time, dt, smooth(w.overview) * strength * 0.75 * quiet, reduced)
    if (w.featured > 0.01) this.drawCloud(ctx, time, dt, smooth(w.featured) * strength * quiet, reduced)
    if (w.directions > 0.01) this.drawGraph(ctx, time, smooth(w.directions) * strength * 0.7 * quiet)
  }

  private label(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, alpha: number, accent = false, size = 11) {
    ctx.font = `500 ${size}px ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace`
    ctx.fillStyle = this.rgba(accent ? 'accent' : 'ink', alpha)
    ctx.fillText(text, x, y)
  }

  // —— 一 · 地形、斜拉桥、城市与物联网上行 ——
  private drawTerrain(ctx: CanvasRenderingContext2D, time: number, alpha: number) {
    const { nx, nz, base } = this.terrain
    const m = this.mouse
    const view: View = {
      yaw: -0.16 + m.nx * 0.32 + Math.sin(time * 0.05) * 0.04, pitch: -0.4 - m.ny * 0.08, dist: 2050,
      cx: this.width * (this.mobile ? 0.5 : 0.55), cy: this.height * (this.mobile ? 0.82 : 0.8), f: this.height * (this.mobile ? 1.3 : 1.04), scale: 0.9 + 0.1 * alpha, lift: (1 - alpha) * 60,
    }
    const at = (i: number, j: number, extra = 0): V3 => ({ x: -1100 + (i / (nx - 1)) * 2200, y: base[j * nx + i]! - 170 + extra + Math.sin(j * 0.6 - time * 0.7) * 3, z: (j / (nz - 1)) * 1700 - 700 })
    const projected: Proj[] = new Array(nx * nz)
    for (let j = 0; j < nz; j++) {
      for (let i = 0; i < nx; i++) {
        let p = this.project(at(i, j), view)
        if (m.presence > 0.05 && p.visible) {
          const d = Math.hypot(p.x - m.x, p.y - m.y)
          if (d < 170) p = this.project(at(i, j, (1 - d / 170) ** 2 * 90 * m.presence), view)
        }
        projected[j * nx + i] = p
      }
    }
    // 等高“行线”：近处更实，远处融进雾里；离光标近的段落染为陶土色。
    for (let j = 0; j < nz; j++) {
      const fog = 1 - j / nz
      ctx.strokeStyle = this.rgba('ink', alpha * (0.06 + fog * 0.26))
      ctx.lineWidth = 0.6 + fog * 0.5
      ctx.beginPath()
      for (let i = 0; i < nx; i++) {
        const p = projected[j * nx + i]!
        if (i) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y)
      }
      ctx.stroke()
    }
    ctx.strokeStyle = this.rgba('ink', alpha * 0.07)
    ctx.lineWidth = 0.5
    ctx.beginPath()
    for (let i = 0; i < nx; i += 2) {
      for (let j = 0; j < nz; j++) {
        const p = projected[j * nx + i]!
        if (j) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y)
      }
    }
    ctx.stroke()
    if (m.presence > 0.05) {
      ctx.strokeStyle = this.rgba('accent', alpha * 0.55 * m.presence)
      ctx.lineWidth = 1
      for (let j = 0; j < nz; j++) {
        ctx.beginPath()
        let open = false
        for (let i = 0; i < nx; i++) {
          const p = projected[j * nx + i]!
          const near = Math.hypot(p.x - m.x, p.y - m.y) < 120
          if (near) { if (open) ctx.lineTo(p.x, p.y); else { ctx.moveTo(p.x, p.y); open = true } } else open = false
        }
        ctx.stroke()
      }
    }

    // 斜拉桥：桥面、双塔、扇形拉索，车辆往返，传感器上行。
    const deckZ = -120, deckY = -40
    const P = (x: number, y: number, z: number) => this.project({ x, y, z }, view)
    // 谷底河流：两岸与缓慢流动的水纹
    if (this.river.length) {
      // 水面：两岸之间的淡色填充，遮住身后的地形线
      ctx.beginPath()
      this.river.forEach((r, k) => { const p = P(r.x - 22, r.y, r.z); if (k) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y) })
      for (let k = this.river.length - 1; k >= 0; k--) { const r = this.river[k]!; const p = P(r.x + 22, r.y, r.z); ctx.lineTo(p.x, p.y) }
      ctx.closePath()
      ctx.fillStyle = `rgb(${this.paper} / ${clamp(alpha * 0.85).toFixed(3)})`
      ctx.fill()
      ctx.fillStyle = this.rgba('accent', alpha * 0.07)
      ctx.fill()
      for (const side of [-1, 1]) {
        ctx.strokeStyle = this.rgba('ink', alpha * 0.36)
        ctx.lineWidth = 0.9
        ctx.beginPath()
        this.river.forEach((r, k) => { const p = P(r.x + side * 22, r.y, r.z); if (k) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y) })
        ctx.stroke()
      }
      ctx.strokeStyle = this.rgba('accent', alpha * 0.35)
      ctx.lineWidth = 0.8
      ctx.setLineDash([3, 14])
      ctx.lineDashOffset = -time * 18
      for (const lane of [-9, 6]) {
        ctx.beginPath()
        this.river.forEach((r, k) => { const p = P(r.x + lane, r.y, r.z); if (k) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y) })
        ctx.stroke()
      }
      ctx.setLineDash([]); ctx.lineDashOffset = 0
    }
    const line = (a: Proj, b: Proj) => { ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y) }
    ctx.strokeStyle = this.rgba('ink', alpha * 0.62)
    ctx.lineWidth = 1.3
    ctx.beginPath()
    line(P(-430, deckY, deckZ), P(430, deckY, deckZ))
    line(P(-430, deckY, deckZ + 26), P(430, deckY, deckZ + 26))
    for (const tx of [-180, 180]) {
      for (const dz of [0, 26]) line(P(tx, -150, deckZ + dz), P(tx, 210, deckZ + 13))
    }
    ctx.stroke()
    ctx.strokeStyle = this.rgba('ink', alpha * 0.24)
    ctx.lineWidth = 0.7
    ctx.beginPath()
    for (const tx of [-180, 180]) {
      for (let k = 0; k < (this.mobile ? 6 : 10); k++) {
        const top = P(tx, 200 - k * 9, deckZ + 13)
        for (const side of [-1, 1]) {
          const dx = tx + side * (34 + k * 22)
          if (Math.abs(dx) > 430) continue
          line(top, P(dx, deckY, deckZ + 13))
        }
      }
    }
    ctx.stroke()
    // 道路：机房 → 引桥 → 桥面 → 城市主街，双线路缘 + 中线
    const road = this.road
    if (road.points.length) {
      const edge = (offset: number) => {
        ctx.beginPath()
        road.points.forEach((_, k) => {
          const u = road.lengths[k]! / road.total
          const q = this.along(u, offset)
          const p = P(q.x, q.y, q.z)
          if (k) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y)
        })
        ctx.stroke()
      }
      ctx.strokeStyle = this.rgba('ink', alpha * 0.52)
      ctx.lineWidth = 1
      edge(-11); edge(11)
      ctx.strokeStyle = this.rgba('ink', alpha * 0.22)
      ctx.setLineDash([6, 8])
      edge(0)
      ctx.setLineDash([])
      // 引桥桥墩
      ctx.strokeStyle = this.rgba('ink', alpha * 0.35)
      ctx.beginPath()
      for (const u of [0.24, 0.27, 0.73, 0.76]) {
        const top = this.along(u)
        const g = this.heightAt(top.x, top.z + 700) - 170
        if (top.y - g < 8) continue
        const a = P(top.x, top.y, top.z), b = P(top.x, g, top.z)
        ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y)
      }
      ctx.stroke()
      // 沿路光缆：虚线 + 数据包。桥上传感器的数据流回机房，机房的结果送进城市。
      ctx.strokeStyle = this.rgba('accent', alpha * 0.32)
      ctx.lineWidth = 0.8
      ctx.setLineDash([2, 4])
      edge(17)
      ctx.setLineDash([])
      const bridgeU = [road.lengths[road.bridge[0]]! / road.total, road.lengths[road.bridge[1]]! / road.total]
      for (let k = 0; k < (this.mobile ? 5 : 9); k++) {
        const toCity = k % 3 === 0
        const f = ((time * (toCity ? 0.07 : 0.09) + k * 0.137) % 1 + 1) % 1
        // 回机房的数据包：从桥面某处出发，沿路向左；送城市的：从机房出发向右
        const startU = toCity ? 0.02 : bridgeU[0]! + (bridgeU[1]! - bridgeU[0]!) * ((k * 0.31) % 1)
        const u = toCity ? startU + (1 - startU) * f : startU * (1 - f)
        const q = this.along(u, 17)
        const p = P(q.x, q.y + 2, q.z)
        ctx.fillStyle = this.rgba('accent', alpha * 0.95)
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.9, 0, Math.PI * 2); ctx.fill()
      }
      // 车辆沿整条道路往返
      for (let k = 0; k < (this.mobile ? 4 : 7); k++) {
        const f = ((time * (0.018 + (k % 3) * 0.004) + k * 0.19) % 1 + 1) % 1
        const forward = k % 2 === 0
        const q = this.along(forward ? f : 1 - f, forward ? -5 : 5)
        const p = P(q.x, q.y + 4, q.z)
        ctx.fillStyle = this.rgba(k === 1 ? 'accent' : 'ink', alpha * 0.85)
        ctx.fillRect(p.x - 3, p.y - 2, 6, 3)
      }
    }
    // 桥上的传感器：振动脉冲
    const sensors = [-330, -180, 0, 180, 330]
    sensors.forEach((x, k) => {
      const base = P(x, deckY, deckZ + 13)
      const phase = ((time * 0.6 + k * 0.21) % 1 + 1) % 1
      ctx.strokeStyle = this.rgba('accent', alpha * 0.6 * (1 - phase))
      ctx.lineWidth = 0.9
      ctx.beginPath(); ctx.arc(base.x, base.y, 3 + phase * 18, 0, Math.PI * 2); ctx.stroke()
      ctx.fillStyle = this.rgba('accent', alpha * 0.9)
      ctx.beginPath(); ctx.arc(base.x, base.y, 1.6, 0, Math.PI * 2); ctx.fill()
    })
    const hubPoint = P(this.city.hub.x, this.city.hub.y + 30, this.city.hub.z)
    if (!this.mobile) this.label(ctx, 'IoT → edge DC · 20 Hz', hubPoint.x - 40, hubPoint.y - 8, alpha * 0.6, true)
    // 城市、塔吊与数据中心（实体三维，按深度遮挡）
    const cy = Math.cos(view.yaw), sy = Math.sin(view.yaw), cp = Math.cos(view.pitch), sp = Math.sin(view.pitch)
    const cam = { x: view.dist * cp * sy, y: -view.dist * sp, z: -view.dist * cp * cy }
    this.city.draw(ctx, (point) => this.project(point, view), cam, time, {
      ink: (a) => this.rgba('ink', a),
      accent: (a) => this.rgba('accent', a),
      paper: (a) => `rgb(${this.paper} / ${clamp(a).toFixed(3)})`,
    }, alpha)
    if (!this.mobile) {
      const t = P(180, 230, deckZ + 13)
      this.label(ctx, 'σ = M·y / I', t.x + 10, t.y, alpha * 0.55)
      const g = P(-760, 160, 300)
      this.label(ctx, 'K·u = f', g.x, g.y, alpha * 0.45)
    }
  }

  // —— 二 · 互联的地球 ——
  private drawGlobe(ctx: CanvasRenderingContext2D, time: number, alpha: number) {
    const m = this.mouse
    const view: View = {
      yaw: -2.0 + time * 0.06 + m.nx * 0.9, pitch: -0.24 - m.ny * 0.16, dist: 1250,
      cx: this.width * (this.mobile ? 0.62 : 0.74), cy: this.height * (this.mobile ? 0.3 : 0.52), f: Math.min(this.width, this.height) * (this.mobile ? 0.72 : 1.18), scale: 0.85 + 0.15 * alpha, lift: (1 - alpha) * 50,
    }
    const cp = Math.cos(view.pitch), sp = Math.sin(view.pitch), cy = Math.cos(view.yaw), sy = Math.sin(view.yaw)
    const cam = { x: view.dist * cp * sy, y: -view.dist * sp, z: -view.dist * cp * cy }
    this.globe.draw(ctx, (p) => this.project(p, view), cam, time, alpha, m, this.mobile, {
      ink: (a) => this.rgba('ink', a),
      accent: (a) => this.rgba('accent', a),
      label: (text, x, y, a, accent, size) => this.label(ctx, text, x, y, a, accent, size),
    })
  }

  // —— 三 · 深层网络走廊 ——
  private drawNetwork(ctx: CanvasRenderingContext2D, time: number, alpha: number) {
    const m = this.mouse
    // 桌面端：能力卡片占据了视口中部，网络改为标题右侧的一条横向长带（侧视，输入在左、输出在右）
    const band = !this.mobile && this.width >= 900
    const view: View = band
      ? {
          yaw: 1.08 + m.nx * 0.1 + Math.sin(time * 0.07) * 0.03, pitch: 0.12 + m.ny * 0.06, dist: 2900,
          cx: this.width * 0.665, cy: Math.max(185, this.height * 0.245), f: this.height * 1.3, scale: 1, lift: 0,
        }
      : {
          yaw: -0.94 + m.nx * 0.35 + Math.sin(time * 0.07) * 0.08, pitch: 0.3 + m.ny * 0.16, dist: this.mobile ? 3600 : 2900,
          cx: this.width * (this.mobile ? 0.5 : 0.46), cy: this.height * 0.54, f: Math.min(this.width, this.height) * (this.mobile ? 2.3 : 2.2), scale: 0.88 + 0.12 * alpha, lift: (1 - alpha) * 50,
        }
    this.neural.draw(ctx, (p) => this.project(p, view), time, alpha, m, this.mobile, {
      ink: (a) => this.rgba('ink', a),
      accent: (a) => this.rgba('accent', a),
      label: (text, x, y, a, accent, size) => { if (!this.mobile || (size || 11) > 9) this.label(ctx, text, x, y, a, accent, size) },
      paper: (a) => `rgb(${this.paper} / ${clamp(a).toFixed(3)})`,
    }, band)
  }

  // —— 三½ · 智能体消息总线：倾斜的同心轨道上，消息胶囊绕行并在轨道间跃迁 ——
  private drawAgents(ctx: CanvasRenderingContext2D, time: number, alpha: number) {
    const m = this.mouse
    const view: View = {
      yaw: time * 0.05 + m.nx * 0.5, pitch: -0.55 - m.ny * 0.2, dist: 1400,
      cx: this.width * 0.5, cy: this.height * 0.55, f: Math.min(this.width, this.height) * 1.3, scale: 0.9 + 0.1 * alpha, lift: (1 - alpha) * 40,
    }
    const P = (p: V3) => this.project(p, view)
    const rings = [220, 330, 450, 580]
    rings.forEach((r, i) => {
      ctx.strokeStyle = this.rgba(i === 1 ? 'accent' : 'ink', alpha * (i === 1 ? 0.3 : 0.14))
      ctx.lineWidth = 0.8
      ctx.setLineDash(i % 2 ? [3, 7] : [])
      ctx.beginPath()
      for (let s = 0; s <= 120; s++) {
        const a = (s / 120) * Math.PI * 2
        const p = P({ x: Math.cos(a) * r, y: Math.sin(a * 3 + i) * 12, z: Math.sin(a) * r })
        if (s) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y)
      }
      ctx.stroke()
    })
    ctx.setLineDash([])
    for (let n = 0; n < 24; n++) {
      const ring = rings[n % rings.length]!
      const a = time * (0.25 + (n % 5) * 0.05) * (n % 2 ? 1 : -1) + n * 0.9
      const hop = Math.max(0, Math.sin(time * 0.8 + n)) ** 8
      const r = ring + hop * 110
      const p = P({ x: Math.cos(a) * r, y: Math.sin(a * 3) * 12 + hop * 80, z: Math.sin(a) * r })
      ctx.fillStyle = this.rgba(n % 4 === 0 ? 'accent' : 'ink', alpha * (0.4 + hop * 0.6))
      ctx.fillRect(p.x - 4 * p.k, p.y - 1.5 * p.k, 8 * p.k, 3 * p.k)
    }
  }

  // —— 四 · 损失曲面与梯度下降 ——
  private lossAt(x: number, y: number) {
    return 0.16 * (x * x + y * y) + 0.55 * Math.sin(1.3 * x) * Math.cos(1.1 * y) + 0.25 * Math.sin(2.1 * x + 0.7) * Math.sin(1.7 * y)
  }

  private drawLoss(ctx: CanvasRenderingContext2D, time: number, dt: number, alpha: number, reduced: boolean) {
    const m = this.mouse
    const view: View = {
      yaw: 0.6 + time * 0.06 + m.nx * 0.5, pitch: 0.55 + m.ny * 0.15, dist: 1300,
      cx: this.width * (this.mobile ? 0.5 : 0.72), cy: this.height * 0.56, f: Math.min(this.width, this.height) * 1.2, scale: 0.85 + 0.15 * alpha, lift: (1 - alpha) * 50,
    }
    const N = this.mobile ? 22 : 34, S = 3.2, scale = 110, heightScale = 90
    const point = (x: number, y: number): V3 => ({ x: x * scale, y: this.lossAt(x, y) * heightScale - 80, z: y * scale })
    ctx.lineWidth = 0.7
    for (let dir = 0; dir < 2; dir++) {
      for (let a = 0; a <= N; a++) {
        const u = -S + (a / N) * 2 * S
        ctx.strokeStyle = this.rgba('ink', alpha * (dir ? 0.1 : 0.2))
        ctx.beginPath()
        for (let b = 0; b <= N; b++) {
          const v = -S + (b / N) * 2 * S
          const p = this.project(dir ? point(v, u) : point(u, v), view)
          if (b) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y)
        }
        ctx.stroke()
      }
    }
    // 带动量的梯度下降
    const ball = this.ball
    if (!reduced) {
      const e = 1e-3
      const gx = (this.lossAt(ball.x + e, ball.y) - this.lossAt(ball.x - e, ball.y)) / (2 * e)
      const gy = (this.lossAt(ball.x, ball.y + e) - this.lossAt(ball.x, ball.y - e)) / (2 * e)
      const steps = Math.min(3, Math.round(dt * 60))
      for (let s = 0; s < steps; s++) {
        ball.vx = ball.vx * 0.9 - 0.012 * gx
        ball.vy = ball.vy * 0.9 - 0.012 * gy
        ball.x = clamp(ball.x + ball.vx, -S, S)
        ball.y = clamp(ball.y + ball.vy, -S, S)
      }
      ball.trail.push(point(ball.x, ball.y))
      ball.losses.push(this.lossAt(ball.x, ball.y))
      if (ball.trail.length > 160) ball.trail.shift()
      if (ball.losses.length > 160) ball.losses.shift()
      if (Math.hypot(gx, gy) < 0.04 && Math.hypot(ball.vx, ball.vy) < 0.002) ball.rest += dt
      if (ball.rest > 1.6) {
        ball.x = (this.random() * 2 - 1) * 2.9; ball.y = (this.random() * 2 - 1) * 2.9
        ball.vx = ball.vy = 0; ball.rest = 0; ball.trail = []; ball.losses = []
      }
    }
    ctx.strokeStyle = this.rgba('accent', alpha * 0.9)
    ctx.lineWidth = 1.4
    ctx.beginPath()
    ball.trail.forEach((p, k) => { const q = this.project({ ...p, y: p.y + 4 }, view); if (k) ctx.lineTo(q.x, q.y); else ctx.moveTo(q.x, q.y) })
    ctx.stroke()
    const head = this.project({ ...point(ball.x, ball.y), y: point(ball.x, ball.y).y + 6 }, view)
    ctx.fillStyle = this.rgba('accent', alpha)
    ctx.beginPath(); ctx.arc(head.x, head.y, 4.5, 0, Math.PI * 2); ctx.fill()
    ctx.strokeStyle = this.rgba('accent', alpha * 0.4)
    ctx.beginPath(); ctx.arc(head.x, head.y, 9 + Math.sin(time * 4) * 2, 0, Math.PI * 2); ctx.stroke()
    // 损失曲线
    if (ball.losses.length > 2) {
      const w = this.mobile ? 150 : 220, h = 64
      const x0 = this.mobile ? this.width - w - 20 : view.cx - w / 2, y0 = this.height - (this.mobile ? 150 : 170)
      const max = Math.max(...ball.losses), min = Math.min(...ball.losses)
      ctx.strokeStyle = this.rgba('ink', alpha * 0.35)
      ctx.lineWidth = 0.8
      ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0, y0 + h); ctx.lineTo(x0 + w, y0 + h); ctx.stroke()
      ctx.strokeStyle = this.rgba('accent', alpha * 0.9)
      ctx.lineWidth = 1.2
      ctx.beginPath()
      ball.losses.forEach((l, k) => {
        const x = x0 + (k / 159) * w, y = y0 + h - ((l - min) / (max - min || 1)) * h
        if (k) ctx.lineTo(x, y); else ctx.moveTo(x, y)
      })
      ctx.stroke()
      this.label(ctx, `loss ${ball.losses[ball.losses.length - 1]!.toFixed(3)}`, x0, y0 - 8, alpha * 0.7, true)
      if (!this.mobile) this.label(ctx, 'θ ← θ − η∇L(θ)', x0 + w - 108, y0 - 8, alpha * 0.55)
    }
  }

  // —— 五 · 代码与公式云 ——
  private drawCloud(ctx: CanvasRenderingContext2D, time: number, dt: number, alpha: number, reduced: boolean) {
    const m = this.mouse
    const view: View = { yaw: m.nx * 0.18, pitch: m.ny * 0.1, dist: 500, cx: this.width / 2, cy: this.height / 2, f: Math.min(this.width, this.height) * 0.9, scale: 1, lift: 0 }
    const projected = this.cloud.map((item) => {
      if (!reduced) {
        item.z -= dt * 90
        if (item.z < -380) { item.z += 2200; item.x = (this.random() - 0.5) * 2000; item.y = (this.random() - 0.5) * 1000 }
      }
      return { item, p: this.project(item, view) }
    })
    ctx.lineWidth = 0.6
    for (let i = 0; i < projected.length; i++) {
      for (let j = i + 1; j < projected.length; j++) {
        const a = projected[i]!, b = projected[j]!
        const d = Math.hypot(a.item.x - b.item.x, a.item.y - b.item.y, a.item.z - b.item.z)
        if (d > 520 || !a.p.visible || !b.p.visible) continue
        ctx.strokeStyle = this.rgba('ink', alpha * 0.08 * (1 - d / 520))
        ctx.beginPath(); ctx.moveTo(a.p.x, a.p.y); ctx.lineTo(b.p.x, b.p.y); ctx.stroke()
      }
    }
    for (const { item, p } of projected) {
      if (!p.visible) continue
      const fade = clamp((2000 - item.z) / 600) * clamp((item.z + 380) / 300)
      const near = m.presence > 0.05 && Math.hypot(p.x - m.x, p.y - m.y) < 110
      const size = clamp(11 * p.k * 1.4, 8, this.mobile ? 18 : 24)
      ctx.font = `${item.formula ? 'italic 400' : '500'} ${size.toFixed(1)}px ${item.formula ? 'ui-serif, Georgia, "Iowan Old Style", serif' : 'ui-monospace, "SFMono-Regular", Menlo, monospace'}`
      ctx.fillStyle = this.rgba(near || item.formula ? 'accent' : 'ink', alpha * fade * (near ? 0.95 : item.formula ? 0.55 : 0.4))
      ctx.fillText(item.text, p.x, p.y)
    }
    // 一行正在“编写”的代码
    if (!this.mobile) {
      const line = CODE[Math.floor(time / 4) % CODE.length]!
      const typed = line.slice(0, Math.floor(((time % 4) / 2.4) * line.length))
      this.label(ctx, `> ${typed}${Math.floor(time * 2) % 2 ? '▍' : ''}`, this.width * 0.06, this.height * 0.9, alpha * 0.6, true, 12)
    }
  }

  // —— 六 · 知识图谱 ——
  private drawGraph(ctx: CanvasRenderingContext2D, time: number, alpha: number) {
    const m = this.mouse
    const view: View = {
      yaw: time * 0.15 + m.nx * 0.8, pitch: 0.2 + m.ny * 0.3, dist: 1100,
      cx: this.width * (this.mobile ? 0.5 : 0.72), cy: this.height * 0.5, f: Math.min(this.width, this.height) * 1.2, scale: 0.85 + 0.15 * alpha, lift: (1 - alpha) * 50,
    }
    const projected = this.graph.nodes.map((node) => this.project(node, view))
    let hover = -1
    if (m.presence > 0.05) {
      let best = 40
      projected.forEach((p, k) => { const d = Math.hypot(p.x - m.x, p.y - m.y); if (d < best) { best = d; hover = k } })
    }
    const center = this.project({ x: 0, y: 0, z: 0 }, view)
    ctx.lineWidth = 0.7
    for (const [a, b] of this.graph.edges) {
      const p = projected[a]!, q = projected[b]!
      const lit = a === hover || b === hover
      const depth = clamp((center.z + 300 - (p.z + q.z) / 2) / 600)
      ctx.strokeStyle = this.rgba(lit ? 'accent' : 'ink', alpha * (lit ? 0.85 : 0.08 + depth * 0.18))
      ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke()
    }
    // 消息沿边传递
    this.graph.edges.forEach(([a, b], k) => {
      if (k % 3) return
      const f = (time * 0.4 + k * 0.17) % 1
      const p = projected[a]!, q = projected[b]!
      ctx.fillStyle = this.rgba('accent', alpha * 0.7)
      ctx.fillRect(p.x + (q.x - p.x) * f - 1, p.y + (q.y - p.y) * f - 1, 2, 2)
    })
    this.graph.nodes.forEach((node, k) => {
      const p = projected[k]!
      const depth = clamp((center.z + 300 - p.z) / 600)
      const lit = k === hover
      ctx.fillStyle = this.rgba(lit || node.label ? 'accent' : 'ink', alpha * (0.3 + depth * 0.6))
      ctx.beginPath(); ctx.arc(p.x, p.y, (node.label ? 3 : 2) + depth * 1.5 + (lit ? 2 : 0), 0, Math.PI * 2); ctx.fill()
      if (node.label && depth > 0.35) {
        ctx.font = `400 ${Math.round(12 + depth * 4)}px "Songti SC", "STSong", Georgia, serif`
        ctx.fillStyle = this.rgba('ink', alpha * depth * 0.75)
        ctx.fillText(node.label, p.x + 8, p.y - 6)
      }
    })
  }
}
