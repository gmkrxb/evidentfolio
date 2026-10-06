<script setup lang="ts">
import { computed } from 'vue'

/** 没有封面图时，根据项目标识生成一幅独一无二的「等高线地图」。 */
const props = defineProps<{ seed: string; label?: string; index?: number }>()

function hash(text: string) {
  let value = 2166136261
  for (let i = 0; i < text.length; i++) { value ^= text.charCodeAt(i); value = Math.imul(value, 16777619) }
  return value >>> 0
}

const art = computed(() => {
  let state = hash(props.seed || 'project') || 1
  const random = () => ((state = (Math.imul(state, 1664525) + 1013904223) >>> 0) / 4294967296)
  const cx = 120 + random() * 160, cy = 90 + random() * 120
  const phases = Array.from({ length: 4 }, () => random() * Math.PI * 2)
  const contours: string[] = []
  for (let k = 1; k <= 22; k++) {
    const radius = k * 15
    let d = ''
    for (let step = 0; step <= 96; step++) {
      const angle = (step / 96) * Math.PI * 2
      const wobble = 1 + 0.16 * Math.sin(3 * angle + phases[0]!) + 0.09 * Math.sin(5 * angle + phases[1]! + k * 0.18) + 0.05 * Math.sin(2 * angle + phases[2]!)
      const x = cx + Math.cos(angle) * radius * wobble * 1.15
      const y = cy + Math.sin(angle) * radius * wobble * 0.82
      d += `${step ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`
    }
    contours.push(d)
  }
  const axis = random() > 0.5
  return { cx, cy, contours, axis, angle: Math.round(phases[3]! * 57.3) % 180 }
})
const code = computed(() => `${String((props.index ?? 0) + 1).padStart(2, '0')} · ${art.value.cx.toFixed(0)}.${art.value.cy.toFixed(0)}`)
</script>

<template>
  <div class="project-art" aria-hidden="true">
    <svg viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">
      <defs>
        <pattern :id="`grid-${seed}`" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" class="project-art__grid" /></pattern>
      </defs>
      <rect width="400" height="300" :fill="`url(#grid-${seed})`" />
      <path v-for="(d, k) in art.contours" :key="k" :d="d" class="project-art__contour" :class="{ 'is-index': k % 5 === 4 }" />
      <g :transform="`rotate(${art.angle} ${art.cx} ${art.cy})`" class="project-art__axis">
        <path :d="`M${art.cx - 260} ${art.cy}H${art.cx + 260}`" />
        <path v-if="art.axis" :d="`M${art.cx} ${art.cy - 200}V${art.cy + 200}`" />
      </g>
      <circle :cx="art.cx" :cy="art.cy" r="4" class="project-art__core" />
      <circle :cx="art.cx" :cy="art.cy" r="11" class="project-art__ring" />
    </svg>
    <span class="project-art__code">{{ code }}</span>
    <strong v-if="label" class="project-art__label">{{ label }}</strong>
  </div>
</template>
