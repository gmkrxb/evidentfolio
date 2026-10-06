<script setup lang="ts">
/**
 * 统一渲染资源中的图片 / 视频 / 音频。
 * 仅可查看的资源走加密票据，在内存中解密为 Blob 后播放，并禁用下载、画中画与右键另存。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { Asset } from '@/types'
import { protectedObjectUrl } from '@/utils/protectedAsset'

defineOptions({ inheritAttrs: false })
const props = withDefaults(defineProps<{
  asset: Pick<Asset, 'uuid' | 'sha256' | 'mime_type' | 'content_url' | 'thumbnail_url'> & { protected?: boolean }
  kind?: 'image' | 'video' | 'audio'
  /** 非受保护资源时使用的地址（例如缩略图），默认原始地址 */
  src?: string
  alt?: string
  /** 列表 / 网格中优先使用公开的缩略图，不解密原图 */
  thumbnail?: boolean
}>(), { kind: undefined, src: undefined, alt: '', thumbnail: false })
const emit = defineEmits<{ load: [Event] }>()

const resolved = ref('')
const failed = ref(false)
let controller: AbortController | null = null
const type = computed(() => props.kind || (props.asset.mime_type.startsWith('video/') ? 'video' : props.asset.mime_type.startsWith('audio/') ? 'audio' : 'image'))

async function resolve() {
  controller?.abort()
  failed.value = false
  if (props.thumbnail && props.asset.thumbnail_url && type.value === 'image') { resolved.value = props.asset.thumbnail_url; return }
  if (!props.asset.protected) { resolved.value = props.src || props.asset.content_url; return }
  resolved.value = ''
  controller = new AbortController()
  try {
    resolved.value = await protectedObjectUrl(props.asset, controller.signal)
  } catch {
    if (!controller.signal.aborted) failed.value = true
  }
}
watch(() => [props.asset.uuid, props.asset.sha256, props.asset.protected, props.src, props.thumbnail], resolve, { immediate: true })
onBeforeUnmount(() => controller?.abort())
</script>

<template>
  <template v-if="asset.protected">
    <img
      v-if="type === 'image'"
      v-bind="$attrs"
      v-protect
      class="asset-media is-protected-media"
      :class="{ 'is-pending': !resolved }"
      :src="resolved || asset.thumbnail_url || undefined"
      :alt="alt"
      draggable="false"
      @load="emit('load', $event)"
    />
    <video
      v-else-if="type === 'video' && resolved"
      v-bind="$attrs"
      v-protect
      class="asset-media is-protected-media"
      :src="resolved"
      :poster="asset.thumbnail_url || undefined"
      controls
      playsinline
      controlslist="nodownload noremoteplayback noplaybackrate"
      disablepictureinpicture
      disableremoteplayback
    />
    <audio
      v-else-if="type === 'audio' && resolved"
      v-bind="$attrs"
      v-protect
      class="asset-media is-protected-media"
      :src="resolved"
      controls
      controlslist="nodownload noremoteplayback"
    />
    <span v-else class="asset-media__pending" :class="{ 'is-failed': failed }" v-bind="$attrs">
      <span>{{ failed ? '加载失败 · Failed' : '解密中 · Decrypting' }}</span>
    </span>
  </template>
  <img v-else-if="type === 'image'" v-bind="$attrs" :src="resolved" :alt="alt" @load="emit('load', $event)" />
  <video v-else-if="type === 'video'" v-bind="$attrs" controls playsinline preload="metadata" :poster="asset.thumbnail_url || undefined">
    <source :src="resolved" :type="asset.mime_type" />
  </video>
  <audio v-else v-bind="$attrs" controls preload="metadata">
    <source :src="resolved" :type="asset.mime_type" />
  </audio>
</template>
