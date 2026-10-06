<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowDown, ArrowRight, ArrowUpRight, FileText } from 'lucide-vue-next'
import ProjectCover from '@/components/public/ProjectCover.vue'
import ProjectArt from '@/components/public/ProjectArt.vue'
import LineArt from '@/components/public/LineArt.vue'
import InferenceCard from '@/components/public/InferenceCard.vue'
import LexiconBand from '@/components/public/LexiconBand.vue'
import AgentSwarm from '@/components/public/AgentSwarm.vue'
import SplitText from '@/components/ui/SplitText.vue'
import CountUp from '@/components/ui/CountUp.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { projectCoverAssets } from '@/utils/projectCover'
import { usePinProgress } from '@/composables/usePinProgress'
import { scrollToY } from '@/utils/smoothScroll'
import { publicApi } from '@/api/public'
import { useAsyncState } from '@/composables/useAsync'
import { useLocaleReload } from '@/composables/useLocaleReload'
import { usePageAnalytics } from '@/composables/useAnalytics'
import { useMeta } from '@/composables/useMeta'
import { useSiteStore } from '@/stores/site'
import { useLocaleStore } from '@/stores/locale'
import type { Project } from '@/types'

const site = useSiteStore()
const locale = useLocaleStore()
const featured = useAsyncState<{ items: Project[] }>({ keepPreviousData: true })
const settings = computed(() => site.settings)
const homeCopy = computed(() => settings.value.home_copy || {})
const projects = computed(() => featured.data.value?.items || [])
const covers = computed(() => Object.fromEntries(projects.value.map((project) => [project.uuid, projectCoverAssets(project)])))
const directions = computed(() => (settings.value.research_directions || []).filter(Boolean))
const stats = computed(() => (settings.value.home_stats || []).filter((item) => item.value || item.label))
const en = computed(() => locale.isEnglish)
const text = (zh: string, english: string) => (en.value ? english : zh)

const personName = computed(() => settings.value.person_name || settings.value.site_name || 'Portfolio')
const headline = computed(() => settings.value.headline || text('在结构与数据之间，\n寻找可被证明的答案。', 'Between structure and data,\nfind answers that can be proven.'))
const manifesto = computed(() => homeCopy.value.manifesto || text(
  '结构，是重力写下的诗。\n数据，是时间留下的痕迹。\n我想让机器学会倾听——\n在钢与混凝土的沉默里，找到可以被证明的答案。',
  'Structure is a poem written by gravity.\nData is the trace that time leaves behind.\nI teach machines to listen —\nto find, in the silence of steel and concrete, answers that can be proven.',
))
const closing = computed(() => homeCopy.value.closing || text('愿每一座结构都被理解，\n每一个结论都有据可依。', 'May every structure be understood,\nand every conclusion rest on evidence.'))
// 每张「图纸」的主题：结构 · 智能 · 信息 · 建筑，各配一句题辞与三个关键词。
const PLATES = [
  { zh: '结构', en: 'Structure', code: 'S', scale: '1:200', keys: [['荷载', 'Load'], ['应力', 'Stress'], ['证据', 'Evidence']], epigraph: ['力，总沿着最短的路，回到大地。', 'Force always finds the shortest way back to the earth.'] },
  { zh: '智能', en: 'Intelligence', code: 'I', scale: 'n = 10⁹', keys: [['表征', 'Representation'], ['注意力', 'Attention'], ['推理', 'Reasoning']], epigraph: ['意义，在连接与连接之间涌现。', 'Meaning emerges between the connections.'] },
  { zh: '信息', en: 'Information', code: 'D', scale: '100 Hz', keys: [['传感', 'Sensing'], ['信号', 'Signal'], ['异常', 'Anomaly']], epigraph: ['异常，是数据写给我们的一封信。', 'An anomaly is a letter the data writes to us.'] },
  { zh: '建筑', en: 'Architecture', code: 'A', scale: '1:100', keys: [['空间', 'Space'], ['比例', 'Proportion'], ['秩序', 'Order']], epigraph: ['空间，是凝固的时间。', 'Space is time, held still.'] },
]
const layers = computed(() => {
  const capabilities = (settings.value.home_capabilities || []).filter((item) => item.title)
  const source = capabilities.length ? capabilities.slice(0, 6) : directions.value.slice(0, 4).map((title) => ({ title, description: '' }))
  return source.map((item, index) => {
    const plate = PLATES[index % PLATES.length]!
    const custom = (item as { epigraph?: string }).epigraph
    return {
      ...item,
      discipline: en.value ? plate.en : plate.zh,
      disciplineAlt: en.value ? plate.zh : plate.en,
      code: `${plate.code}-${String(index + 1).padStart(2, '0')}`,
      scale: plate.scale,
      keys: plate.keys.map(([zh, english]) => (en.value ? english : zh)),
      epigraph: custom || (en.value ? plate.epigraph[1] : plate.epigraph[0]),
    }
  })
})
const year = new Date().getFullYear()
const title = computed(() => String(settings.value.default_seo_title || settings.value.site_name || 'Portfolio'))
const description = computed(() => String(settings.value.default_seo_description || settings.value.bio || ''))

