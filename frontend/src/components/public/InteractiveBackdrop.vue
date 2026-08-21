<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Cpu, Power } from 'lucide-vue-next'
import { useLocaleStore } from '@/stores/locale'

interface Ripple {
  id: number
  x: number
  y: number
}

const eligible = ref(false)
const enabled = ref(false)
const cursor = ref<HTMLElement | null>(null)
const active = ref(false)
const ripples = ref<Ripple[]>([])
const locale = useLocaleStore()
let frame = 0
let pointerX = -100
let pointerY = -100
let nextId = 1

function renderCursor() {
  frame = 0
  if (cursor.value) cursor.value.style.transform = `translate3d(${pointerX}px, ${pointerY}px, 0)`
}
function move(event: PointerEvent) {
  pointerX = event.clientX
  pointerY = event.clientY
  active.value = Boolean((event.target as Element | null)?.closest('a, button, input, textarea, select'))
  if (!frame) frame = requestAnimationFrame(renderCursor)
}
function click(event: PointerEvent) {
  const id = nextId++
  ripples.value.push({ id, x: event.clientX, y: event.clientY })
  window.setTimeout(() => {
    ripples.value = ripples.value.filter((item) => item.id !== id)
  }, 900)
}

function attach() {
  document.documentElement.classList.add('interactive-cursor')
  window.addEventListener('pointermove', move, { passive: true })
  window.addEventListener('pointerdown', click, { passive: true })
}

function detach() {
  document.documentElement.classList.remove('interactive-cursor')
  window.removeEventListener('pointermove', move)
  window.removeEventListener('pointerdown', click)
  if (frame) cancelAnimationFrame(frame)
  frame = 0
  ripples.value = []
}

function toggle() {
  enabled.value = !enabled.value
  localStorage.setItem('portfolio-interactions', enabled.value ? 'on' : 'off')
  if (enabled.value) attach()
  else detach()
}

onMounted(() => {
  eligible.value = window.matchMedia('(pointer: fine) and (min-width: 1024px) and (prefers-reduced-motion: no-preference)').matches
  enabled.value = eligible.value && localStorage.getItem('portfolio-interactions') !== 'off'
  if (!enabled.value) return
  attach()
})
onBeforeUnmount(() => {
  detach()
})
</script>

<template>
  <button
    v-if="eligible"
    type="button"
    class="interaction-toggle"
    :class="{ 'is-off': !enabled }"
    :aria-pressed="enabled"
    :title="enabled ? locale.t('disableInteraction') : locale.t('enableInteraction')"
    @click.stop="toggle"
  >
    <Cpu v-if="enabled" :size="16" />
    <Power v-else :size="16" />
    <span>{{ enabled ? locale.t('interactionOn') : locale.t('interactionOff') }}</span>
  </button>
  <div v-if="enabled" class="interactive-layer" aria-hidden="true">
    <div class="circuit-field">
      <span v-for="index in 10" :key="index" :class="`circuit-node circuit-node--${index}`">
        {{ index % 3 === 0 ? 'AI' : index % 2 === 0 ? '01' : '[]' }}
      </span>
    </div>
    <span
      v-for="ripple in ripples"
      :key="ripple.id"
      class="pointer-ripple"
      :style="{ left: `${ripple.x}px`, top: `${ripple.y}px` }"
    />
    <span ref="cursor" class="chip-cursor" :class="{ active }">
      <i /><i /><i /><i />
    </span>
  </div>
</template>
