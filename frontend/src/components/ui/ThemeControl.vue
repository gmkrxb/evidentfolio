<script setup lang="ts">
import { Monitor, Moon, Sun } from 'lucide-vue-next'
import { computed } from 'vue'
import { useTheme, type ThemePreference } from '@/stores/theme'
import { useLocaleStore } from '@/stores/locale'
const theme = useTheme()
const locale = useLocaleStore()
const options = computed(() => [
  { value: 'system' as ThemePreference, icon: Monitor, label: locale.isEnglish ? 'Auto' : '自动' },
  { value: 'light' as ThemePreference, icon: Sun, label: locale.isEnglish ? 'Light' : '浅色' },
  { value: 'dark' as ThemePreference, icon: Moon, label: locale.isEnglish ? 'Dark' : '深色' },
])
</script>
<template>
  <div class="theme-control" role="group" :aria-label="locale.isEnglish ? 'Appearance' : '外观主题'" :style="{ '--theme-index': options.findIndex(option => option.value === theme.preference.value) }">
    <button v-for="option in options" :key="option.value" type="button" :aria-label="option.label" :aria-pressed="theme.preference.value === option.value" :title="option.label" @click="theme.setTheme(option.value, $event)"><component :is="option.icon" :size="14" aria-hidden="true" /><span>{{ option.label }}</span></button>
  </div>
</template>
