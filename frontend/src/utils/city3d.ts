/**
 * 首屏三维城市：塔楼群（分层退台、楼层线、窗格灯光）、在建楼与回转塔吊、
 * 数据中心（机柜指示灯、屋顶冷机风扇、双曲冷却塔）、通信塔，以及连接它们的光纤数据流。
 * 以带遮挡的实体面 + 线框绘制：面用纸色填充遮住身后的线条，按深度由远及近绘制。
 */

export type V3 = { x: number; y: number; z: number }
export type P2 = { x: number; y: number; z: number; k: number; visible: boolean }
type Project = (p: V3) => P2
type Box = { x: number; y: number; z: number; w: number; h: number; d: number }
type Tower = Box & { seed: number; setback?: Box; antenna: number; floors: number }

export interface CityPaint {
  ink: (alpha: number) => string
  accent: (alpha: number) => string
  paper: (alpha: number) => string
}

function rng(seed: number) {
  let s = seed >>> 0
  return () => ((s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296)
}
const hash = (n: number) => { const v = Math.sin(n * 127.1 + 311.7) * 43758.5453; return v - Math.floor(v) }

const FACES: Array<{ corners: [number, number, number, number]; n: V3; side: boolean }> = [
  { corners: [0, 1, 5, 4], n: { x: 0, y: 0, z: -1 }, side: true }, // 前 z0
  { corners: [3, 2, 6, 7], n: { x: 0, y: 0, z: 1 }, side: true }, // 后 z1
  { corners: [0, 3, 7, 4], n: { x: -1, y: 0, z: 0 }, side: true }, // 左 x0
  { corners: [1, 2, 6, 5], n: { x: 1, y: 0, z: 0 }, side: true }, // 右 x1
  { corners: [4, 5, 6, 7], n: { x: 0, y: 1, z: 0 }, side: false }, // 顶
]

export class City3D {
  towers: Tower[] = []
  site: Box & { floors: number } = { x: 0, y: 0, z: 0, w: 0, h: 0, d: 0, floors: 0 }
  crane = { x: 0, y: 0, z: 0, height: 0, jib: 0, counter: 0 }
  hall: Box = { x: 0, y: 0, z: 0, w: 0, h: 0, d: 0 }
  chillers: Box[] = []
  coolers: Array<{ x: number; y: number; z: number; r: number; h: number }> = []
  mast = { x: 0, y: 0, z: 0, h: 0 }
  private steam: Array<{ k: number; t: number; x: number; z: number }> = []

  build(mobile: boolean, ground: (x: number, z: number) => number) {
    const random = rng(1949)
    this.towers = []
    const lots = mobile ? [[560, -420], [660, -300], [760, -460], [640, -150]] : [
      [470, -470], [560, -380], [660, -500], [760, -420], [880, -500], [540, -230], [650, -270], [790, -280], [900, -340], [960, -180], [720, -120], [600, -80],
    ]
    for (const [x, z] of lots as Array<[number, number]>) {
      const w = 44 + random() * 30, d = 40 + random() * 30
      const h = 90 + Math.pow(random(), 1.4) * 300
      const y = ground(x + w / 2, z + d / 2)
      const tower: Tower = { x, y, z, w, h, d, seed: random() * 1000, antenna: random() > 0.55 ? 18 + random() * 28 : 0, floors: Math.max(6, Math.round(h / 13)) }
      if (h > 220 && random() > 0.35) {
        const inset = 8 + random() * 6
        tower.setback = { x: x + inset, y: y + h, z: z + inset, w: w - inset * 2, h: 30 + random() * 60, d: d - inset * 2 }
      }
      this.towers.push(tower)
    }
    // 在建楼与塔吊
    const sx = mobile ? 450 : 450, sz = mobile ? -40 : -40
    this.site = { x: sx, y: ground(sx + 40, sz + 30), z: sz, w: 84, h: 150, d: 64, floors: 6 }
    this.crane = { x: sx - 26, y: this.site.y, z: sz + 32, height: 330, jib: 250, counter: 82 }
    // 数据中心：机房主楼 + 屋顶冷机 + 冷却塔 + 通信塔
    const hx = mobile ? -880 : -880, hz = -520
    this.hall = { x: hx, y: ground(hx + 190, hz + 110), z: hz, w: 380, h: 74, d: 220 }
    this.chillers = []
    for (let row = 0; row < 2; row++) {
      for (let col = 0; col < (mobile ? 4 : 6); col++) {
        this.chillers.push({ x: hx + 26 + col * 58, y: this.hall.y + this.hall.h, z: hz + 40 + row * 92, w: 40, h: 14, d: 54 })
      }
    }
    this.coolers = mobile ? [] : [
      { x: hx + 300, y: ground(hx + 300, hz + 330), z: hz + 320, r: 44, h: 150 },
      { x: hx + 400, y: ground(hx + 400, hz + 300), z: hz + 300, r: 38, h: 128 },
    ]
    this.mast = { x: hx + 430, y: ground(hx + 430, hz + 60), z: hz + 60, h: 300 }
    this.steam = Array.from({ length: mobile ? 0 : 16 }, (_, i) => ({ k: i % 2, t: i / 16, x: (hash(i) - 0.5) * 30, z: (hash(i + 9) - 0.5) * 30 }))
  }

  /** 光纤链路端点（供外部绘制传感器上行）。 */
  get hub(): V3 { return { x: this.hall.x + this.hall.w / 2, y: this.hall.y + this.hall.h + 20, z: this.hall.z + this.hall.d / 2 } }

  draw(ctx: CanvasRenderingContext2D, project: Project, cam: V3, time: number, paint: CityPaint, alpha: number) {
    type Item = { depth: number; draw: () => void }
    const items: Item[] = []
    const depthOf = (p: V3) => Math.hypot(p.x - cam.x, p.y - cam.y, p.z - cam.z)
    for (const tower of this.towers) {
      items.push({ depth: depthOf({ x: tower.x + tower.w / 2, y: tower.y + tower.h / 2, z: tower.z + tower.d / 2 }), draw: () => this.drawTower(ctx, project, cam, tower, time, paint, alpha) })
    }
    items.push({ depth: depthOf({ x: this.site.x + 40, y: this.site.y + 60, z: this.site.z + 30 }), draw: () => this.drawSite(ctx, project, paint, alpha) })
    items.push({ depth: depthOf({ x: this.crane.x, y: this.crane.y + 150, z: this.crane.z }) - 40, draw: () => this.drawCrane(ctx, project, time, paint, alpha) })
    items.push({ depth: depthOf({ x: this.hall.x + this.hall.w / 2, y: this.hall.y, z: this.hall.z + this.hall.d / 2 }), draw: () => this.drawDataCenter(ctx, project, cam, time, paint, alpha) })
    for (const cooler of this.coolers) items.push({ depth: depthOf(cooler), draw: () => this.drawCooler(ctx, project, cooler, paint, alpha) })
    items.push({ depth: depthOf({ ...this.mast, y: this.mast.y + 100 }), draw: () => this.drawMast(ctx, project, time, paint, alpha) })
    items.sort((a, b) => b.depth - a.depth).forEach((item) => item.draw())
    this.drawSteam(ctx, project, time, paint, alpha)
    this.drawLinks(ctx, project, time, paint, alpha)
  }

  // —— 通用：实体盒子（背面剔除 + 纸色填充 + 轮廓） ——
  private corners(b: Box): V3[] {
    const x0 = b.x, x1 = b.x + b.w, y0 = b.y, y1 = b.y + b.h, z0 = b.z, z1 = b.z + b.d
    return [
      { x: x0, y: y0, z: z0 }, { x: x1, y: y0, z: z0 }, { x: x1, y: y0, z: z1 }, { x: x0, y: y0, z: z1 },
      { x: x0, y: y1, z: z0 }, { x: x1, y: y1, z: z0 }, { x: x1, y: y1, z: z1 }, { x: x0, y: y1, z: z1 },
    ]
  }

  private visibleFaces(b: Box, cam: V3) {
    const cx = b.x + b.w / 2, cy = b.y + b.h / 2, cz = b.z + b.d / 2
    return FACES.filter((face) => {
      const fx = cx + face.n.x * b.w / 2, fy = cy + face.n.y * b.h / 2, fz = cz + face.n.z * b.d / 2
      return face.n.x * (cam.x - fx) + face.n.y * (cam.y - fy) + face.n.z * (cam.z - fz) > 0
    })
  }

  private solid(ctx: CanvasRenderingContext2D, project: Project, cam: V3, b: Box, paint: CityPaint, alpha: number, edge = 0.5, fill = 0.94) {
    const c = this.corners(b).map(project)
    const faces = this.visibleFaces(b, cam)
    for (const face of faces) {
      const pts = face.corners.map((i) => c[i]!)
      ctx.beginPath()
      pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)))
      ctx.closePath()
      // 侧面略带明暗，形成体积感。
      const shade = face.n.y ? 0 : face.n.x ? 0.035 : 0.015
      ctx.fillStyle = paint.paper(fill * alpha)
      ctx.fill()
      if (shade) { ctx.fillStyle = paint.ink(shade * alpha); ctx.fill() }
      ctx.strokeStyle = paint.ink(edge * alpha)
      ctx.lineWidth = 0.9
      ctx.stroke()
    }
    return { c, faces }
  }

  private lerp(a: P2, b: P2, t: number) { return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t } }

  // —— 塔楼 ——
  private drawTower(ctx: CanvasRenderingContext2D, project: Project, cam: V3, t: Tower, time: number, paint: CityPaint, alpha: number) {
    const { c, faces } = this.solid(ctx, project, cam, t, paint, alpha, 0.55)
    for (const face of faces.filter((f) => f.side)) {
      const [a, b, top2, top1] = face.corners.map((i) => c[i]!) as [P2, P2, P2, P2]
      // 楼层线
      ctx.strokeStyle = paint.ink(0.13 * alpha)
      ctx.lineWidth = 0.6
      ctx.beginPath()
      for (let f = 1; f < t.floors; f++) {
        const u = f / t.floors
        const l = this.lerp(a, top1, u), r = this.lerp(b, top2, u)
        ctx.moveTo(l.x, l.y); ctx.lineTo(r.x, r.y)
      }
      ctx.stroke()
      // 竖向幕墙分格
      ctx.strokeStyle = paint.ink(0.07 * alpha)
      ctx.beginPath()
      for (let m = 1; m < 4; m++) {
        const u = m / 4
        const bottom = this.lerp(a, b, u), top = this.lerp(top1, top2, u)
        ctx.moveTo(bottom.x, bottom.y); ctx.lineTo(top.x, top.y)
      }
      ctx.stroke()
      // 窗格灯光：缓慢、错落地亮起
      for (let f = 0; f < t.floors; f++) {
        for (let m = 0; m < 4; m++) {
          const n = t.seed + f * 7 + m * 13 + face.n.x * 3 + face.n.z * 5
          const on = Math.sin(time * 0.22 + hash(n) * 40) > 0.82
          if (!on) continue
          const u = (f + 0.5) / t.floors, v = (m + 0.5) / 4
          const l = this.lerp(a, top1, u), r = this.lerp(b, top2, u)
          const x = l.x + (r.x - l.x) * v, y = l.y + (r.y - l.y) * v
          ctx.fillStyle = hash(n + 1) > 0.7 ? paint.accent(0.85 * alpha) : paint.ink(0.42 * alpha)
          ctx.fillRect(x - 1.4, y - 1, 2.8, 2)
        }
      }
    }
    if (t.setback) this.solid(ctx, project, cam, t.setback, paint, alpha, 0.55)
    const roof = t.setback ? t.setback.y + t.setback.h : t.y + t.h
    if (t.antenna) {
      const base = project({ x: t.x + t.w / 2, y: roof, z: t.z + t.d / 2 })
      const tip = project({ x: t.x + t.w / 2, y: roof + t.antenna, z: t.z + t.d / 2 })
      ctx.strokeStyle = paint.ink(0.5 * alpha)
      ctx.beginPath(); ctx.moveTo(base.x, base.y); ctx.lineTo(tip.x, tip.y); ctx.stroke()
      if (Math.sin(time * 2.6 + t.seed) > 0.3) {
        ctx.fillStyle = paint.accent(alpha)
        ctx.beginPath(); ctx.arc(tip.x, tip.y, 2, 0, Math.PI * 2); ctx.fill()
      }
    }
  }

  // —— 在建楼：裸露的楼板与柱网 ——
  private drawSite(ctx: CanvasRenderingContext2D, project: Project, paint: CityPaint, alpha: number) {
    const s = this.site
    const step = s.h / s.floors
    ctx.lineWidth = 0.8
    for (let f = 0; f <= s.floors; f++) {
      const y = s.y + f * step
      const slab = [project({ x: s.x, y, z: s.z }), project({ x: s.x + s.w, y, z: s.z }), project({ x: s.x + s.w, y, z: s.z + s.d }), project({ x: s.x, y, z: s.z + s.d })]
      ctx.beginPath()
      slab.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)))
      ctx.closePath()
      ctx.fillStyle = paint.paper(0.55 * alpha); ctx.fill()
      ctx.strokeStyle = paint.ink((f === s.floors ? 0.5 : 0.35) * alpha); ctx.stroke()
    }
    ctx.strokeStyle = paint.ink(0.4 * alpha)
    ctx.beginPath()
    for (let i = 0; i <= 3; i++) {
      for (const z of [s.z, s.z + s.d]) {
        const x = s.x + (s.w * i) / 3
        const a = project({ x, y: s.y, z }), b = project({ x, y: s.y + s.h, z })
        ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y)
      }
    }
    ctx.stroke()
    // 脚手架斜撑
    ctx.strokeStyle = paint.ink(0.16 * alpha)
    ctx.beginPath()
    for (let f = 0; f < s.floors; f++) {
      const a = project({ x: s.x, y: s.y + f * step, z: s.z - 6 }), b = project({ x: s.x + s.w, y: s.y + (f + 1) * step, z: s.z - 6 })
      ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y)
    }
    ctx.stroke()
  }

  // —— 塔吊：格构塔身、回转吊臂、平衡臂、拉杆、小车与吊钩 ——
  private drawCrane(ctx: CanvasRenderingContext2D, project: Project, time: number, paint: CityPaint, alpha: number) {
    const c = this.crane
    const half = 7
    const top = c.y + c.height
    ctx.lineWidth = 0.8
    // 塔身四肢与 K 形腹杆
    ctx.strokeStyle = paint.ink(0.6 * alpha)
    ctx.beginPath()
    const legs = [[-half, -half], [half, -half], [half, half], [-half, half]]
    for (const [dx, dz] of legs) {
      const a = project({ x: c.x + dx!, y: c.y, z: c.z + dz! }), b = project({ x: c.x + dx!, y: top, z: c.z + dz! })
      ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y)
    }
    ctx.stroke()
    ctx.strokeStyle = paint.ink(0.26 * alpha)
    ctx.beginPath()
    const panel = 16
    for (let y = c.y, k = 0; y < top; y += panel, k++) {
      for (let side = 0; side < 4; side++) {
        const [ax, az] = legs[side]!, [bx, bz] = legs[(side + 1) % 4]!
        const p1 = project({ x: c.x + ax!, y, z: c.z + az! }), p2 = project({ x: c.x + bx!, y: y + panel, z: c.z + bz! })
        const p3 = project({ x: c.x + bx!, y, z: c.z + bz! })
        if (k % 2) { ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y) } else { const p4 = project({ x: c.x + ax!, y: y + panel, z: c.z + az! }); ctx.moveTo(p3.x, p3.y); ctx.lineTo(p4.x, p4.y) }
        ctx.moveTo(p1.x, p1.y); ctx.lineTo(p3.x, p3.y)
      }
    }
    ctx.stroke()
    // 回转
    const angle = time * 0.16 + 0.8
    const ux = Math.cos(angle), uz = Math.sin(angle)
    const at = (s: number, y: number, lateral = 0): V3 => ({ x: c.x + ux * s - uz * lateral, y, z: c.z + uz * s + ux * lateral })
    const jibY = top + 4
    // 吊臂：三角桁架（两根下弦 + 一根上弦）
    const segments = 12
    ctx.strokeStyle = paint.ink(0.62 * alpha)
    ctx.beginPath()
    for (const [lat, dy] of [[-5, 0], [5, 0], [0, 10]] as Array<[number, number]>) {
      const a = project(at(0, jibY + dy, lat)), b = project(at(c.jib, jibY + dy * 0.4, lat * 0.4))
      ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y)
    }
    ctx.stroke()
    ctx.strokeStyle = paint.ink(0.22 * alpha)
    ctx.beginPath()
    for (let i = 0; i < segments; i++) {
      const s0 = (c.jib * i) / segments, s1 = (c.jib * (i + 1)) / segments
      const shrink0 = 1 - (0.6 * i) / segments, shrink1 = 1 - (0.6 * (i + 1)) / segments
      const low = project(at(s0, jibY, -5 * shrink0)), high = project(at(s1, jibY + 10 * shrink1, 0))
      const low2 = project(at(s0, jibY, 5 * shrink0))
      ctx.moveTo(low.x, low.y); ctx.lineTo(high.x, high.y); ctx.lineTo(low2.x, low2.y)
    }
    ctx.stroke()
    // 平衡臂与配重
    ctx.strokeStyle = paint.ink(0.6 * alpha)
    ctx.beginPath()
    const back0 = project(at(0, jibY, 0)), back1 = project(at(-c.counter, jibY, 0))
    ctx.moveTo(back0.x, back0.y); ctx.lineTo(back1.x, back1.y)
    ctx.stroke()
    const weight = [at(-c.counter + 4, jibY - 4, -9), at(-c.counter + 26, jibY - 4, -9), at(-c.counter + 26, jibY - 4, 9), at(-c.counter + 4, jibY - 4, 9),
      at(-c.counter + 4, jibY - 22, -9), at(-c.counter + 26, jibY - 22, -9), at(-c.counter + 26, jibY - 22, 9), at(-c.counter + 4, jibY - 22, 9)].map(project)
    ctx.fillStyle = paint.ink(0.5 * alpha)
    ctx.beginPath()
    for (const face of [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]) {
      face.forEach((i, n) => (n ? ctx.lineTo(weight[i]!.x, weight[i]!.y) : ctx.moveTo(weight[i]!.x, weight[i]!.y)))
      ctx.closePath()
    }
    ctx.fill()
    // 塔帽与拉杆
    const apex = project({ x: c.x, y: top + 54, z: c.z })
    const jibTie = project(at(c.jib * 0.62, jibY + 7, 0)), backTie = project(at(-c.counter, jibY, 0))
    ctx.strokeStyle = paint.ink(0.42 * alpha)
    ctx.beginPath()
    for (const [dx, dz] of legs) { const p = project({ x: c.x + dx!, y: top, z: c.z + dz! }); ctx.moveTo(p.x, p.y); ctx.lineTo(apex.x, apex.y) }
    ctx.moveTo(jibTie.x, jibTie.y); ctx.lineTo(apex.x, apex.y); ctx.lineTo(backTie.x, backTie.y)
    ctx.stroke()
    // 驾驶室
    const cab = project(at(6, jibY - 10, 10))
    ctx.fillStyle = paint.accent(0.7 * alpha)
    ctx.fillRect(cab.x - 4, cab.y - 3, 8, 6)
    // 小车、钢丝绳与吊物（轻微摆动）
    const s = 50 + (0.5 + 0.5 * Math.sin(time * 0.35)) * (c.jib - 80)
    const drop = 40 + (0.5 + 0.5 * Math.sin(time * 0.27 + 1)) * (c.height - 120)
    const sway = Math.sin(time * 1.3) * 5
    const trolley = project(at(s, jibY - 1, 0))
    const hookPoint = at(s, jibY - drop, sway)
    const hook = project(hookPoint)
    ctx.fillStyle = paint.ink(0.75 * alpha)
    ctx.fillRect(trolley.x - 4, trolley.y - 2, 8, 4)
    ctx.strokeStyle = paint.ink(0.45 * alpha)
    ctx.lineWidth = 0.7
    ctx.beginPath()
    for (const lat of [-2, 2]) { const top2 = project(at(s, jibY - 1, lat)); ctx.moveTo(top2.x, top2.y); ctx.lineTo(hook.x, hook.y) }
    ctx.stroke()
    const load = [-14, 14].flatMap((dx) => [-8, 8].map((dz) => project({ x: hookPoint.x + dx, y: hookPoint.y - 10, z: hookPoint.z + dz })))
    ctx.strokeStyle = paint.ink(0.3 * alpha)
    ctx.beginPath()
    for (const p of load) { ctx.moveTo(hook.x, hook.y); ctx.lineTo(p.x, p.y) }
    ctx.stroke()
    const beam = [project({ x: hookPoint.x - 22, y: hookPoint.y - 12, z: hookPoint.z }), project({ x: hookPoint.x + 22, y: hookPoint.y - 12, z: hookPoint.z })]
    ctx.strokeStyle = paint.accent(0.9 * alpha)
    ctx.lineWidth = 3
    ctx.beginPath(); ctx.moveTo(beam[0]!.x, beam[0]!.y); ctx.lineTo(beam[1]!.x, beam[1]!.y); ctx.stroke()
    ctx.lineWidth = 1
    // 臂端航空灯
    if (Math.sin(time * 3) > 0) {
      const tip = project(at(c.jib, jibY + 4, 0))
      ctx.fillStyle = paint.accent(alpha)
      ctx.beginPath(); ctx.arc(tip.x, tip.y, 2, 0, Math.PI * 2); ctx.fill()
    }
  }

  // —— 数据中心 ——
  private drawDataCenter(ctx: CanvasRenderingContext2D, project: Project, cam: V3, time: number, paint: CityPaint, alpha: number) {
    const h = this.hall
    const { c, faces } = this.solid(ctx, project, cam, h, paint, alpha, 0.6)
    // 立面：机柜列阵与指示灯
    for (const face of faces.filter((f) => f.side)) {
      const [a, b, top2, top1] = face.corners.map((i) => c[i]!) as [P2, P2, P2, P2]
      const racks = face.n.z ? 16 : 10
      ctx.strokeStyle = paint.ink(0.16 * alpha)
      ctx.lineWidth = 0.6
      ctx.beginPath()
      for (let r = 1; r < racks; r++) {
        const u = r / racks
        const p = this.lerp(a, b, u), q = this.lerp(top1, top2, u * 0.98 + 0.01)
        const q2 = { x: p.x + (q.x - p.x) * 0.82, y: p.y + (q.y - p.y) * 0.82 }
        ctx.moveTo(p.x, p.y); ctx.lineTo(q2.x, q2.y)
      }
      const band1 = this.lerp(a, top1, 0.82), band2 = this.lerp(b, top2, 0.82)
      ctx.moveTo(band1.x, band1.y); ctx.lineTo(band2.x, band2.y)
      ctx.stroke()
      for (let r = 0; r < racks; r++) {
        for (let led = 0; led < 7; led++) {
          const n = r * 31 + led * 7 + face.n.x * 11 + face.n.z * 17
          const phase = Math.sin(time * (1.5 + hash(n) * 5) + hash(n + 3) * 30)
          if (phase < 0.1) continue
          const u = (r + 0.5) / racks, v = 0.12 + (led / 7) * 0.62
          const l = this.lerp(a, top1, v), rr = this.lerp(b, top2, v)
          const x = l.x + (rr.x - l.x) * u, y = l.y + (rr.y - l.y) * u
          ctx.fillStyle = hash(n + 5) > 0.82 ? paint.accent(0.95 * alpha) : paint.ink((0.25 + phase * 0.3) * alpha)
          ctx.fillRect(x - 1, y - 0.8, 2, 1.6)
        }
      }
    }
    // 屋顶冷机与旋转风扇
    for (const [i, chiller] of this.chillers.entries()) {
      this.solid(ctx, project, cam, chiller, paint, alpha, 0.45)
      for (const dz of [0.28, 0.72]) {
        const center = { x: chiller.x + chiller.w / 2, y: chiller.y + chiller.h + 0.5, z: chiller.z + chiller.d * dz }
        const r = 10
        ctx.strokeStyle = paint.ink(0.45 * alpha)
        ctx.lineWidth = 0.7
        ctx.beginPath()
        for (let k = 0; k <= 20; k++) {
          const a = (k / 20) * Math.PI * 2
          const p = project({ x: center.x + Math.cos(a) * r, y: center.y, z: center.z + Math.sin(a) * r })
          if (k) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y)
        }
        const spin = time * 5 + i
        const middle = project(center)
        for (let blade = 0; blade < 3; blade++) {
          const a = spin + (blade * Math.PI * 2) / 3
          const p = project({ x: center.x + Math.cos(a) * r * 0.85, y: center.y, z: center.z + Math.sin(a) * r * 0.85 })
          ctx.moveTo(middle.x, middle.y); ctx.lineTo(p.x, p.y)
        }
        ctx.stroke()
      }
    }
  }

  // —— 双曲冷却塔 ——
  private drawCooler(ctx: CanvasRenderingContext2D, project: Project, t: { x: number; y: number; z: number; r: number; h: number }, paint: CityPaint, alpha: number) {
    const rings = 9, waist = 0.62
    const radius = (u: number) => t.r * (waist + (1 - waist) * Math.pow((u - 0.68) / 0.68, 2) * 1.4)
    const ring = (u: number) => Array.from({ length: 33 }, (_, k) => {
      const a = (k / 32) * Math.PI * 2, r = radius(u)
      return project({ x: t.x + Math.cos(a) * r, y: t.y + u * t.h, z: t.z + Math.sin(a) * r })
    })
    // 轮廓填充以遮挡身后
    const base = ring(0), top = ring(1)
    ctx.beginPath()
    const left = Array.from({ length: rings + 1 }, (_, i) => { const u = i / rings; return project({ x: t.x - radius(u), y: t.y + u * t.h, z: t.z }) })
    const right = Array.from({ length: rings + 1 }, (_, i) => { const u = i / rings; return project({ x: t.x + radius(u), y: t.y + u * t.h, z: t.z }) })
    left.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)))
    right.reverse().forEach((p) => ctx.lineTo(p.x, p.y))
    ctx.closePath()
    ctx.fillStyle = paint.paper(0.92 * alpha); ctx.fill()
    ctx.strokeStyle = paint.ink(0.5 * alpha); ctx.lineWidth = 0.9; ctx.stroke()
    ctx.strokeStyle = paint.ink(0.14 * alpha)
    ctx.lineWidth = 0.6
    for (let i = 0; i <= rings; i++) {
      const pts = ring(i / rings)
      ctx.beginPath()
      pts.forEach((p, k) => (k ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)))
      ctx.stroke()
    }
    ctx.strokeStyle = paint.ink(0.5 * alpha)
    ctx.beginPath(); top.forEach((p, k) => (k ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.stroke()
    ctx.beginPath(); base.forEach((p, k) => (k ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.stroke()
  }

  private drawSteam(ctx: CanvasRenderingContext2D, project: Project, time: number, paint: CityPaint, alpha: number) {
    for (const puff of this.steam) {
      const tower = this.coolers[puff.k]
      if (!tower) continue
      const life = (time * 0.08 + puff.t) % 1
      const p = project({ x: tower.x + puff.x * (1 + life * 3) + life * 40, y: tower.y + tower.h + life * 120, z: tower.z + puff.z })
      ctx.strokeStyle = paint.ink(0.16 * (1 - life) * alpha)
      ctx.lineWidth = 0.8
      ctx.beginPath(); ctx.arc(p.x, p.y, (6 + life * 22) * p.k, 0, Math.PI * 2); ctx.stroke()
    }
  }

  // —— 通信塔：三角格构 + 抛物面天线 + 信号 ——
  private drawMast(ctx: CanvasRenderingContext2D, project: Project, time: number, paint: CityPaint, alpha: number) {
    const m = this.mast
    const legs = [0, 1, 2].map((k) => (k / 3) * Math.PI * 2 + 0.4)
    const at = (u: number, k: number): V3 => { const r = 18 * (1 - u * 0.85); return { x: m.x + Math.cos(legs[k]!) * r, y: m.y + u * m.h, z: m.z + Math.sin(legs[k]!) * r } }
    ctx.strokeStyle = paint.ink(0.55 * alpha)
    ctx.lineWidth = 0.8
    ctx.beginPath()
    for (let k = 0; k < 3; k++) { const a = project(at(0, k)), b = project(at(1, k)); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y) }
    ctx.stroke()
    ctx.strokeStyle = paint.ink(0.2 * alpha)
    ctx.beginPath()
    for (let i = 0; i < 14; i++) {
      const u0 = i / 14, u1 = (i + 1) / 14
      for (let k = 0; k < 3; k++) { const a = project(at(u0, k)), b = project(at(u1, (k + 1) % 3)); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y) }
    }
    ctx.stroke()
    for (const [u, dir] of [[0.72, 0.4], [0.82, 2.6]] as Array<[number, number]>) {
      const center = { x: m.x + Math.cos(dir) * 14, y: m.y + u * m.h, z: m.z + Math.sin(dir) * 14 }
      ctx.strokeStyle = paint.ink(0.5 * alpha)
      ctx.beginPath()
      for (let k = 0; k <= 16; k++) {
        const a = (k / 16) * Math.PI * 2
        const p = project({ x: center.x - Math.sin(dir) * Math.cos(a) * 9, y: center.y + Math.sin(a) * 9, z: center.z + Math.cos(dir) * Math.cos(a) * 9 })
        if (k) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y)
      }
      ctx.stroke()
    }
    const tip = project({ x: m.x, y: m.y + m.h + 10, z: m.z })
    for (let k = 0; k < 3; k++) {
      const phase = (time * 0.6 + k / 3) % 1
      ctx.strokeStyle = paint.accent(0.55 * (1 - phase) * alpha)
      ctx.beginPath(); ctx.arc(tip.x, tip.y, 5 + phase * 30, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke()
    }
    if (Math.sin(time * 2.2) > 0) { ctx.fillStyle = paint.accent(alpha); ctx.beginPath(); ctx.arc(tip.x, tip.y, 2.2, 0, Math.PI * 2); ctx.fill() }
  }

  // —— 光纤：数据中心 ↔ 通信塔 ↔ 城市 ——
  private drawLinks(ctx: CanvasRenderingContext2D, project: Project, time: number, paint: CityPaint, alpha: number) {
    const hub = this.hub
    const tallest = this.towers.reduce((best, t) => (t.h > best.h ? t : best), this.towers[0]!)
    const ends: V3[] = [
      { x: this.mast.x, y: this.mast.y + this.mast.h * 0.8, z: this.mast.z },
      { x: tallest.x + tallest.w / 2, y: tallest.y + tallest.h + (tallest.setback?.h || 0), z: tallest.z + tallest.d / 2 },
      { x: this.crane.x, y: this.crane.y + this.crane.height, z: this.crane.z },
    ]
    ends.forEach((end, index) => {
      const mid = { x: (hub.x + end.x) / 2, y: Math.max(hub.y, end.y) + 160 + index * 40, z: (hub.z + end.z) / 2 - 60 }
      const points = Array.from({ length: 33 }, (_, i) => {
        const t = i / 32
        return project({ x: (1 - t) ** 2 * hub.x + 2 * (1 - t) * t * mid.x + t * t * end.x, y: (1 - t) ** 2 * hub.y + 2 * (1 - t) * t * mid.y + t * t * end.y, z: (1 - t) ** 2 * hub.z + 2 * (1 - t) * t * mid.z + t * t * end.z })
      })
      ctx.strokeStyle = paint.accent(0.38 * alpha)
      ctx.lineWidth = 0.8
      ctx.setLineDash([2, 4])
      ctx.beginPath(); points.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.stroke()
      ctx.setLineDash([])
      for (let k = 0; k < 3; k++) {
        const f = (((time * 0.22 + index * 0.3 + k / 3) % 1) + 1) % 1
        const head = points[Math.min(32, Math.max(0, Math.floor(f * 32)))]
        if (!head) continue
        ctx.fillStyle = paint.accent(0.95 * alpha)
        ctx.beginPath(); ctx.arc(head.x, head.y, 2.2, 0, Math.PI * 2); ctx.fill()
      }
    })
    ctx.lineWidth = 1
  }
}