const hero = ref<HTMLElement | null>(null)
const manifestoSection = ref<HTMLElement | null>(null)
const layersSection = ref<HTMLElement | null>(null)
const work = ref<HTMLElement | null>(null)
const track = ref<HTMLElement | null>(null)
const activeWork = ref(0)
const workPinned = ref(false)
const shift = ref(0)
const pinQuery = window.matchMedia('(min-width: 900px) and (min-height: 600px) and (prefers-reduced-motion: no-preference)')

usePinProgress(hero)
// 手机端（非吸顶布局）的离场进度：首屏滚出视口时文字上移、缩小、淡出
usePinProgress(hero, { mode: 'pass', variable: '--pp' })
usePinProgress(manifestoSection)
usePinProgress(layersSection)
const { refresh: refreshWork } = usePinProgress(work, {
  onUpdate: (value) => {
    const total = projects.value.length + 1
    activeWork.value = Math.min(total - 1, Math.max(0, Math.round(value * (total - 1))))
  },
})

function measureWork() {
  workPinned.value = pinQuery.matches
  if (!track.value) return
  shift.value = workPinned.value ? Math.max(0, track.value.scrollWidth - document.documentElement.clientWidth) : 0
  refreshWork()
}

function scrollToSection(element: HTMLElement | null) {
  if (!element) return
  scrollToY(element.getBoundingClientRect().top + window.scrollY, 1400)
}

