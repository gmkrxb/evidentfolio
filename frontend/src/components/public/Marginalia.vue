<script setup lang="ts">
/**
 * 页边札记：在各页首屏的右侧缓缓轮换的一句话——哲学、计算、物联、音乐与智能。
 * 每页从不同的主题开始；鼠标悬停时暂停，点击切到下一句；减少动态效果时不轮换。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useLocaleStore } from '@/stores/locale'

type Theme = 'philosophy' | 'computing' | 'iot' | 'music' | 'intelligence'
const props = withDefaults(defineProps<{ start?: Theme }>(), { start: 'philosophy' })
const locale = useLocaleStore()

const GLYPHS: Record<Theme, { mark: string; zh: string; en: string }> = {
  philosophy: { mark: '∴', zh: '哲学', en: 'Philosophy' },
  computing: { mark: 'λ', zh: '计算', en: 'Computing' },
  iot: { mark: '∿', zh: '物联', en: 'Sensing' },
  music: { mark: '♩', zh: '音乐', en: 'Music' },
  intelligence: { mark: '◎', zh: '智能', en: 'Intelligence' },
}
const LINES: Array<{ theme: Theme; zh: string; en: string; by: string; byEn: string }> = [
  { theme: 'philosophy', zh: '知之为知之，不知为不知，是知也。', en: 'To know what you know, and to know what you do not know — that is knowledge.', by: '孔子', byEn: 'Confucius' },
  { theme: 'philosophy', zh: '人不能两次踏进同一条河流。', en: 'No one steps in the same river twice.', by: '赫拉克利特', byEn: 'Heraclitus' },
  { theme: 'philosophy', zh: '我的语言的界限，意味着我的世界的界限。', en: 'The limits of my language mean the limits of my world.', by: '维特根斯坦', byEn: 'Wittgenstein' },
  { theme: 'philosophy', zh: '天地有大美而不言。', en: 'Heaven and earth hold great beauty, and say nothing of it.', by: '庄子', byEn: 'Zhuangzi' },
  { theme: 'computing', zh: '程序首先是写给人读的，只是顺便让机器执行。', en: 'Programs must be written for people to read, and only incidentally for machines to execute.', by: '阿贝尔森 & 萨斯曼', byEn: 'Abelson & Sussman' },
  { theme: 'computing', zh: '地图不是疆域。', en: 'The map is not the territory.', by: '科日布斯基', byEn: 'Korzybski' },
  { theme: 'computing', zh: '万物皆数。', en: 'All is number.', by: '毕达哥拉斯', byEn: 'Pythagoras' },
  { theme: 'iot', zh: '最深刻的技术，是那些消失了的技术。', en: 'The most profound technologies are those that disappear.', by: '马克·韦泽', byEn: 'Mark Weiser' },
  { theme: 'iot', zh: '信息，是被消除的不确定性。', en: 'Information is uncertainty, resolved.', by: '仿香农', byEn: 'after Shannon' },
  { theme: 'music', zh: '大音希声，大象无形。', en: 'The great sound is hard to hear; the great image has no form.', by: '老子', byEn: 'Laozi' },
  { theme: 'music', zh: '建筑是凝固的音乐。', en: 'Architecture is frozen music.', by: '歌德', byEn: 'Goethe' },
  { theme: 'music', zh: '音乐，是心灵在不知不觉中做的算术。', en: 'Music is the arithmetic of a soul that does not know it is counting.', by: '仿莱布尼茨', byEn: 'after Leibniz' },
  { theme: 'intelligence', zh: '我们只能看到前方很短的距离，但能看到那里有许多事要做。', en: 'We can only see a short distance ahead, but we can see plenty there that needs to be done.', by: '图灵', byEn: 'Alan Turing' },
  { theme: 'intelligence', zh: '所有模型都是错的，但有些是有用的。', en: 'All models are wrong, but some are useful.', by: '乔治·博克斯', byEn: 'George Box' },
]

const first = Math.max(0, LINES.findIndex((line) => line.theme === props.start))
const index = ref(first)
const line = computed(() => LINES[index.value % LINES.length]!)
const glyph = computed(() => GLYPHS[line.value.theme])
let timer = 0
const paused = ref(false)
function next() { index.value = (index.value + 1) % LINES.length }
onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  timer = window.setInterval(() => { if (!paused.value && !document.hidden) next() }, 9000)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <figure class="marginalia" @mouseenter="paused = true" @mouseleave="paused = false" @click="next">
    <figcaption class="marginalia__head">
      <span class="marginalia__mark" aria-hidden="true">{{ glyph.mark }}</span>
      <span>{{ locale.isEnglish ? glyph.en : glyph.zh }}</span>
      <i aria-hidden="true" />
      <span class="marginalia__count">{{ String(index % LINES.length + 1).padStart(2, '0') }} / {{ LINES.length }}</span>
    </figcaption>
    <Transition name="marginalia" mode="out-in">
      <blockquote :key="index">
        <p>{{ locale.isEnglish ? line.en : line.zh }}</p>
        <cite>— {{ locale.isEnglish ? line.byEn : line.by }}</cite>
      </blockquote>
    </Transition>
  </figure>
</template>

<style scoped>
.marginalia { position: absolute; right: max(calc(clamp(32px, 6vw, 96px) / 2), calc((100% - 1320px) / 2)); bottom: clamp(96px, 14vh, 150px); width: min(320px, 30vw); margin: 0; cursor: pointer; user-select: none; }
.marginalia__head { display: flex; align-items: center; gap: 10px; color: var(--color-muted); font-family: var(--font-mono); font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase; }
.marginalia__head i { flex: 1; height: 1px; background: var(--color-line-strong); }
.marginalia__mark { display: inline-grid; width: 22px; height: 22px; place-items: center; border: 1px solid var(--color-line-strong); border-radius: 50%; color: var(--color-accent-ink); font-size: 12px; letter-spacing: 0; text-transform: none; animation: marginalia-breathe 6s ease-in-out infinite; }
.marginalia__count { letter-spacing: .08em; }
blockquote { margin: 14px 0 0; padding: 0; border: 0; }
blockquote p { max-width: none !important; margin: 0 !important; color: var(--color-ink) !important; font-family: var(--font-display); font-size: 17px !important; line-height: 1.6 !important; letter-spacing: -.005em; text-wrap: pretty; }
blockquote cite { display: block; margin-top: 8px; color: var(--color-muted); font-family: var(--font-mono); font-size: 11px; font-style: normal; letter-spacing: .08em; }
.marginalia-enter-active { transition: opacity .9s ease, filter .9s ease, transform 1s cubic-bezier(.16,1,.3,1); }
.marginalia-leave-active { transition: opacity .45s ease, filter .45s ease; }
.marginalia-enter-from { opacity: 0; filter: blur(6px); transform: translateY(8px); }
.marginalia-leave-to { opacity: 0; filter: blur(6px); }
@keyframes marginalia-breathe { 50% { box-shadow: 0 0 0 5px color-mix(in srgb, var(--color-accent) 10%, transparent); } }
@media (max-width: 1099px) {
  .marginalia { position: relative; right: auto; bottom: auto; width: auto; max-width: 560px; margin: 28px 0 0; }
}
@media (prefers-reduced-motion: reduce) { .marginalia__mark { animation: none; } }
</style>
