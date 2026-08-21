<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { Check, ChevronDown } from 'lucide-vue-next'
import { useLocaleStore } from '@/stores/locale'

export interface SelectOption {
  value: string
  label: string
  description?: string
}

const props = withDefaults(defineProps<{
  modelValue: string | null
  options: SelectOption[]
  label: string
  placeholder?: string
}>(), { placeholder: '' })
const locale = useLocaleStore()
const placeholderText = computed(() => props.placeholder || locale.t('selectPlaceholder'))
const emit = defineEmits<{ 'update:modelValue': [value: string]; change: [value: string] }>()
const root = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)
const open = ref(false)
const activeIndex = ref(0)
const selected = computed(() => props.options.find((item) => item.value === props.modelValue))

function toggle() {
  open.value = !open.value
  if (open.value) {
    activeIndex.value = Math.max(0, props.options.findIndex((item) => item.value === props.modelValue))
  }
}
function select(value: string) {
  emit('update:modelValue', value)
  emit('change', value)
  open.value = false
  nextTick(() => trigger.value?.focus())
}
function onKeydown(event: KeyboardEvent) {
  if (!open.value && ['ArrowDown', 'Enter', ' '].includes(event.key)) {
    event.preventDefault()
    open.value = true
    return
  }
  if (!open.value) return
  if (event.key === 'Escape') {
    open.value = false
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % props.options.length
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value - 1 + props.options.length) % props.options.length
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    const option = props.options[activeIndex.value]
    if (option) select(option.value)
  }
}
function outside(event: PointerEvent) {
  if (!root.value?.contains(event.target as Node)) open.value = false
}
window.addEventListener('pointerdown', outside)
onBeforeUnmount(() => window.removeEventListener('pointerdown', outside))
</script>

<template>
  <div ref="root" class="base-select" @keydown="onKeydown">
    <button
      ref="trigger"
      type="button"
      class="base-select__trigger"
      :aria-label="label"
      aria-haspopup="listbox"
      :aria-expanded="open"
      @click="toggle"
    >
      <span>{{ selected?.label || placeholderText }}</span>
      <ChevronDown :size="16" :class="{ rotated: open }" />
    </button>
    <Transition name="select-pop">
      <div v-if="open" class="base-select__menu" role="listbox" :aria-label="label">
        <button
          v-for="(option, index) in options"
          :key="option.value"
          type="button"
          role="option"
          :aria-selected="option.value === modelValue"
          :class="{ active: index === activeIndex, selected: option.value === modelValue }"
          @pointerenter="activeIndex = index"
          @click="select(option.value)"
        >
          <span><strong>{{ option.label }}</strong><small v-if="option.description">{{ option.description }}</small></span>
          <Check v-if="option.value === modelValue" :size="15" />
        </button>
      </div>
    </Transition>
  </div>
</template>
