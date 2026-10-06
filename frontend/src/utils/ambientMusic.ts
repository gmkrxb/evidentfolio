/**
 * 生成式钢琴小品（Web Audio 实时合成，无音频文件）。
 *
 * 作曲：D 大调，3/4 拍，每分钟 63 拍——缓慢的华尔兹，近于萨蒂《裸体歌舞》的呼吸。
 * - 左手：每小节第一拍落一个低音，第二、三拍轻轻按下和弦；踏板在换和弦时抬起；
 * - 右手：以四小节为一句，按“强拍用和弦音、弱拍级进”的规则生成旋律，句首上行、句尾回落并停在和弦音上；
 *   有的乐句留白，只剩左手，让音乐呼吸；
 * - 底层是一层极轻的弦乐铺底，随和弦交叉淡入淡出；
 * - 一切由墙钟推导：任何页面、任何标签页、刷新之后，都在同一小节、同一拍上继续；
 *   多个标签页同时打开时只有获得焦点的那一个发声。
 * - 交互：点击会在下一个八分音符上落下一个与和声协和的高音（左低右高）；章节改变旋律的疏密与力度。
 * 偏好保存在本机；浏览器要求先有一次交互，因此首次访问需点击 / 触摸 / 按键后才开始。
 */
import { readPreference, writePreference } from './storage'

export type SoundState = 'off' | 'armed' | 'playing'
type Listener = (state: SoundState) => void

const KEY = 'portfolio_sound'
const BEAT = 60 / 63
const BAR = BEAT * 3
const CHORD_BARS = 2
const PHRASE_BARS = 4
const LOOKAHEAD = 1.6
const LEVEL = 0.6

interface Chord { bass: number; hand: number[]; tones: number[]; late?: number[] }
// MIDI 音高：bass 低音，hand 左手和弦（第二、三拍），tones 右手可落在强拍上的和弦音
const PROGRESSION: Chord[] = [
  { bass: 38, hand: [54, 57, 61], tones: [66, 69, 73, 74, 76, 78, 81] }, //        Dmaj7
  { bass: 43, hand: [54, 59, 62], tones: [67, 69, 71, 74, 78, 79, 81] }, //        Gmaj7
  { bass: 47, hand: [54, 57, 62], tones: [66, 69, 71, 74, 78, 81] }, //            Bm7
  { bass: 42, hand: [52, 57, 61], tones: [66, 69, 73, 76, 78, 81] }, //            F♯m7
  { bass: 43, hand: [54, 59, 62], tones: [67, 71, 74, 78, 79, 81] }, //            Gmaj7
  { bass: 42, hand: [57, 62, 64], tones: [66, 69, 74, 76, 78, 81] }, //            D/F♯ add9
  { bass: 40, hand: [55, 62, 66], tones: [67, 71, 74, 76, 78, 79] }, //            Em9
  { bass: 45, hand: [55, 62, 64], tones: [69, 74, 76, 79, 81], late: [55, 61, 64] }, // A7sus4 → A7
]
const SCALE = [62, 64, 66, 67, 69, 71, 73, 74, 76, 78, 79, 81, 83] // D 大调，D4–B5
// 每小节的节奏型（以拍计；负数为休止）
const RHYTHMS = [[3], [2, 1], [1, 2], [1, 1, 1], [-1, 2], [1.5, 1.5], [2, 1], [1, 1, 1]]
const CADENCES = [[3], [2, -1], [1, 2]]
const MOODS: Record<string, { rest: number; velocity: number }> = {
  intro: { rest: 0.2, velocity: 1 },
  manifesto: { rest: 0.4, velocity: 0.9 },
  capabilities: { rest: 0.15, velocity: 1.05 },
  agents: { rest: 0.1, velocity: 1.08 },
  overview: { rest: 0.25, velocity: 1 },
  featured: { rest: 0.2, velocity: 1.02 },
  directions: { rest: 0.3, velocity: 0.95 },
  connect: { rest: 0.4, velocity: 0.9 },
  projects: { rest: 0.25, velocity: 1 },
  detail: { rest: 0.45, velocity: 0.88 },
  certificates: { rest: 0.35, velocity: 0.92 },
  resumes: { rest: 0.45, velocity: 0.88 },
  contact: { rest: 0.4, velocity: 0.9 },
}

