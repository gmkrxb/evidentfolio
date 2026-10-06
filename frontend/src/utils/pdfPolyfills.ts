/**
 * pdf.js 6 使用了一批非常新的 JavaScript 能力（Map.getOrInsertComputed、Math.sumPrecise、
 * Uint8Array.fromBase64 等），Safari 与稍旧的 Chrome / Firefox 尚未支持，会导致简历无法打开。
 * 这里在主线程与 PDF Worker 中按需补齐，只在缺失时定义。
 */
/* eslint-disable @typescript-eslint/no-explicit-any */
const define = (target: any, name: string, value: unknown) => {
  if (target && !(name in target)) Object.defineProperty(target, name, { value, writable: true, configurable: true, enumerable: false })
}

for (const Collection of [Map, WeakMap] as any[]) {
  define(Collection.prototype, 'getOrInsert', function (this: any, key: unknown, value: unknown) {
    if (!this.has(key)) this.set(key, value)
    return this.get(key)
  })
  define(Collection.prototype, 'getOrInsertComputed', function (this: any, key: unknown, compute: (key: unknown) => unknown) {
    if (!this.has(key)) this.set(key, compute(key))
    return this.get(key)
  })
}

define(Promise, 'withResolvers', function withResolvers<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
})

define(Promise, 'try', function (callback: (...args: unknown[]) => unknown, ...args: unknown[]) {
  return new Promise((resolve) => resolve(callback(...args)))
})

define(Math, 'sumPrecise', function (values: Iterable<number>) {
  // Neumaier 补偿求和，精度足够 pdf.js 的字节长度计算。
  let sum = 0
  let compensation = 0
  for (const value of values) {
    const next = sum + value
    compensation += Math.abs(sum) >= Math.abs(value) ? sum - next + value : value - next + sum
    sum = next
  }
  return sum + compensation
})

define(Uint8Array.prototype, 'toHex', function (this: Uint8Array) {
  let out = ''
  for (let i = 0; i < this.length; i++) out += this[i]!.toString(16).padStart(2, '0')
  return out
})

define(Uint8Array.prototype, 'toBase64', function (this: Uint8Array) {
  let binary = ''
  for (let i = 0; i < this.length; i += 0x8000) binary += String.fromCharCode(...this.subarray(i, i + 0x8000))
  return btoa(binary)
})

define(Uint8Array, 'fromBase64', function (value: string) {
  const binary = atob(value.replace(/[\s]/g, ''))
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
})

define(Uint8Array, 'fromHex', function (value: string) {
  const bytes = new Uint8Array(value.length / 2)
  for (let i = 0; i < bytes.length; i++) bytes[i] = parseInt(value.slice(i * 2, i * 2 + 2), 16)
  return bytes
})

export {}
