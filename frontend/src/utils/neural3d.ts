/**
 * 「深层网络」走廊：原始监测信号被切成补丁 token，穿过十二层 Transformer 平面（上千个神经元），
 * 前向传播的激活波前由近及远推进，随后反向传播的梯度以陶土色回流；注意力弧在当前层内跳跃，
 * 层间以稀疏的强连接相连，末端汇成类别分布。鼠标在画面上激起涟漪，并点亮附近的神经元。
 */

type V3 = { x: number; y: number; z: number }
type P2 = { x: number; y: number; z: number; k: number; visible: boolean }
type Project = (p: V3) => P2

export interface NeuralPaint {
  ink: (alpha: number) => string
  accent: (alpha: number) => string
  label: (text: string, x: number, y: number, alpha: number, accent?: boolean, size?: number) => void
  /** 纸色：用于层面板的磨砂填充，遮住身后的层 */
  paper?: (alpha: number) => string
}

const LAYERS = 12
const COLS = 15
const ROWS = 9
const SPACING_Z = 170
const STEP = 38
const NAMES = ['Embed', 'Attn', 'FFN', 'Attn', 'FFN', 'Attn', 'FFN', 'Attn', 'FFN', 'Attn', 'Norm', 'Head']
const CLASSES = ['normal', 'outlier', 'square', 'missing', 'minor', 'drift', 'trend']
const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v))

export class Neural3D {
  private ripples: Array<{ x: number; y: number; t: number }> = []
  private lastPointer = { x: -1, y: -1, t: 0 }