const hz = (midi: number) => 440 * Math.pow(2, (midi - 69) / 12)
const clock = () => Date.now() / 1000
/** 当前是否处于浏览器认可的瞬时用户激活中（不支持该 API 的浏览器视为是）。 */
const userActivated = () => {
  const activation = (navigator as Navigator & { userActivation?: { isActive: boolean } }).userActivation
  return activation ? activation.isActive : true
}
const mod = (value: number, size: number) => ((value % size) + size) % size
/** 确定性的伪随机：同一时刻在所有标签页得到同一个值。 */
function hash(a: number, b: number) {
  let h = Math.imul(a ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul(b + 0x632be59b, 0xc2b2ae35)
  h ^= h >>> 13; h = Math.imul(h, 0x27d4eb2d); h ^= h >>> 15
  return (h >>> 0) / 4294967296
}
const chordOfBar = (bar: number) => PROGRESSION[mod(Math.floor(bar / CHORD_BARS), PROGRESSION.length)]!
const nearest = (pool: number[], target: number) => pool.reduce((best, note) => (Math.abs(note - target) < Math.abs(best - target) ? note : best), pool[0]!)

interface Note { time: number; midi: number; length: number; velocity: number }
/** 生成第 phrase 句的右手旋律（全局时间）。 */
export function composePhrase(phrase: number): Note[] {
  const notes: Note[] = []
  const firstBar = phrase * PHRASE_BARS
  let pitch = nearest(chordOfBar(firstBar).tones, 71 + Math.round(hash(phrase, 1) * 6))
  let index = 0
  for (let b = 0; b < PHRASE_BARS; b++) {
    const bar = firstBar + b
    const chord = chordOfBar(bar)
    const cadence = b === PHRASE_BARS - 1
    const pattern = cadence ? CADENCES[Math.floor(hash(phrase, 7) * CADENCES.length)]! : RHYTHMS[Math.floor(hash(phrase * 5 + b, 3) * RHYTHMS.length)]!
    let beat = 0
    pattern.forEach((length, k) => {
      if (length < 0) { beat += -length; return }
      const strong = beat === 0
      // 句子的轮廓：前半上行，后半回落
      const direction = b < 2 ? 1 : -1
      const roll = hash(phrase * 31 + index, 11)
      if (strong || cadence) {
        const target = pitch + direction * (roll < 0.5 ? 2 : 4) - (roll > 0.85 ? direction * 5 : 0)
        pitch = nearest(chord.tones, target)
      } else {
        const at = SCALE.indexOf(nearest(SCALE, pitch))
        const step = roll < 0.6 ? direction : roll < 0.85 ? -direction : direction * 2
        pitch = SCALE[Math.max(0, Math.min(SCALE.length - 1, at + step))]!
      }
      const arc = Math.sin(((b * 3 + beat) / (PHRASE_BARS * 3)) * Math.PI)
      notes.push({
        time: (bar * 3 + beat) * BEAT,
        midi: pitch,
        length: length * BEAT * (k === pattern.length - 1 ? 1.15 : 0.98),
        velocity: 0.42 + arc * 0.16 + (strong ? 0.04 : 0),
      })
      beat += length
      index += 1
    })
  }
  // 句尾偶尔有一声高八度的回响
  if (hash(phrase, 13) < 0.45) {
    const last = notes[notes.length - 1]!
    notes.push({ time: last.time + BEAT * 1.5, midi: Math.min(last.midi + 12, 90), length: BEAT * 2, velocity: 0.22 })
  }
  return notes
}

class AmbientEngine {
  state: SoundState = 'off'
  private ctx: AudioContext | null = null
  private master: GainNode | null = null
  private pianoBus: GainNode | null = null
  private padBus: GainNode | null = null
  private scheduled = new Map<string, number>()
  private phrases = new Map<number, Note[]>()
  private timer = 0
  private section = 'intro'
  private lastTouch = 0
  private listeners = new Set<Listener>()
  private installed = false
  private ducked = false
  private active = true
  private allowed = false
  private inactiveTimer = 0
  private readonly id = Math.random().toString(36).slice(2)
  private channel: BroadcastChannel | null = null

  subscribe(listener: Listener) {
    this.listeners.add(listener)
    listener(this.state)
    return () => this.listeners.delete(listener)
  }

  private emit(state: SoundState) {
    this.state = state
    this.listeners.forEach((listener) => listener(state))
  }

  /** 由公开布局调用：挂上全局交互监听。可重复调用。 */
  install() {
    this.setActive(true)
    if (this.installed || typeof window === 'undefined') return
    this.installed = true
    this.section = document.documentElement.dataset.section || this.section
    const gesture = (event: Event) => {
      if ((event.target as HTMLElement | null)?.closest?.('[data-sound-toggle]')) return
      // 只在浏览器认可的“用户激活”里创建音频（触摸的 pointerdown、Esc 等按键都不算），否则会出现自动播放警告
      if (!userActivated()) return
      if (this.state === 'armed' && this.active && this.allowed) void this.play()
    }
    window.addEventListener('pointerdown', gesture, { passive: true })
    window.addEventListener('pointerup', gesture, { passive: true })
    window.addEventListener('touchend', gesture, { passive: true })
    window.addEventListener('keydown', gesture)
    window.addEventListener('pointerdown', (event) => this.touch(event.clientX), { passive: true })
    window.addEventListener('portfolio:section', (event) => { this.section = String((event as CustomEvent<string>).detail || 'intro') })
    window.addEventListener('portfolio:chime', () => this.arpeggio())
    document.addEventListener('visibilitychange', () => (document.hidden ? this.duck() : this.claim()))
    window.addEventListener('focus', () => this.claim())
    // 另一个标签页关闭了声音：这里也关；另一个标签页开启：这里待命。
    window.addEventListener('storage', (event) => {
      if (event.key !== KEY) return
      if (event.newValue === 'off' && this.state !== 'off') this.stop(false)
      else if (event.newValue === 'on' && this.state === 'off' && this.allowed) this.emit('armed')
    })
    try {
      this.channel = new BroadcastChannel('portfolio-sound')
      this.channel.onmessage = (event: MessageEvent<{ type: string; id: string }>) => {
        if (event.data?.type === 'claim' && event.data.id !== this.id) this.duck()
      }
    } catch { /* 不支持时各标签页独立发声 */ }
  }

  /** 站点设置：管理员可在后台关闭全站音乐。 */
  setAllowed(allowed: boolean) {
    if (allowed === this.allowed) return
    this.allowed = allowed
    if (!allowed) { if (this.state !== 'off') this.stop(false); return }
    const preference = readPreference(KEY)
    if (preference === 'off') return
    this.emit('armed')
    void this.tryAutoplay()
  }

  /**
   * 页面加载后立即尝试发声：浏览器允许自动播放时直接开始（从全局进度接上）；
   * 不允许时保持“待命”，第一次点击 / 触摸 / 按键即开始。
   * 支持 getAutoplayPolicy 的浏览器先询问策略，被禁止时不创建音频，避免控制台警告。
   */
  private async tryAutoplay() {
    const policy = (navigator as Navigator & { getAutoplayPolicy?: (type: string) => string }).getAutoplayPolicy?.('audiocontext')
    if (policy === 'disallowed') return
    if (!this.ctx) this.build()
    const ctx = this.ctx
    if (!ctx) return
    void ctx.resume().catch(() => undefined)
    await new Promise((resolve) => window.setTimeout(resolve, 150))
    if (ctx.state === 'running' && this.state === 'armed' && this.allowed) {
      this.emit('playing')
      this.claim()
    }
  }

  /** 进入 / 离开公开页面（后台不播放）。短暂的布局切换不会打断音乐。 */
  setActive(active: boolean) {
    window.clearTimeout(this.inactiveTimer)
    if (active) {
      this.active = true
      if (this.state === 'playing') this.claim()
      return
    }
    this.inactiveTimer = window.setTimeout(() => { this.active = false; this.duck() }, 600)
  }

  toggle() {
    if (!this.allowed) return
    if (this.state === 'off') void this.play()
    else this.stop()
  }

  async play(quiet = false) {
    if (!this.allowed) return
    if (!quiet) writePreference(KEY, 'on')
    try {
      if (!this.ctx) this.build()
      const ctx = this.ctx
      if (!ctx) return
      const resumed = ctx.resume()
      if (quiet) {
        // 自动续播：浏览器不允许时保持“待命”，等待第一次交互
        await Promise.race([resumed, new Promise((resolve) => window.setTimeout(resolve, 400))])
        if (ctx.state !== 'running') { this.emit('armed'); return }
      } else await resumed
      this.emit('playing')
      this.claim()
    } catch {
      this.emit('armed')
    }
  }

  stop(persist = true) {
    if (persist) writePreference(KEY, 'off')
    this.emit('off')
    this.fadeOut(1.4)
  }

  /** 让本标签页成为唯一发声者，并从全局进度处接上。 */
  private claim() {
    if (this.state !== 'playing' || !this.active || document.hidden || !this.ctx || !this.master) return
    this.channel?.postMessage({ type: 'claim', id: this.id })
    const wasSilent = this.ducked || this.ctx.state !== 'running' || this.master.gain.value < 0.05
    this.ducked = false
    void this.ctx.resume()
    if (wasSilent) this.scheduled.clear()
    const now = this.ctx.currentTime
    this.master.gain.cancelScheduledValues(now)
    this.master.gain.setValueAtTime(this.master.gain.value, now)
    this.master.gain.linearRampToValueAtTime(LEVEL, now + (wasSilent ? 3 : 0.6))
    window.clearInterval(this.timer)
    this.timer = window.setInterval(() => this.schedule(), 200)
    this.schedule(true)
  }

  private duck() {
    if (!this.ctx || this.ducked) return
    this.ducked = true
    this.fadeOut(1.4)
  }

  private fadeOut(seconds: number) {
    window.clearInterval(this.timer)
    this.timer = 0
    const ctx = this.ctx
    if (!ctx || !this.master) return
    const now = ctx.currentTime
    this.master.gain.cancelScheduledValues(now)
    this.master.gain.setValueAtTime(this.master.gain.value, now)
    this.master.gain.linearRampToValueAtTime(0, now + seconds)
    window.setTimeout(() => {
      if (this.state !== 'playing' || this.ducked) { this.scheduled.clear(); void ctx.suspend() }
    }, seconds * 1000 + 200)
  }

  private build() {
    const Context = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Context) return
    const ctx = new Context({ latencyHint: 'playback' })
    const master = ctx.createGain()
    master.gain.value = 0
    const warmth = ctx.createBiquadFilter()
    warmth.type = 'highshelf'
    warmth.frequency.value = 3800
    warmth.gain.value = -5
    const body = ctx.createBiquadFilter()
    body.type = 'peaking'
    body.frequency.value = 220
    body.Q.value = 0.7
    body.gain.value = 1.5
    const compressor = ctx.createDynamicsCompressor()
    compressor.threshold.value = -18
    compressor.knee.value = 20
    compressor.ratio.value = 2.2
    compressor.attack.value = 0.03
    compressor.release.value = 0.5
    master.connect(warmth).connect(body).connect(compressor).connect(ctx.destination)

    // 混响：平滑、偏暗的厅堂脉冲（无嘶声），22 ms 预延迟
    const convolver = ctx.createConvolver()
    const length = Math.floor(ctx.sampleRate * 3.8)
    const impulse = ctx.createBuffer(2, length, ctx.sampleRate)
    for (let channel = 0; channel < 2; channel++) {
      const data = impulse.getChannelData(channel)
      let y = 0, z = 0
      for (let i = 0; i < length; i++) {
        const t = i / ctx.sampleRate
        const k = 0.32 * Math.exp(-t * 1.1) + 0.025
        y += k * ((Math.random() * 2 - 1) - y)
        z += k * (y - z)
        data[i] = z * Math.exp(-t * 1.55) * Math.min(1, t / 0.02) * 3.4
      }
    }
    convolver.buffer = impulse
    const preDelay = ctx.createDelay(0.1)
    preDelay.delayTime.value = 0.022
    const reverb = ctx.createGain()
    reverb.gain.value = 0.34
    reverb.connect(preDelay).connect(convolver).connect(master)

    const pianoBus = ctx.createGain()
    pianoBus.connect(master)
    pianoBus.connect(reverb)

    const padTone = ctx.createBiquadFilter()
    padTone.type = 'lowpass'
    padTone.frequency.value = 1100
    padTone.Q.value = 0.3
    const padBus = ctx.createGain()
    padBus.connect(padTone)
    const padSend = ctx.createGain()
    padSend.gain.value = 1.6
    padTone.connect(master)
    padTone.connect(padSend).connect(reverb)

    this.ctx = ctx
    this.master = master
    this.pianoBus = pianoBus
    this.padBus = padBus
  }

  /** 前瞻调度：把未来 LOOKAHEAD 秒内的全局事件换算到音频时钟上。 */
  private schedule(joining = false) {
    const ctx = this.ctx
    if (!ctx || this.state !== 'playing' || this.ducked || ctx.state !== 'running') return
    const g = clock()
    const base = ctx.currentTime
    const at = (time: number) => base + Math.max(0, time - g)
    const horizon = g + LOOKAHEAD
    const mood = MOODS[this.section] || MOODS.intro!

    // 左手：每拍检查一次
    const firstBeat = Math.ceil(g / BEAT - 0.001)
    for (let beat = firstBeat; beat * BEAT < horizon; beat++) {
      const key = `lh:${beat}`
      if (this.scheduled.has(key)) continue
      this.scheduled.set(key, beat * BEAT)
      const bar = Math.floor(beat / 3)
      const position = mod(beat, 3)
      const chord = chordOfBar(bar)
      const changeAt = (Math.floor(bar / CHORD_BARS) + 1) * CHORD_BARS * BAR // 换和弦时抬踏板
      const second = mod(bar, CHORD_BARS) === CHORD_BARS - 1
      const hand = second && chord.late ? chord.late : chord.hand
      const time = beat * BEAT
      if (position === 0) {
        this.piano(chord.bass, at(time), 0.42, changeAt - time + 0.15)
        if (mod(bar, CHORD_BARS) === 0) this.piano(chord.bass + 12, at(time + 0.012), 0.2, changeAt - time + 0.15)
      } else {
        const soft = position === 1 ? 0.27 : 0.21
        hand.forEach((note, i) => this.piano(note, at(time + i * 0.018), soft, BEAT * 0.95 + 0.12))
      }
    }

    // 弦乐铺底：每个和弦一层
    const chordIndex = Math.floor(g / (BAR * CHORD_BARS))
    for (const n of [chordIndex, chordIndex + 1]) {
      const key = `pad:${n}`
      const start = n * BAR * CHORD_BARS
      if (this.scheduled.has(key) || start - 1.5 > horizon) continue
      this.scheduled.set(key, start + BAR * CHORD_BARS)
      const chord = chordOfBar(n * CHORD_BARS)
      const from = Math.max(start - 1.2, g)
      this.pad([chord.bass + 12, ...chord.hand], at(from), joining && n === chordIndex ? 3 : 2.4, at(start + BAR * CHORD_BARS))
    }

    // 右手旋律：按乐句生成
    const phraseLength = BAR * PHRASE_BARS
    const phrase = Math.floor(g / phraseLength)
    for (const p of [phrase, phrase + 1]) {
      if (p * phraseLength > horizon) continue
      if (hash(p, 97) < mood.rest) continue // 留白
      let notes = this.phrases.get(p)
      if (!notes) { notes = composePhrase(p); this.phrases.set(p, notes) }
      notes.forEach((note, i) => {
        const key = `rh:${p}:${i}`
        if (note.time < g - 0.01 || note.time > horizon || this.scheduled.has(key)) return
        this.scheduled.set(key, note.time)
        this.piano(note.midi, at(note.time), Math.min(0.75, note.velocity * mood.velocity), note.length)
      })
    }

    for (const [key, time] of this.scheduled) if (time < g - 12) this.scheduled.delete(key)
    for (const p of this.phrases.keys()) if (p < phrase - 1) this.phrases.delete(p)
  }

  /** 弦乐铺底：纯净的正弦叠加，缓慢起落。 */
  private pad(notes: number[], start: number, attack: number, end: number) {
    const ctx = this.ctx!
    notes.forEach((note, index) => {
      const level = index === 0 ? 0.014 : 0.009
      const gain = ctx.createGain()
      gain.gain.setValueAtTime(0, start)
      gain.gain.linearRampToValueAtTime(level, start + attack)
      const hold = Math.max(start + attack, end - 0.6)
      gain.gain.setValueAtTime(level, hold)
      gain.gain.setTargetAtTime(0, hold, 1.1)
      gain.connect(this.padBus!)
      ;[[1, 1, -4], [1, 1, 4], [2, 0.12, 0]].forEach(([ratio, amp, cents]) => {
        const osc = ctx.createOscillator()
        osc.frequency.value = hz(note) * ratio!
        osc.detune.value = cents!
        const partial = ctx.createGain()
        partial.gain.value = amp!
        osc.connect(partial).connect(gain)
        osc.start(start)
        osc.stop(hold + 7)
      })
    })
  }

  /**
   * 钢琴：加法合成。泛音带轻微的不谐和（弦的刚度），基音由两根略微失谐的弦构成；
   * 先是击弦后的迅速回落，再是长长的余音；高泛音衰减更快；力度越大音色越亮；松开时由制音器止住。
   */
  private piano(note: number, when: number, velocity: number, hold: number) {
    const ctx = this.ctx
    if (!ctx || !this.pianoBus) return
    const f0 = hz(note)
    const out = ctx.createGain()
    out.gain.value = velocity * 0.2
    let tail: AudioNode = out
    if (ctx.createStereoPanner) {
      const panner = ctx.createStereoPanner()
      panner.pan.value = Math.max(-0.45, Math.min(0.45, (note - 62) / 40))
      out.connect(panner)
      tail = panner
    }
    tail.connect(this.pianoBus)
    const sustain = 3.4 * Math.pow(2, -(note - 60) / 24)
    const brightness = 0.42 + velocity * 0.45
    const release = when + Math.max(0.2, hold)
    const end = Math.min(when + sustain * 3.2, release + 1.4)
    const attack = 0.003 + (1 - velocity) * 0.006
    const partials = f0 > 1400 ? 4 : f0 > 700 ? 5 : 7
    for (let n = 1; n <= partials; n++) {
      const ratio = n * Math.sqrt(1 + 0.00038 * n * n)
      const amp = Math.pow(brightness, n - 1) / Math.pow(n, 1.1)
      if (amp < 0.012) break
      const env = ctx.createGain()
      const decay = sustain / (1 + 0.55 * (n - 1))
      env.gain.setValueAtTime(0, when)
      env.gain.linearRampToValueAtTime(amp, when + attack)
      env.gain.setTargetAtTime(amp * 0.42, when + attack, 0.09 + 0.05 / n) // 击弦后的迅速回落
      env.gain.setTargetAtTime(0, when + 0.25, decay / 2.2) //                  余音
      env.gain.setTargetAtTime(0, release, 0.16 + 0.08 / n) //                   制音器
      env.connect(out)
      const strings = n === 1 ? [-0.9, 0.9] : [0]
      strings.forEach((cents) => {
        const osc = ctx.createOscillator()
        osc.frequency.value = f0 * ratio
        osc.detune.value = cents
        if (strings.length > 1) {
          const half = ctx.createGain()
          half.gain.value = 0.5
          osc.connect(half).connect(env)
        } else osc.connect(env)
        osc.start(when)
        osc.stop(end)
      })
    }
  }

  /** 点击：在下一个八分音符上落下一个和弦音，左低右高。 */
  private touch(x: number) {
    const now = performance.now()
    if (this.state !== 'playing' || this.ducked || !this.ctx || now - this.lastTouch < 220) return
    this.lastTouch = now
    const g = clock()
    const grid = BEAT / 2
    const time = Math.ceil((g + 0.03) / grid) * grid
    const pool = chordOfBar(Math.floor(time / BAR)).tones
    const ratio = Math.max(0, Math.min(1, x / Math.max(1, window.innerWidth)))
    const note = pool[Math.round(ratio * (pool.length - 1))]!
    this.piano(note, this.ctx.currentTime + (time - g), 0.3, BEAT * 1.5)
  }

  /** 智能体广播：沿和弦上行的八分音符琶音。 */
  private arpeggio() {
    if (this.state !== 'playing' || this.ducked || !this.ctx) return
    const g = clock()
    const grid = BEAT / 2
    const start = Math.ceil((g + 0.03) / grid) * grid
    const pool = chordOfBar(Math.floor(start / BAR)).tones
    pool.slice(-4).forEach((note, step) => this.piano(note, this.ctx!.currentTime + (start - g) + step * grid, 0.3 - step * 0.03, BEAT * (2 - step * 0.3)))
  }
}

export const ambient = new AmbientEngine()
