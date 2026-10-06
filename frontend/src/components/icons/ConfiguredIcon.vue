<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'
import { Circle } from 'lucide-vue-next'
import { iconRegistry, type IconRegistryName } from '@/icons/registry'

const props = defineProps<{
  imageUuid?: string
  iconName?: string
  iconSvg?: string
  size?: number
}>()
const selected = computed(() => iconRegistry[props.iconName as IconRegistryName])
const sanitizedSvg = computed(() => {
  if (!props.iconSvg) return ''
  const clean = DOMPurify.sanitize(props.iconSvg, {
        USE_PROFILES: { svg: true, svgFilters: false },
        FORBID_TAGS: ['script', 'style', 'foreignObject', 'use', 'image', 'animate', 'set'],
        FORBID_ATTR: ['style', 'href', 'xlink:href'],
  })
  const document = new DOMParser().parseFromString(clean, 'image/svg+xml')
  const svg = document.documentElement
  if (svg.localName !== 'svg' || document.querySelector('parsererror')) return ''
  // 自定义图标统一继承主题色，保留镂空与透明区域。
  for (const element of [svg, ...svg.querySelectorAll('*')]) {
    element.removeAttribute('color')
    for (const attribute of ['fill', 'stroke']) {
      const value = element.getAttribute(attribute)
      if (value && !['none', 'transparent'].includes(value.trim().toLowerCase())) {
        element.setAttribute(attribute, 'currentColor')
      }
    }
  }
  if (!svg.hasAttribute('fill')) svg.setAttribute('fill', 'currentColor')
  return new XMLSerializer().serializeToString(svg)
})
</script>

<template>
  <img
    v-if="imageUuid"
    class="configured-icon__image"
    :src="`/api/v1/public/assets/${imageUuid}/thumbnail`"
    alt=""
  />
  <component :is="selected" v-else-if="selected" :style="{ width: `${size || 22}px`, height: `${size || 22}px` }" />
  <span
    v-else-if="sanitizedSvg"
    class="configured-icon__svg"
    :style="{ width: `${size || 22}px`, height: `${size || 22}px` }"
    v-html="sanitizedSvg"
  />
  <Circle v-else :size="size || 22" />
</template>