  /** 主绘制：project 已包含相机；cursor 为屏幕坐标与存在度。 */
  /**
   * band：桌面端以侧视的横向长带呈现（输入在左、输出在右），各层随章节进入依次从上方落位。
   */
  draw(ctx: CanvasRenderingContext2D, project: Project, time: number, alpha: number, cursor: { x: number; y: number; presence: number }, mobile: boolean, paint: NeuralPaint, band = false) {
    this.paint = paint
    this.band = band
    const cols = mobile ? 11 : COLS, rows = mobile ? 7 : ROWS
    const layers = mobile ? 9 : LAYERS
    const z0 = -((layers - 1) * SPACING_Z) / 2
    const period = 7.5
    const cycle = (time % period) / period
    const forward = clamp(cycle / 0.62)
    const backward = clamp((cycle - 0.66) / 0.3)
    const front = forward * (layers + 1) - 1
    const back = (1 - backward) * (layers + 1) - 1

    // 涟漪：鼠标移动足够远时在当前位置激起一圈。
    if (cursor.presence > 0.3 && Math.hypot(cursor.x - this.lastPointer.x, cursor.y - this.lastPointer.y) > 60 && time - this.lastPointer.t > 0.25) {
      this.ripples.push({ x: cursor.x, y: cursor.y, t: time })
      this.lastPointer = { x: cursor.x, y: cursor.y, t: time }
    }
    this.ripples = this.ripples.filter((r) => time - r.t < 2.2)

    // 入场：各层依次从上方落位并淡入
    const settleOf = (k: number) => { const t = clamp(alpha * 1.7 - (k / layers) * 0.7); return t * t * (3 - 2 * t) }
    const drop = (k: number) => (1 - settleOf(k)) * 260
    this.settle = settleOf
    const neuron = (k: number, i: number, j: number): V3 => ({ x: (i - (cols - 1) / 2) * STEP, y: (j - (rows - 1) / 2) * STEP + drop(k), z: z0 + k * SPACING_Z })
    // 特征图：平滑、各层不同的激活图样
    const feature = (k: number, i: number, j: number) => {
      const a = Math.sin(i * (0.55 + k * 0.07) + k * 1.7 + time * 0.4) * Math.cos(j * (0.62 - k * 0.03) - k * 0.9)
      const b = Math.sin((i + j) * 0.33 + k * 2.3)
      return clamp(0.5 + 0.45 * a + 0.2 * b)
    }

    // 走廊框架：各层四角连成的透视通道
    const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]] as const
    const half = { x: ((cols - 1) / 2) * STEP + 26, y: ((rows - 1) / 2) * STEP + 26 }
    const frame = (k: number) => corners.map(([sx, sy]) => project({ x: sx * half.x, y: sy * half.y + drop(k), z: z0 + k * SPACING_Z }))
    const frames = Array.from({ length: layers }, (_, k) => frame(k))
    return this.render(ctx, project, time, alpha, cursor, { cols, rows, layers, z0, front, back, backward, neuron, feature, frames })
  }

  private render(ctx: CanvasRenderingContext2D, project: Project, time: number, alpha: number, cursor: { x: number; y: number; presence: number },
    g: { cols: number; rows: number; layers: number; z0: number; front: number; back: number; backward: number; neuron: (k: number, i: number, j: number) => V3; feature: (k: number, i: number, j: number) => number; frames: P2[][] }) {
    const paint = this.paint as NeuralPaint
    const { cols, rows, layers, front, back, backward, neuron, feature, frames } = g
    // 通道纵向棱线
    ctx.strokeStyle = paint.ink(0.12 * alpha)
    ctx.lineWidth = 0.7
    ctx.beginPath()
    for (let c = 0; c < 4; c++) {
      frames.forEach((f, k) => (k ? ctx.lineTo(f[c]!.x, f[c]!.y) : ctx.moveTo(f[c]!.x, f[c]!.y)))
    }
    ctx.stroke()

    // 由远及近绘制每一层
    const projected: P2[][] = []
    for (let k = layers - 1; k >= 0; k--) {
      const f = frames[k]!
      const layerAlpha = this.settle(k)
      if (layerAlpha < 0.02) { projected[k] = []; continue }
      const wave = Math.exp(-((k - front) ** 2) / 1.6) * layerAlpha
      const grad = backward > 0 ? Math.exp(-((k - back) ** 2) / 1.2) : 0
      ctx.beginPath()
      f.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)))
      ctx.closePath()
      if (paint.paper) { ctx.fillStyle = paint.paper(0.62 * alpha * layerAlpha); ctx.fill() } // 磨砂玻璃般的层面板
      ctx.fillStyle = wave > 0.3 ? paint.accent(wave * 0.05 * alpha) : paint.ink((0.012 + wave * 0.03) * alpha)
      ctx.fill()
      ctx.strokeStyle = grad > 0.2 ? paint.accent((0.25 + grad * 0.5) * alpha) : paint.ink((0.16 + wave * 0.35) * alpha)
      ctx.lineWidth = 0.8 + wave * 0.6
      ctx.stroke()
      const pts: P2[] = []
      for (let j = 0; j < rows; j++) {
        for (let i = 0; i < cols; i++) {
          const p = project(neuron(k, i, j))
          pts.push(p)
          let v = feature(k, i, j) * (0.18 + wave * 0.82)
          let lit = 0
          if (cursor.presence > 0.05) {
            const d = Math.hypot(p.x - cursor.x, p.y - cursor.y)
            lit = Math.max(0, 1 - d / 90) * cursor.presence
          }
          for (const r of this.ripples) {
            const age = time - r.t
            const d = Math.hypot(p.x - r.x, p.y - r.y)
            lit = Math.max(lit, Math.exp(-((d - age * 260) ** 2) / 900) * (1 - age / 2.2))
          }
          v = Math.max(v, lit)
          const size = (1.4 + v * 3) * Math.min(1.5, p.k * 1.6)
          const hot = v > 0.72 || lit > 0.4 || grad * feature(k, i, j) > 0.5
          if (hot) {
            // 被激活的神经元：圆点 + 一圈柔光
            ctx.fillStyle = paint.accent(0.12 * v * alpha * layerAlpha)
            ctx.beginPath(); ctx.arc(p.x, p.y, size * 1.9, 0, Math.PI * 2); ctx.fill()
            ctx.fillStyle = paint.accent((0.5 + v * 0.5) * alpha * layerAlpha)
            ctx.beginPath(); ctx.arc(p.x, p.y, size * 0.62, 0, Math.PI * 2); ctx.fill()
          } else {
            ctx.fillStyle = paint.ink((0.14 + v * 0.6) * alpha * layerAlpha)
            ctx.fillRect(p.x - size / 2, p.y - size / 2, size, size)
          }
        }
      }
      projected[k] = pts
      // 层名与编号
      const tag = f[3]!
      // 横带模式下层挨得近，只标注奇数层与正在计算的层
      if (!this.band || k % 2 === 0 || wave > 0.5) paint.label(`L${String(k + 1).padStart(2, '0')} · ${NAMES[k % NAMES.length]}`, tag.x, tag.y - 8, (0.3 + wave * 0.6) * alpha * layerAlpha, wave > 0.5, 10)
    }

    // 层间强连接：只连接波前两侧的高激活神经元
    const tokens: Array<{ p: P2; q: P2; f: number; w: number }> = []
    ctx.lineWidth = 0.7
    for (let k = 0; k < layers - 1; k++) {
      const wave = Math.exp(-((k + 0.5 - front) ** 2) / 1.2)
      if (wave < 0.08) continue
      const a = projected[k], b = projected[k + 1]
      if (!a?.length || !b?.length) continue
      ctx.strokeStyle = paint.accent(0.32 * wave * alpha)
      ctx.beginPath()
      for (let n = 0; n < 26; n++) {
        const i = (n * 7 + k * 5) % cols, j = (n * 3 + k) % rows
        const i2 = (i + ((n % 5) - 2) + cols) % cols, j2 = (j + ((n % 3) - 1) + rows) % rows
        if (feature(k, i, j) < 0.55) continue
        const p = a[j * cols + i]!, q = b[j2 * cols + i2]!
        ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y)
        tokens.push({ p, q, f: ((time * 1.1 + n * 0.173) % 1 + 1) % 1, w: wave })
      }
      ctx.stroke()
    }
    // 沿强连接流动的信号粒子
    for (const token of tokens) {
      const x = token.p.x + (token.q.x - token.p.x) * token.f, y = token.p.y + (token.q.y - token.p.y) * token.f
      ctx.fillStyle = paint.accent(0.85 * token.w * alpha)
      ctx.beginPath(); ctx.arc(x, y, 1.6, 0, Math.PI * 2); ctx.fill()
    }

    // 注意力：在波前所在层内画多头注意力弧
    const head = Math.round(clamp(front, 0, layers - 1))
    const pts = projected[head]
    if (pts?.length && front > -0.5 && front < layers) {
      const query = (Math.floor(time * 1.6) * 7) % (cols * rows)
      const q = pts[query]!
      for (let h = 0; h < 10; h++) {
        const key = (query * 13 + h * 29 + 11) % (cols * rows)
        const p = pts[key]!
        const lift = 40 + h * 6
        ctx.strokeStyle = paint.accent((0.25 + (h % 3) * 0.18) * alpha)
        ctx.lineWidth = 0.6 + (h % 3) * 0.4
        ctx.beginPath()
        ctx.moveTo(q.x, q.y)
        ctx.quadraticCurveTo((q.x + p.x) / 2, Math.min(q.y, p.y) - lift * q.k, p.x, p.y)
        ctx.stroke()
      }
      ctx.strokeStyle = paint.accent(alpha)
      ctx.beginPath(); ctx.arc(q.x, q.y, 5, 0, Math.PI * 2); ctx.stroke()
    }

    // 输入：信号带与补丁 token 飞入第一层
    const z0 = g.z0
    const zIn = z0 - 260
    ctx.strokeStyle = paint.ink(0.55 * alpha)
    ctx.lineWidth = 1.1
    ctx.beginPath()
    const width = (cols - 1) * STEP
    for (let s = 0; s <= 120; s++) {
      const u = s / 120
      const x = -width / 2 + u * width
      const y = -((g.rows - 1) / 2) * STEP - 70 + Math.sin(u * 40 + time * 4) * 10 * Math.exp(-u) + Math.sin(u * 13 - time * 2) * 7 + (Math.abs(u - 0.62) < 0.015 ? -38 : 0)
      const p = project({ x, y, z: zIn })
      if (s) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y)
    }
    ctx.stroke()
    const patches = 8
    for (let n = 0; n < patches; n++) {
      const u = (n + 0.5) / patches
      const fly = (time * 0.5 + n * 0.11) % 1
      const from = { x: -width / 2 + u * width, y: -((g.rows - 1) / 2) * STEP - 70, z: zIn }
      const to = neuron(0, Math.round(u * (cols - 1)), Math.round(fly * (rows - 1)))
      const p = project({ x: from.x + (to.x - from.x) * fly, y: from.y + (to.y - from.y) * fly, z: from.z + (to.z - from.z) * fly })
      const size = 7 * p.k
      ctx.strokeStyle = paint.accent((0.8 - fly * 0.5) * alpha)
      ctx.lineWidth = 1
      ctx.strokeRect(p.x - size, p.y - size * 0.6, size * 2, size * 1.2)
    }
    const inTag = project({ x: -width / 2, y: -((g.rows - 1) / 2) * STEP - 100, z: zIn })
    paint.label('x ∈ ℝ^{72000} → 6 × patch tokens', inTag.x, inTag.y, 0.6 * alpha, true, 10)

    // 输出：在最后一层旁以屏幕坐标绘制类别分布，避免透视压缩后文字重叠
    const settle = clamp((front - (layers - 2)) / 2)
    const last = frames[layers - 1]!
    const barW = 14, gap = 8, maxH = 70
    const total = CLASSES.length * (barW + gap)
    let anchor = { x: Math.min(...last.map((p) => p.x)) - 20, y: Math.max(...last.map((p) => p.y)) + 34 }
    let x0 = Math.max(16, anchor.x - total)
    if (this.band) {
      // 横带：输出分布画在最后一层的右侧，与层的中线对齐
      const right = Math.max(...last.map((p) => p.x))
      const mid = last.reduce((sum, p) => sum + p.y, 0) / last.length
      anchor = { x: right + 30, y: mid + maxH / 2 }
      x0 = Math.min(anchor.x, (ctx.canvas.clientWidth || ctx.canvas.width) - Math.max(total, 210) - 24)
    }
    let best = 0
    const values = CLASSES.map((_, n) => {
      const target = n === 1 ? 0.78 : 0.05 + ((n * 37) % 10) / 120
      return 0.14 + (target - 0.14) * settle
    })
    values.forEach((value, n) => { if (value > values[best]!) best = n })
    ctx.strokeStyle = paint.ink(0.3 * alpha)
    ctx.lineWidth = 0.8
    ctx.beginPath(); ctx.moveTo(x0 - 6, anchor.y); ctx.lineTo(x0 + total, anchor.y); ctx.stroke()
    values.forEach((value, n) => {
      ctx.fillStyle = n === best ? paint.accent(0.9 * alpha) : paint.ink(0.35 * alpha)
      ctx.fillRect(x0 + n * (barW + gap), anchor.y - value * maxH, barW, value * maxH)
    })
    paint.label(`${CLASSES[best]} · p = ${values[best]!.toFixed(2)}`, x0, anchor.y + 16, 0.75 * alpha, true, 10)
    paint.label(backward > 0 ? '∂L/∂θ ← backprop' : 'softmax → p(y | x, evidence)', x0, anchor.y + 30, 0.5 * alpha, backward > 0, 10)
  }

  paint: NeuralPaint | null = null
  private band = false
  private settle: (k: number) => number = () => 1
}
