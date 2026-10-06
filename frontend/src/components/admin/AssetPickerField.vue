<script setup lang="ts">
import { computed, ref } from 'vue'
import { File, FolderOpen, X } from 'lucide-vue-next'
import ResourcePickerModal from './ResourcePickerModal.vue'
import type { Asset } from '@/types'
const props = withDefaults(defineProps<{ modelValue?: string | null; assets?: Asset[]; accept?: string; title?: string; placeholder?: string }>(), { assets: () => [], accept: '*/*', title: '选择文件', placeholder: '尚未选择文件' })
const emit = defineEmits<{ 'update:modelValue': [uuid: string]; picked: [assets: Asset[]] }>()
const open = ref(false)
const localAssets = ref<Asset[]>([])
const selected = computed(() => [...localAssets.value, ...props.assets].find(asset => asset.uuid === props.modelValue))
function confirm(uuids: string[], assets: Asset[]) { localAssets.value = assets; emit('update:modelValue', uuids[0] || ''); emit('picked', assets); open.value = false }
</script>
<template>
  <div class="asset-picker-field"><div class="asset-picker-field__identity"><img v-if="selected?.thumbnail_url" :src="selected.thumbnail_url" alt="" /><File v-else :size="22" /><span>{{ selected?.display_name || (modelValue ? '已关联文件' : placeholder) }}</span></div><div class="asset-picker-field__actions"><button type="button" class="button button--outline button--small" @click="open = true"><FolderOpen :size="16" />{{ modelValue ? '更换文件' : '从资源库选择' }}</button><button v-if="modelValue" type="button" class="icon-button" aria-label="清除文件选择" @click="emit('update:modelValue', '')"><X :size="17" /></button></div></div>
  <ResourcePickerModal :open="open" :assets="assets" :selected="modelValue ? [modelValue] : []" :multiple="false" :accept="accept" :title="title" @close="open = false" @confirm="confirm" />
</template>
