<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { parseCountValue } from '@/utils/countValue'

/** 数字进入视口时从零计数到目标值；非数字内容原样显示。千分位、小数与前后缀都保持原样。 */
const props = defineProps<{ value: string | number }>()
const root = ref<HTMLElement | null>(null)
const parsed = computed(() => parseCountValue(String(props.value ?? '')))
const shown = ref<string>('')
let frame = 0
let observer: IntersectionObserver | undefined
let played = false

function finalText() { return String(props.value ?? '') }
function play() {
  const target = parsed.value
  if (!target || played) { shown.value = finalText(); return }
  played = true
  const start = performance.now(), duration = 1600
  const step = (now: number) => {
    const t = Math.min(1, (now - start) / duration)
    const eased = 1 - Math.pow(2, -10 * t)
    shown.value = t >= 1 ? finalText() : target.format(target.number * eased)
    if (t < 1) frame = requestAnimationFrame(step)
  }
  frame = requestAnimationFrame(step)
}
onMounted(() => {
  if (!parsed.value || window.matchMedia('(prefers-reduced-motion: reduce)').matches || typeof IntersectionObserver === 'undefined') { shown.value = finalText(); return }
  shown.value = parsed.value.format(0)
  observer = new IntersectionObserver(([entry]) => { if (entry?.isIntersecting) { play(); observer?.disconnect() } }, { threshold: 0.4 })
  if (root.value) observer.observe(root.value)
})
watch(() => props.value, () => { if (played || !parsed.value) shown.value = finalText() })
onBeforeUnmount(() => { observer?.disconnect(); cancelAnimationFrame(frame) })
</script>

<template>
  <span ref="root" class="count-up" :aria-label="String(value)"><span aria-hidden="true">{{ shown || value }}</span></span>
</template>
