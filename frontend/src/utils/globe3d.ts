/**
 * 「互联的地球」：陆地点阵按昼夜明暗着色，大气辉光，刻度环与雷达扫描；
 * 三条倾斜轨道上的卫星向城市下行数据；城市之间的海底光缆以彗尾数据包传输；
 * 城市向上升起数据柱，悬停时显示城市名与延迟。
 */
import { landPoints } from './landPoints'

type V3 = { x: number; y: number; z: number }
type P2 = { x: number; y: number; z: number; k: number; visible: boolean }
type Project = (p: V3) => P2

export interface GlobePaint {
  ink: (alpha: number) => string
  accent: (alpha: number) => string
  label: (text: string, x: number, y: number, alpha: number, accent?: boolean, size?: number) => void
}

const R = 300
const CITIES: Array<{ lat: number; lon: number; name: string }> = [
  { lat: 39.9, lon: 116.4, name: 'Beijing' }, { lat: 25.0, lon: 102.7, name: 'Kunming' }, { lat: 31.2, lon: 121.5, name: 'Shanghai' },
  { lat: 22.5, lon: 114.1, name: 'Shenzhen' }, { lat: 1.35, lon: 103.8, name: 'Singapore' }, { lat: 51.5, lon: -0.1, name: 'London' },
  { lat: 40.7, lon: -74.0, name: 'New York' }, { lat: 37.8, lon: -122.4, name: 'San Francisco' }, { lat: -33.9, lon: 151.2, name: 'Sydney' },
  { lat: 25.2, lon: 55.3, name: 'Dubai' }, { lat: 50.1, lon: 8.7, name: 'Frankfurt' }, { lat: 35.7, lon: 139.7, name: 'Tokyo' },
  { lat: 48.9, lon: 2.35, name: 'Paris' }, { lat: -23.5, lon: -46.6, name: 'São Paulo' }, { lat: 30.6, lon: 104.1, name: 'Chengdu' },
  { lat: 19.1, lon: 72.9, name: 'Mumbai' }, { lat: 55.8, lon: 37.6, name: 'Moscow' }, { lat: -1.3, lon: 36.8, name: 'Nairobi' },
]
const ROUTES: Array<[number, number]> = [[0, 1], [0, 2], [2, 3], [1, 4], [3, 4], [0, 11], [2, 7], [5, 6], [6, 7], [5, 10], [10, 9], [9, 4], [4, 8], [12, 5], [6, 13], [11, 7], [14, 1], [14, 0], [15, 9], [15, 4], [16, 10], [17, 9], [17, 5]]
const ORBITS = [{ tilt: 0.5, node: 0.2, r: 1.32, speed: 0.32, sats: 3 }, { tilt: -0.9, node: 1.4, r: 1.46, speed: -0.22, sats: 2 }, { tilt: 1.25, node: 2.6, r: 1.6, speed: 0.17, sats: 2 }]
const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v))

function sphere(lat: number, lon: number, r: number): V3 {
  const phi = (lat * Math.PI) / 180, lam = (lon * Math.PI) / 180
  // 观察者在球外，经度向东应在屏幕右侧，因此 x 取负号（否则地图左右镜像）。
  return { x: -r * Math.cos(phi) * Math.sin(lam), y: r * Math.sin(phi), z: r * Math.cos(phi) * Math.cos(lam) }
}

export class Globe3D {
  private land: Array<V3 & { n: V3 }> = []
  private built = false

  private build(mobile: boolean) {
    // 斐波那契格点：等面积分布，轮廓与真实海岸线一致；移动端隔点取样
    this.land = landPoints()
      .filter((_, index) => !mobile || index % 2 === 0)
      .map(({ lat, lon }) => {
        const p = sphere(lat, lon, R)
        return { ...p, n: { x: p.x / R, y: p.y / R, z: p.z / R } }
      })
    this.built = true
  }

