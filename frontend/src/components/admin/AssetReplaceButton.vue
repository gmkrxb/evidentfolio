<script setup lang="ts">
import { ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { adminApi } from '@/api/admin'
import { useToastStore } from '@/stores/toast'
import type { Asset } from '@/types'

/**
 * 替换附件：直接从本机选择新文件上传为下一版本。
 * 原链接、公开权限与所有关联内容保持不变，资源库中不会多出一份重复的源文件。
 */
const props = withDefaults(defineProps<{ asset: Asset; variant?: 'icon' | 'text' }>(), { variant: 'text' })
defineOptions({ inheritAttrs: false })
const emit = defineEmits<{ replaced: [asset: Asset] }>()
const input = ref<HTMLInputElement | null>(null)
const busy = ref(false)
const toast = useToastStore()

function choose() {
  if (!busy.value) input.value?.click()
}
async function replace(event: Event) {
  const element = event.target as HTMLInputElement
  const file = element.files?.[0]
  element.value = ''
  if (!file || busy.value) return
  if (props.asset.mime_type && file.type && file.type !== props.asset.mime_type) {
    toast.show(`请选择与原文件相同类型的文件（${props.asset.extension.replace('.', '').toUpperCase() || props.asset.mime_type}）`, 'error')
    return
  }
  const next = (props.asset.version || 1) + 1
  if (!window.confirm(`用“${file.name}”替换“${props.asset.display_name}”，作为第 ${next} 版？\n全部关联内容会立即使用新版本，原链接与${props.asset.is_public ? '公开' : '私有'}权限保持不变。`)) return
  busy.value = true
  try {
    const result = await adminApi.replaceAsset(props.asset, file)
    emit('replaced', result)
    toast.show(`附件已更新为第 ${result.version} 版`, 'success')
  } catch (cause) {
    toast.show(cause instanceof Error ? cause.message : '替换失败，原附件未改变', 'error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <!-- 按钮直接作为父级操作栏的子元素，继承与“预览 / 编辑 / 删除”相同的样式。 -->
  <button v-bind="$attrs" type="button" class="asset-replace" :class="{ 'is-busy': busy }" :disabled="busy" :aria-label="`替换 ${asset.display_name}`" :title="`从本机选择新文件，替换为第 ${(asset.version || 1) + 1} 版`" @click.stop="choose">
    <RefreshCw :size="16" :class="{ spinning: busy }" /><template v-if="variant === 'text'">{{ busy ? '上传中…' : '替换' }}</template>
  </button>
  <input ref="input" type="file" hidden style="display: none !important" tabindex="-1" aria-hidden="true" :accept="asset.mime_type || undefined" @change="replace" />
</template>

<style scoped>
.asset-replace.is-busy { cursor: progress; }
.spinning { animation: asset-replace-spin 1s linear infinite; }
@keyframes asset-replace-spin { to { transform: rotate(360deg); } }
</style>
