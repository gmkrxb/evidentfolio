<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

type CodeScene = {
  language: string
  file: string
  accent: string
  lines: string[]
}

const scenes: CodeScene[] = [
  {
    language: 'PYTHON',
    file: 'agent_workflow.py',
    accent: '#78b88a',
    lines: [
      '<k>async def</k> <f>build_agent</f>(request: Task):',
      '    context = <k>await</k> memory.<f>retrieve</f>(request)',
      '    plan = planner.<f>decompose</f>(request, context)',
      '    <k>return await</k> executor.<f>run</f>(plan)',
    ],
  },
  {
    language: 'TYPESCRIPT',
    file: 'useStreaming.ts',
    accent: '#6fa3c9',
    lines: [
      '<k>const</k> stream = <k>await</k> model.<f>generate</f>({',
      '  prompt, tools, responseFormat: schema,',
      '})',
      '<k>for await</k> (<k>const</k> token <k>of</k> stream) render(token)',
    ],
  },
  {
    language: 'GO',
    file: 'inference_service.go',
    accent: '#68b7c4',
    lines: [
      '<k>func</k> (s *Service) <f>Infer</f>(ctx context.Context) error {',
      '  result, err := s.model.<f>Predict</f>(ctx, window)',
      '  <k>if</k> err != nil { <k>return</k> retry(err) }',
      '  <k>return</k> s.events.<f>Publish</f>(result)',
      '}',
    ],
  },
  {
    language: 'VUE',
    file: 'InsightPanel.vue',
    accent: '#6ab79a',
    lines: [
      '<k>const</k> insights = computed(() =>',
      '  signals.value.<f>map</f>(explainAnomaly)',
      ')',
      '<t>&lt;InsightGraph</t> <p>:data</p>=<s>"insights"</s> <t>/&gt;</t>',
    ],
  },
]

const active = ref(0)
const revealed = ref(scenes[0].lines.length)
let rotationTimer: number | undefined
let typingTimer: number | undefined

const scene = computed(() => scenes[active.value])
const visibleLines = computed(() => scene.value.lines.slice(0, revealed.value))

function nextScene() {
  active.value = (active.value + 1) % scenes.length
  revealed.value = 0
  window.clearInterval(typingTimer)
  typingTimer = window.setInterval(() => {
    revealed.value += 1
    if (revealed.value >= scene.value.lines.length) window.clearInterval(typingTimer)
  }, 190)
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  rotationTimer = window.setInterval(nextScene, 4800)
})

onBeforeUnmount(() => {
  window.clearInterval(rotationTimer)
  window.clearInterval(typingTimer)
})
</script>

<template>
  <div class="vibe-code" aria-hidden="true" :style="{ '--code-accent': scene.accent }">
    <div class="vibe-code__glow" />
    <div class="vibe-code__window">
      <div class="vibe-code__bar">
        <span class="vibe-code__dots"><i /><i /><i /></span>
        <span>{{ scene.file }}</span>
        <strong>{{ scene.language }}</strong>
      </div>
      <div class="vibe-code__body">
        <div v-for="lineNumber in 6" :key="lineNumber" class="vibe-code__line">
          <span>{{ String(lineNumber).padStart(2, '0') }}</span>
          <code v-if="visibleLines[lineNumber - 1]" v-html="visibleLines[lineNumber - 1]" />
          <code v-else>&nbsp;</code>
        </div>
        <i class="vibe-code__cursor" />
      </div>
      <div class="vibe-code__status">
        <span>● generating</span>
        <span>UTF-8</span>
        <span>Ln {{ Math.min(revealed + 1, 6) }}, Col 18</span>
      </div>
    </div>
    <span class="vibe-code__chip vibe-code__chip--one">⌘ agent.run()</span>
    <span class="vibe-code__chip vibe-code__chip--two">✓ formatted</span>
    <span class="vibe-code__chip vibe-code__chip--three">AI-assisted</span>
  </div>
</template>