  draw(ctx: CanvasRenderingContext2D, project: Project, cam: V3, time: number, alpha: number, cursor: { x: number; y: number; presence: number }, mobile: boolean, paint: GlobePaint) {
    if (!this.built) this.build(mobile)
    const center = project({ x: 0, y: 0, z: 0 })
    const radius = R * center.k
    const camLen = Math.hypot(cam.x, cam.y, cam.z) || 1
    const view = { x: cam.x / camLen, y: cam.y / camLen, z: cam.z / camLen }
    const facing = (p: V3) => (p.x * view.x + p.y * view.y + p.z * view.z) / R
    // 太阳方向缓慢绕转，形成晨昏线
    const sunAngle = time * 0.05 + 1.2
    const sun = { x: Math.cos(sunAngle), y: 0.28, z: Math.sin(sunAngle) }

    // 大气辉光与本体
    const glow = ctx.createRadialGradient(center.x, center.y, radius * 0.92, center.x, center.y, radius * 1.28)
    glow.addColorStop(0, paint.accent(0.09 * alpha))
    glow.addColorStop(1, paint.accent(0))
    ctx.fillStyle = glow
    ctx.beginPath(); ctx.arc(center.x, center.y, radius * 1.28, 0, Math.PI * 2); ctx.fill()
    ctx.strokeStyle = paint.ink(0.28 * alpha)
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.arc(center.x, center.y, radius, 0, Math.PI * 2); ctx.stroke()

    // 刻度环：每 5° 一短刻，30° 一长刻并标注
    const ring = radius * 1.14
    const spin = time * 0.04
    ctx.strokeStyle = paint.ink(0.3 * alpha)
    ctx.lineWidth = 0.8
    ctx.beginPath()
    for (let d = 0; d < 360; d += 5) {
      const a = (d * Math.PI) / 180 + spin
      const long = d % 30 === 0
      const r0 = ring, r1 = ring + (long ? 10 : 4)
      ctx.moveTo(center.x + Math.cos(a) * r0, center.y + Math.sin(a) * r0)
      ctx.lineTo(center.x + Math.cos(a) * r1, center.y + Math.sin(a) * r1)
    }
    ctx.stroke()
    if (!mobile) {
      for (let d = 0; d < 360; d += 30) {
        const a = (d * Math.PI) / 180 + spin
        paint.label(`${String(d).padStart(3, '0')}°`, center.x + Math.cos(a) * (ring + 18) - 12, center.y + Math.sin(a) * (ring + 18) + 4, 0.4 * alpha, false, 9)
      }
    }
    // 雷达扫描扇区
    const sweep = time * 0.9
    const fan = ctx.createConicGradient ? ctx.createConicGradient(sweep - 0.6, center.x, center.y) : null
    if (fan) {
      fan.addColorStop(0, paint.accent(0))
      fan.addColorStop(0.09, paint.accent(0.12 * alpha))
      fan.addColorStop(0.1, paint.accent(0))
      fan.addColorStop(1, paint.accent(0))
      ctx.fillStyle = fan
      ctx.beginPath(); ctx.arc(center.x, center.y, radius, 0, Math.PI * 2); ctx.fill()
    }

    // 经纬网（只画朝向观察者的半球）
    ctx.strokeStyle = paint.ink(0.08 * alpha)
    ctx.lineWidth = 0.6
    ctx.beginPath()
    for (let lat = -60; lat <= 60; lat += 30) {
      let pen = false
      for (let lon = -180; lon <= 180; lon += 5) {
        const s = sphere(lat, lon, R)
        const p = project(s)
        if (facing(s) > 0) { if (pen) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y); pen = true } else pen = false
      }
    }
    for (let lon = -180; lon < 180; lon += 30) {
      let pen = false
      for (let lat = -90; lat <= 90; lat += 5) {
        const s = sphere(lat, lon, R)
        const p = project(s)
        if (facing(s) > 0) { if (pen) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y); pen = true } else pen = false
      }
    }
    ctx.stroke()

    // 陆地：昼侧更亮，夜侧暗；扫描线经过时闪亮
    const size = mobile ? 1.5 : 2.1
    const sweepDir = { x: Math.cos(sweep), y: Math.sin(sweep) }
    for (const point of this.land) {
      const f = facing(point)
      if (f < 0.04) continue // 只画朝向观察者的半球，背面不透出来（否则大陆会叠成镜像）
      const p = project(point)
      const day = clamp(point.n.x * sun.x + point.n.y * sun.y + point.n.z * sun.z + 0.25)
      const dx = p.x - center.x, dy = p.y - center.y
      const ang = Math.atan2(dy * sweepDir.x - dx * sweepDir.y, dx * sweepDir.x + dy * sweepDir.y)
      const scanned = ang < 0 && ang > -0.35 ? 1 + ang / 0.35 : 0
      const near = cursor.presence > 0.05 ? Math.max(0, 1 - Math.hypot(p.x - cursor.x, p.y - cursor.y) / 80) * cursor.presence : 0
      const a = (0.14 + day * 0.5 + f * 0.24) * (mobile ? 0.62 : 1)
      const hot = near > 0.25 || scanned > 0.6
      ctx.fillStyle = hot ? paint.accent(Math.min(1, a + 0.4) * alpha) : paint.ink(a * alpha)
      const s = size * (0.7 + Math.max(0, f) * 0.5) * (1 + near * 0.8)
      ctx.fillRect(p.x - s / 2, p.y - s / 2, s, s)
    }

    // 轨道与卫星
    const satellites: Array<{ p: P2; w: V3 }> = []
    ORBITS.forEach((orbit, o) => {
      const ct = Math.cos(orbit.tilt), st = Math.sin(orbit.tilt), cn = Math.cos(orbit.node), sn = Math.sin(orbit.node)
      const point = (a: number): V3 => {
        const x = Math.cos(a) * R * orbit.r, z = Math.sin(a) * R * orbit.r
        const y1 = -z * st, z1 = z * ct
        return { x: x * cn - z1 * sn, y: y1, z: x * sn + z1 * cn }
      }
      ctx.strokeStyle = paint.ink(0.14 * alpha)
      ctx.lineWidth = 0.7
      ctx.setLineDash(o === 1 ? [3, 6] : [])
      ctx.beginPath()
      for (let s = 0; s <= 96; s++) {
        const w = point((s / 96) * Math.PI * 2)
        const p = project(w)
        if (s) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y)
      }
      ctx.stroke()
      ctx.setLineDash([])
      for (let n = 0; n < orbit.sats; n++) {
        const a = time * orbit.speed + (n / orbit.sats) * Math.PI * 2 + o
        const w = point(a)
        const p = project(w)
        const behind = facing(w) < 0 && Math.hypot(p.x - center.x, p.y - center.y) < radius
        if (behind) continue
        satellites.push({ p, w })
        ctx.fillStyle = paint.ink(0.85 * alpha)
        ctx.fillRect(p.x - 2.5, p.y - 1.2, 5, 2.4)
        ctx.strokeStyle = paint.ink(0.6 * alpha)
        ctx.beginPath(); ctx.moveTo(p.x - 7, p.y); ctx.lineTo(p.x + 7, p.y); ctx.stroke()
      }
    })

    // 城市与上升的数据柱
    const cityPoints = CITIES.map((city) => {
      const s = sphere(city.lat, city.lon, R + 2)
      return { city, s, p: project(s), f: facing(s) }
    })
    cityPoints.forEach(({ s, p, f }, index) => {
      if (f < 0.05) return
      const pulse = (time * 0.8 + index * 0.17) % 1
      ctx.strokeStyle = paint.accent(0.7 * (1 - pulse) * alpha)
      ctx.lineWidth = 0.9
      ctx.beginPath(); ctx.arc(p.x, p.y, 2 + pulse * 10, 0, Math.PI * 2); ctx.stroke()
      const height = 18 + ((index * 37) % 30) + Math.sin(time * 2 + index) * 6
      const top = project({ x: s.x * (1 + height / R), y: s.y * (1 + height / R), z: s.z * (1 + height / R) })
      ctx.strokeStyle = paint.accent(0.55 * f * alpha)
      ctx.lineWidth = 1.4
      ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(top.x, top.y); ctx.stroke()
      ctx.fillStyle = paint.accent(alpha)
      ctx.beginPath(); ctx.arc(p.x, p.y, 2.4, 0, Math.PI * 2); ctx.fill()
    })

    // 卫星下行：每颗卫星选择最近的可见城市
    for (const [n, { p, w }] of satellites.entries()) {
      let best: (typeof cityPoints)[number] | null = null, bestD = Infinity
      for (const c of cityPoints) {
        if (c.f < 0.1) continue
        const d = Math.hypot(c.s.x - w.x, c.s.y - w.y, c.s.z - w.z)
        if (d < bestD) { bestD = d; best = c }
      }
      if (!best || bestD > R * 1.2) continue
      const phase = (time * 1.2 + n * 0.3) % 1
      ctx.strokeStyle = paint.accent(0.3 * alpha)
      ctx.setLineDash([2, 4])
      ctx.lineWidth = 0.7
      ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(best.p.x, best.p.y); ctx.stroke()
      ctx.setLineDash([])
      ctx.fillStyle = paint.accent(0.9 * alpha)
      ctx.beginPath(); ctx.arc(p.x + (best.p.x - p.x) * phase, p.y + (best.p.y - p.y) * phase, 1.8, 0, Math.PI * 2); ctx.fill()
    }

    // 海底光缆 / 骨干网：大圆弧 + 彗尾
    ROUTES.forEach(([a, b], index) => {
      const ca = CITIES[a]!, cb = CITIES[b]!
      const p1 = sphere(ca.lat, ca.lon, 1), p2 = sphere(cb.lat, cb.lon, 1)
      const dot = clamp(p1.x * p2.x + p1.y * p2.y + p1.z * p2.z, -1, 1)
      const omega = Math.acos(dot)
      if (omega < 0.01) return
      const steps = 40
      const pts: Array<P2 & { front: boolean }> = []
      for (let s = 0; s <= steps; s++) {
        const t = s / steps
        const k1 = Math.sin((1 - t) * omega) / Math.sin(omega), k2 = Math.sin(t * omega) / Math.sin(omega)
        const h = R * (1 + Math.sin(Math.PI * t) * (0.1 + omega * 0.09))
        const w = { x: (p1.x * k1 + p2.x * k2) * h, y: (p1.y * k1 + p2.y * k2) * h, z: (p1.z * k1 + p2.z * k2) * h }
        const p = project(w)
        const front = facing(w) > -0.05 || Math.hypot(p.x - center.x, p.y - center.y) > radius
        pts.push({ ...p, front })
      }
      ctx.strokeStyle = paint.accent(0.2 * alpha)
      ctx.lineWidth = 0.7
      ctx.beginPath()
      pts.forEach((p, s) => (s && p.front && pts[s - 1]!.front ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)))
      ctx.stroke()
      const head = ((time * (0.18 + (index % 4) * 0.04) + index * 0.13) % 1) * steps
      for (let trail = 0; trail < 9; trail++) {
        const s = Math.floor(head) - trail
        if (s < 1) break
        const p = pts[s]!, q = pts[s - 1]!
        if (!p.front || !q.front) continue
        ctx.strokeStyle = paint.accent((1 - trail / 9) * 0.95 * alpha)
        ctx.lineWidth = 2 - trail * 0.15
        ctx.beginPath(); ctx.moveTo(q.x, q.y); ctx.lineTo(p.x, p.y); ctx.stroke()
      }
    })

    // 悬停城市：名称与模拟延迟
    if (cursor.presence > 0.05) {
      let hover: (typeof cityPoints)[number] | null = null, best = 34
      for (const c of cityPoints) {
        if (c.f < 0.05) continue
        const d = Math.hypot(c.p.x - cursor.x, c.p.y - cursor.y)
        if (d < best) { best = d; hover = c }
      }
      if (hover) {
        ctx.strokeStyle = paint.accent(alpha)
        ctx.lineWidth = 1
        ctx.beginPath(); ctx.arc(hover.p.x, hover.p.y, 9, 0, Math.PI * 2); ctx.stroke()
        const latency = 12 + Math.round(Math.abs(Math.sin(hover.city.lon)) * 180)
        paint.label(`${hover.city.name} · ${hover.city.lat.toFixed(1)}°, ${hover.city.lon.toFixed(1)}° · ${latency} ms`, hover.p.x + 14, hover.p.y - 10, alpha, true, 11)
      }
    }
    if (!mobile) paint.label('TCP/IP · MQTT · 5G · LEO · edge → cloud', center.x - radius, center.y + ring + 44, 0.5 * alpha)
  }
}
