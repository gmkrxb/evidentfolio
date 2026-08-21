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
const sanitizedSvg = computed(() =>
  props.iconSvg
    ? DOMPurify.sanitize(props.iconSvg, {
        USE_PROFILES: { svg: true, svgFilters: false },
        FORBID_TAGS: ['script', 'style', 'foreignObject', 'use', 'image', 'animate', 'set'],
        FORBID_ATTR: ['style', 'href', 'xlink:href'],
      })
    : '',
)
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