const clock = ref('')
let clockTimer = 0
function tick() {
  clock.value = new Intl.DateTimeFormat(en.value ? 'en-GB' : 'zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(new Date())
}

async function load() {
  await featured.run(async (signal) => {
    await site.load().catch(() => undefined)
    const count = Math.min(12, Math.max(1, Number(site.settings.featured_project_count) || 3))
    const result = await publicApi.projects({ featured: true, page_size: count }, signal)
    return { items: result.items }
  })
}

watch(() => projects.value.length, async () => { await nextTick(); measureWork() })

/**
 * 推理窗与首屏文字的避让：先按默认位置（右上）测量，若与标题、简介或按钮的任何一行文字相交，
 * 改放到右下；仍相交则隐藏。测量与切换在同一帧内同步完成，不会闪烁。
 */
let placeFrame = 0
/**
 * 推理窗与首屏文字的避让，只在“静止的版面”上计算：
 * 文字逐字入场、推理窗淡入都带有位移动画，直接测量会得到动画中途的位置，
 * 进而误判重叠、把标题突然缩小。因此先复制一份关闭了所有动画的隐形正文来测量，
 * 推理窗用不受 transform 影响的 offset 位置；结论只写回一次，重复计算结果一致，不会跳动。
 */
function placeInference() {
  placeFrame = 0
  const card = hero.value?.querySelector<HTMLElement>('.ah-hero__inference')
  const body = hero.value?.querySelector<HTMLElement>('.ah-hero__body')
  const host = body?.offsetParent as HTMLElement | null
  if (!card || !body || !host) return
  if (window.scrollY > window.innerHeight * 0.2) return // 只在首屏未被滚动变换时测量
  const ghost = body.cloneNode(true) as HTMLElement
  ghost.classList.add('is-measuring')
  ghost.setAttribute('aria-hidden', 'true')
  ghost.style.removeProperty('--hero-text-max')
  Object.assign(ghost.style, { position: 'absolute', left: `${body.offsetLeft}px`, top: `${body.offsetTop}px`, width: `${body.offsetWidth}px`, margin: '0', visibility: 'hidden', pointerEvents: 'none' })
  host.appendChild(ghost)
  const range = document.createRange()
  const baseHeight = ghost.offsetHeight
  const cardRect = () => {
    const parent = (card.offsetParent as HTMLElement | null)?.getBoundingClientRect() || { left: 0, top: 0 }
    const left = parent.left + card.offsetLeft, top = parent.top + card.offsetTop
    return { left, top, right: left + card.offsetWidth, bottom: top + card.offsetHeight }
  }
  const collides = () => {
    // 正文在弹性布局里纵向居中：变高后上沿会上移一半的增量
    ghost.style.top = `${body.offsetTop - (ghost.offsetHeight - baseHeight) / 2}px`
    const c = cardRect()
    const rects: DOMRect[] = []
    const scan = document.createTreeWalker(ghost, NodeFilter.SHOW_TEXT)
    for (let node = scan.nextNode(); node; node = scan.nextNode()) {
      if (!node.textContent?.trim() || node.parentElement?.closest('.sr-only')) continue // 读屏文字不占可见空间
      range.selectNodeContents(node)
      for (const rect of range.getClientRects()) if (rect.width > 1 && rect.height > 1) rects.push(rect)
    }
    ghost.querySelectorAll('a, button').forEach((element) => rects.push(element.getBoundingClientRect()))
    return rects.some((r) => r.right > c.left - 24 && r.left < c.right + 24 && r.bottom > c.top - 6 && r.top < c.bottom + 6)
  }
  // 依次尝试：原样 → 收窄文字让位 → 紧凑推理窗 + 收窄 → 移到右下 → 隐藏
  let narrowTo = ''
  const avoid = (on: boolean) => {
    narrowTo = ''
    ghost.style.removeProperty('--hero-text-max')
    if (!on) return true
    const room = cardRect().left - ghost.getBoundingClientRect().left - 40
    if (room < ghost.offsetWidth * 0.5) return false
    narrowTo = `${Math.floor(room)}px`
    ghost.style.setProperty('--hero-text-max', narrowTo)
    return true
  }
  let result: { mode: string; narrow: string } = { mode: 'hidden', narrow: '' }
  const attempts: Array<[string, boolean]> = [['', false], ['', true], ['compact', true], ['low', false]]
  for (const [mode, narrow] of attempts) {
    card.dataset.mode = mode
    if (!avoid(narrow)) continue
    if (getComputedStyle(card).position !== 'absolute' || !collides()) { result = { mode, narrow: narrowTo }; break }
  }
  ghost.remove()
  card.dataset.mode = result.mode
  if (result.narrow) body.style.setProperty('--hero-text-max', result.narrow)
  else body.style.removeProperty('--hero-text-max')
}
function schedulePlacement() { if (!placeFrame) placeFrame = requestAnimationFrame(placeInference) }
let resizeTimer = 0
// 拖动窗口时不逐帧重排，停下 150ms 后再算一次
function onPlacementResize() { window.clearTimeout(resizeTimer); resizeTimer = window.setTimeout(schedulePlacement, 150) }
watch(headline, async () => { if (!heroReady.value) return; await nextTick(); schedulePlacement() })
watch(() => settings.value.bio, async () => { if (!heroReady.value) return; await nextTick(); schedulePlacement() })
/**
 * 首屏在“字体就绪 + 站点文案到达”之后才开始逐字入场：先在隐形状态下排好版、算好推理窗的位置，
 * 再一次性显示，避免标题先以一种字号出现、随后又因字体或文案变化而突然缩小。最多等待 1.2 秒。
 */
const heroReady = ref(false)
function prepareHero() {
  const fonts = document.fonts?.ready ?? Promise.resolve()
  const data = site.load().catch(() => undefined)
  void Promise.race([Promise.all([fonts, data]), new Promise((resolve) => window.setTimeout(resolve, 1200))])
    .then(async () => { await nextTick(); placeInference(); heroReady.value = true })
}
useLocaleReload(load)
onMounted(() => {
  void load()
  tick()
  clockTimer = window.setInterval(tick, 1000)
  window.addEventListener('resize', measureWork, { passive: true })
  window.addEventListener('resize', onPlacementResize, { passive: true })
  pinQuery.addEventListener('change', measureWork)
  measureWork()
  prepareHero()
})
onBeforeUnmount(() => {
  window.clearInterval(clockTimer)
  window.removeEventListener('resize', measureWork)
  window.removeEventListener('resize', onPlacementResize)
  window.clearTimeout(resizeTimer)
  cancelAnimationFrame(placeFrame)
  pinQuery.removeEventListener('change', measureWork)
})
usePageAnalytics('home')
useMeta({ title, description })
</script>

<template>
  <div class="atelier-home">
    <!-- 一 · 序：名字、命题与一束穿过场的光 -->
    <section id="introduction" ref="hero" class="ah-hero">
      <div class="ah-hero__sticky">
        <div class="container ah-hero__inner">
          <div class="ah-hero__meta">
            <span class="ah-mono"><i class="ah-dot" />{{ settings.hero_eyebrow || text('AI · 土木 · 信息', 'AI · Civil · Information') }}</span>
            <span v-if="settings.hero_focus_value" class="ah-mono ah-hero__focus">{{ settings.hero_focus_label || text('正在探索', 'Currently exploring') }} — {{ settings.hero_focus_value }}</span>
          </div>
          <div class="ah-hero__body" :class="{ 'is-pending': !heroReady }">
            <p class="ah-hero__name"><span>{{ personName }}</span></p>
            <h1 class="ah-hero__title"><SplitText :key="`${headline}:${heroReady}`" :text="headline" mode="intro" :delay="180" :step="55" /></h1>
            <p v-if="settings.bio" class="ah-hero__bio">{{ settings.bio }}</p>
            <div class="ah-hero__actions">
              <RouterLink v-magnetic class="ah-button ah-button--solid" :to="locale.publicPath('/projects')">{{ locale.t('featuredProjects') }}<ArrowUpRight :size="17" /></RouterLink>
              <RouterLink v-magnetic class="ah-button ah-button--ghost" :to="locale.publicPath('/resumes')"><FileText :size="16" />{{ locale.t('onlineResume') }}</RouterLink>
            </div>
          </div>
        </div>
        <InferenceCard class="ah-hero__inference" />
        <div v-if="directions.length" class="ah-ticker" aria-hidden="true">
          <div class="ah-ticker__track">
            <template v-for="copy in 4" :key="copy">
              <span v-for="(direction, index) in directions" :key="`${copy}-${index}`">{{ direction }}<i>✦</i></span>
            </template>
          </div>
        </div>
        <button v-magnetic="0.4" type="button" class="ah-cue" @click="scrollToSection(manifestoSection)">
          <span class="ah-mono">{{ text('向下 · 阅读结构', 'Scroll · read the structure') }}</span>
          <i><ArrowDown :size="14" /></i>
        </button>
      </div>
    </section>

    <!-- 二 · 宣言：文字随滚动着墨 -->
    <section id="manifesto" ref="manifestoSection" class="ah-manifesto">
      <div class="ah-manifesto__sticky">
        <div class="container ah-manifesto__inner">
          <span v-scramble="`§ 01 — ${text('关于', 'About')}`" class="ah-mono ah-label">§ 01 — {{ text('关于', 'About') }}</span>
          <p v-scroll-progress="{ start: .92, end: .32 }" class="ah-manifesto__text"><SplitText :key="manifesto" :text="manifesto" mode="fill" /></p>
          <div v-if="directions.length" v-scroll-progress="{ start: .98, end: .6 }" class="ah-manifesto__directions">
            <span v-for="(direction, index) in directions" :key="index" :style="{ '--k': index }"><em>{{ String(index + 1).padStart(2, '0') }}</em>{{ direction }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 三 · 层：能力如图层般叠起 -->
    <section v-if="layers.length" id="capabilities" ref="layersSection" class="ah-layers" :style="{ '--n': layers.length }">
      <div class="ah-layers__sticky">
        <div class="container ah-layers__inner">
          <header class="ah-layers__head">
            <span v-scramble="`§ 02 — ${homeCopy.capabilities_eyebrow || text('方法', 'Method')}`" class="ah-mono ah-label">§ 02 — {{ homeCopy.capabilities_eyebrow || text('方法', 'Method') }}</span>
            <h2 class="ah-display">{{ homeCopy.capabilities_title || text('从力学，到语言。', 'From mechanics, to language.') }}</h2>
            <p v-if="homeCopy.capabilities_description">{{ homeCopy.capabilities_description }}</p>
          </header>
          <div class="ah-layers__stage">
            <article v-for="(item, index) in layers" :key="index" v-scroll-progress="{ start: .95, end: .4 }" class="ah-layer" :style="{ '--i': index }">
              <div class="ah-layer__text">
                <span class="ah-layer__numeral" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
                <div class="ah-layer__head ah-mono"><span>{{ text('图版', 'Plate') }} {{ String(index + 1).padStart(2, '0') }} / {{ String(layers.length).padStart(2, '0') }}</span><span>{{ item.discipline }} · {{ item.disciplineAlt }}</span></div>
                <h3>{{ item.title }}</h3>
                <p class="ah-layer__epigraph">{{ item.epigraph }}</p>
                <p v-if="item.description" class="ah-layer__description">{{ item.description }}</p>
                <ul class="ah-layer__keys"><li v-for="(key, k) in item.keys" :key="k"><em>{{ String.fromCharCode(97 + k) }}.</em>{{ key }}</li></ul>
              </div>
              <figure class="ah-layer__sheet">
                <i class="ah-crop ah-crop--tl" /><i class="ah-crop ah-crop--tr" /><i class="ah-crop ah-crop--bl" /><i class="ah-crop ah-crop--br" />
                <div class="ah-layer__art"><LineArt :variant="index" live /></div>
                <figcaption class="ah-titleblock ah-mono">
                  <span><small>{{ text('图号', 'Dwg') }}</small>{{ item.code }}</span>
                  <span><small>{{ text('比例', 'Scale') }}</small>{{ item.scale }}</span>
                  <span><small>{{ text('主题', 'Subject') }}</small>{{ item.discipline }}</span>
                  <span><small>{{ text('日期', 'Date') }}</small>{{ year }}</span>
                </figcaption>
              </figure>
            </article>
          </div>
        </div>
      </div>
    </section>

    <!-- 三½ · 协作：多智能体 -->
    <section id="agents" class="ah-agents">
      <div class="container">
        <header class="ah-agents__head">
          <span v-scramble="`§ 03 — ${homeCopy.agents_eyebrow || text('协作', 'Agents')}`" class="ah-mono ah-label">§ 03 — {{ homeCopy.agents_eyebrow || text('协作', 'Agents') }}</span>
          <h2 class="ah-display">{{ homeCopy.agents_title || text('让智能体，彼此校验。', 'Agents that check one another.') }}</h2>
          <p>{{ homeCopy.agents_description || text('感知、检索、推理、校验与执行，各司其职；每一个结论，都要回到原始数据接受另一位智能体的检验。', 'Perception, retrieval, reasoning, verification and action — each claim must survive another agent’s check against the raw data.') }}</p>
        </header>
        <AgentSwarm v-reveal="{ kind: 'panel' }" />
      </div>
    </section>

    <!-- 四 · 数：被证明的东西 -->
    <section v-if="stats.length" id="overview" class="ah-stats">
      <div class="container">
        <span v-scramble="`§ 04 — ${text('证据', 'Evidence')}`" class="ah-mono ah-label">§ 04 — {{ text('证据', 'Evidence') }}</span>
        <div class="ah-stats__grid">
          <div v-for="(item, index) in stats" :key="index" v-reveal="{ delay: index * 90, kind: 'metric' }" class="ah-stat">
            <em>{{ String(index + 1).padStart(2, '0') }}</em>
            <strong><CountUp :value="item.value" /></strong>
            <span>{{ item.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <LexiconBand />

    <!-- 五 · 作品：横向展开的长廊 -->
    <section id="featured" ref="work" class="ah-work" :class="{ 'is-pinned': workPinned }" :style="{ '--shift': `${shift}px`, '--n': projects.length + 1 }">
      <div class="ah-work__sticky">
        <div class="container ah-work__head">
          <div>
            <span v-scramble="`§ 05 — ${homeCopy.projects_eyebrow || text('作品', 'Work')}`" class="ah-mono ah-label">§ 05 — {{ homeCopy.projects_eyebrow || text('作品', 'Work') }}</span>
            <h2 class="ah-display">{{ homeCopy.projects_title || text('作品，是思考留下的结构。', 'Work is the structure thought leaves behind.') }}</h2>
          </div>
          <div class="ah-work__aside">
            <p v-if="homeCopy.projects_description">{{ homeCopy.projects_description }}</p>
            <span v-if="projects.length" class="ah-mono ah-work__count">{{ String(Math.min(activeWork + 1, projects.length)).padStart(2, '0') }} — {{ String(projects.length).padStart(2, '0') }}</span>
          </div>
        </div>
        <LoadingState v-if="featured.loading.value && !projects.length" class="container" :rows="4" variant="card" />
        <ErrorState v-else-if="featured.error.value" class="container" :message="featured.error.value" @retry="load" />
        <div v-else ref="track" class="ah-work__track">
          <RouterLink v-for="(project, index) in projects" :key="project.uuid" v-reveal="{ delay: (index % 3) * 90, kind: 'card' }" :to="locale.publicPath(`/projects/${project.uuid}`)" class="ah-card" :style="{ '--i': index }" :data-scroll-key="project.uuid">
            <div class="ah-card__media">
              <div class="ah-card__parallax">
                <ProjectCover v-if="covers[project.uuid]?.length" :assets="covers[project.uuid]!" :eager="index < 2" />
                <ProjectArt v-else :seed="project.uuid" :index="index" />
              </div>
            </div>
            <div class="ah-card__caption">
              <div class="ah-card__meta ah-mono">
                <span>{{ String(index + 1).padStart(2, '0') }}</span>
                <span>{{ project.category?.name || text('项目', 'Project') }}</span>
                <span v-if="project.start_date">{{ project.start_date.slice(0, 4) }}</span>
              </div>
              <h3>{{ project.title }}</h3>
              <p>{{ project.subtitle || project.summary }}</p>
              <span class="ah-card__more">{{ locale.t('viewCase') }}<ArrowUpRight :size="16" /></span>
            </div>
          </RouterLink>
          <RouterLink class="ah-card ah-card--more" :to="locale.publicPath('/projects')" :style="{ '--i': projects.length }">
            <span class="ah-mono">{{ text('全部', 'Index') }}</span>
            <strong>{{ locale.t('allProjects') }}</strong>
            <i><ArrowRight :size="22" /></i>
          </RouterLink>
        </div>
        <div v-if="workPinned && projects.length" class="container ah-work__rail"><span /></div>
      </div>
    </section>

    <!-- 六 · 方向 -->
    <section v-if="site.categories.length" id="directions" class="ah-directions">
      <div class="container">
        <div class="ah-directions__head">
          <span v-scramble="`§ 06 — ${homeCopy.categories_eyebrow || text('方向', 'Directions')}`" class="ah-mono ah-label">§ 06 — {{ homeCopy.categories_eyebrow || text('方向', 'Directions') }}</span>
          <h2 class="ah-display">{{ homeCopy.categories_title || text('探索更多方向。', 'Explore the directions.') }}</h2>
        </div>
        <div class="ah-directions__list">
          <RouterLink v-for="(category, index) in site.categories" :key="category.uuid" v-reveal="{ delay: index * 70, kind: 'row' }" :to="{ path: locale.publicPath('/projects'), query: { category: category.uuid } }" class="ah-direction">
            <span class="ah-mono">{{ String(index + 1).padStart(2, '0') }}</span>
            <strong>{{ category.name }}</strong>
            <small>{{ category.description }}</small>
            <i><ArrowUpRight :size="20" /></i>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- 七 · 结语 -->
    <section id="connect" class="ah-closing">
      <div class="container ah-closing__inner">
        <span v-scramble="`§ 07 — ${homeCopy.contact_eyebrow || text('来信', 'Correspondence')}`" class="ah-mono ah-label">§ 07 — {{ homeCopy.contact_eyebrow || text('来信', 'Correspondence') }}</span>
        <p v-reveal="{ kind: 'panel' }" class="ah-closing__quote"><SplitText :key="closing" :text="closing" mode="intro" :step="45" /></p>
        <p v-if="homeCopy.contact_description || settings.current_identity" class="ah-closing__note">{{ homeCopy.contact_description || settings.current_identity }}</p>
        <div class="ah-closing__actions">
          <RouterLink v-magnetic class="ah-button ah-button--solid" :to="locale.publicPath('/contact')">{{ locale.t('contactMe') }}<ArrowUpRight :size="17" /></RouterLink>
          <RouterLink v-magnetic class="ah-button ah-button--ghost" :to="locale.publicPath('/resumes')"><FileText :size="16" />{{ locale.t('onlineResume') }}</RouterLink>
        </div>
        <div class="ah-closing__meta ah-mono">
          <span v-if="settings.location">{{ settings.location }}</span>
          <span>{{ clock }}</span>
          <span>{{ settings.current_identity }}</span>
        </div>
      </div>
    </section>
  </div>
</template>
