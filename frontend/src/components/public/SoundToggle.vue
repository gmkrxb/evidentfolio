<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ambient, type SoundState } from '@/utils/ambientMusic'
import { useLocaleStore } from '@/stores/locale'

const locale = useLocaleStore()
const state = ref<SoundState>('off')
let unsubscribe: (() => void) | undefined
// 浏览器拦截了自动播放时，轻声提示一次（每次会话只出现一次，几秒后自行隐去）
const hint = ref(false)
let hintTimer = 0
onMounted(() => {
  unsubscribe = ambient.subscribe((value) => {
    state.value = value
    if (value !== 'armed') { hint.value = false; return }
    window.clearTimeout(hintTimer)
    hintTimer = window.setTimeout(() => {
      if (state.value !== 'armed') return
      try { if (sessionStorage.getItem('portfolio_sound_hint')) return; sessionStorage.setItem('portfolio_sound_hint', '1') } catch { /* 忽略 */ }
      hint.value = true
      window.setTimeout(() => { hint.value = false }, 6500)
    }, 1200)
  })
})
onBeforeUnmount(() => { unsubscribe?.(); window.clearTimeout(hintTimer) })
const on = computed(() => state.value !== 'off')
const label = computed(() => (locale.isEnglish ? (on.value ? 'Sound on — click to mute' : 'Sound off — click to play') : (on.value ? '声音已开启，点击静音' : '声音已关闭，点击播放')))
</script>

<template>
  <button type="button" class="sound-toggle" :class="[`is-${state}`]" data-sound-toggle :aria-pressed="on" :aria-label="label" :title="label" @click="ambient.toggle()">
    <span class="sound-toggle__bars" aria-hidden="true"><i /><i /><i /><i /></span>
    <Transition name="sound-hint"><span v-if="hint" class="sound-toggle__hint" aria-hidden="true">{{ locale.isEnglish ? 'Tap anywhere — the music begins' : '轻触任意处，音乐便开始' }}</span></Transition>
  </button>
</template>

<style scoped>
.sound-toggle { position: relative; display: inline-grid; width: 36px; height: 36px; flex: none; padding: 0; place-items: center; border: 1px solid var(--color-line); border-radius: 999px; background: color-mix(in srgb, var(--color-bg) 50%, transparent); color: var(--color-ink); cursor: pointer; transition: background .3s, border-color .3s, transform .45s cubic-bezier(.34,1.36,.5,1); }
.sound-toggle:hover { border-color: var(--color-ink); }
.sound-toggle:active { transform: scale(.9); }
.sound-toggle__bars { display: flex; align-items: center; gap: 2.5px; height: 14px; }
.sound-toggle__bars i { width: 2px; height: 3px; border-radius: 2px; background: currentColor; transition: height .4s cubic-bezier(.16,1,.3,1), opacity .3s; }
.sound-toggle.is-off .sound-toggle__bars i { opacity: .45; }
.sound-toggle.is-armed .sound-toggle__bars i { height: 6px; animation: sound-wait 2.4s ease-in-out infinite; }
.sound-toggle.is-armed .sound-toggle__bars i:nth-child(2) { animation-delay: .2s; }
.sound-toggle.is-armed .sound-toggle__bars i:nth-child(3) { animation-delay: .4s; }
.sound-toggle.is-armed .sound-toggle__bars i:nth-child(4) { animation-delay: .6s; }
.sound-toggle.is-playing { color: var(--color-accent-ink); border-color: color-mix(in srgb, var(--color-accent) 50%, transparent); }
.sound-toggle.is-playing .sound-toggle__bars i { animation: sound-bar 1.1s ease-in-out infinite; }
.sound-toggle.is-playing .sound-toggle__bars i:nth-child(2) { animation-duration: .8s; animation-delay: -.3s; }
.sound-toggle.is-playing .sound-toggle__bars i:nth-child(3) { animation-duration: 1.3s; animation-delay: -.6s; }
.sound-toggle.is-playing .sound-toggle__bars i:nth-child(4) { animation-duration: .95s; animation-delay: -.15s; }

.sound-toggle__hint { position: absolute; top: calc(100% + 12px); right: -6px; padding: 8px 12px; border: 1px solid var(--color-line); border-radius: 10px; background: color-mix(in srgb, var(--color-surface-strong) 92%, transparent); -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px); color: var(--color-ink-soft); font-family: var(--font-mono); font-size: 11px; letter-spacing: .06em; white-space: nowrap; box-shadow: 0 18px 40px -28px rgb(30 20 10 / 45%); pointer-events: none; }
.sound-toggle__hint::before { content: ''; position: absolute; top: -5px; right: 18px; width: 8px; height: 8px; border-top: 1px solid var(--color-line); border-left: 1px solid var(--color-line); background: inherit; transform: rotate(45deg); }
.sound-hint-enter-active, .sound-hint-leave-active { transition: opacity .5s ease, transform .6s cubic-bezier(.16,1,.3,1); }
.sound-hint-enter-from, .sound-hint-leave-to { opacity: 0; transform: translateY(-6px); }
@keyframes sound-bar { 0%, 100% { height: 3px; } 50% { height: 14px; } }
@keyframes sound-wait { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .sound-toggle__bars i { animation: none !important; } .sound-toggle.is-playing .sound-toggle__bars i { height: 10px; } }
</style>
